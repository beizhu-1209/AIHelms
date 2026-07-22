from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from services import efficiency_service, usage_log_service

MAX_EXPORT_ROWS = 100000


def _text(params: dict[str, object], key: str, default: str = "") -> str:
    value = params.get(key)
    return str(value) if value not in (None, "") else default


def _int(params: dict[str, object], key: str) -> int | None:
    value = params.get(key)
    if value in (None, ""):
        return None
    return int(value)


def _ids(params: dict[str, object], *keys: str) -> list[int]:
    for key in keys:
        value = params.get(key)
        if value in (None, ""):
            continue
        if isinstance(value, (list, tuple, set)):
            return [int(item) for item in value if str(item).strip().isdigit()]
        items = str(value).split(',')
        return [int(item.strip()) for item in items if item.strip().isdigit()]
    return []


def _strings(params: dict[str, object], key: str) -> list[str] | None:
    value = params.get(key)
    if value in (None, ""):
        return None
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value]
    else:
        items = [item.strip() for item in str(value).split(',')]
    return [item for item in items if item] or None


def _datetime(params: dict[str, object], key: str) -> datetime | None:
    value = params.get(key)
    if value in (None, ""):
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _date_range(params: dict[str, object]) -> tuple[date, date]:
    start_raw = params.get("start_date")
    end_raw = params.get("end_date")
    if start_raw and end_raw:
        return date.fromisoformat(str(start_raw)), date.fromisoformat(str(end_raw))
    today = date.today()
    period = _text(params, "period", "month")
    if period == "today":
        return today, today
    if period == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    if period == "7d":
        return today - timedelta(days=6), today
    if period == "30d":
        return today - timedelta(days=29), today
    return today.replace(day=1), today


def _flatten_name(value: object, fallback: str = "") -> str:
    if isinstance(value, dict):
        return str(value.get("display_name") or value.get("name") or value.get("username") or fallback)
    return fallback


def _key_name(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("key_token") or "")
    return ""


async def build_export_rows(
    session: AsyncSession,
    source: str,
    export_type: str,
    params: dict[str, object],
) -> tuple[list[str], list[list[object]]]:
    if source == "usage_logs":
        return await _build_usage_log_rows(session, export_type, params)
    if source == "efficiency":
        return await _build_efficiency_rows(session, export_type, params)
    raise ValueError("该来源暂不支持创建导出任务")


async def _build_usage_log_rows(
    session: AsyncSession,
    export_type: str,
    params: dict[str, object],
) -> tuple[list[str], list[list[object]]]:
    common = {
        "page": 1,
        "page_size": MAX_EXPORT_ROWS,
        "start_time": _datetime(params, "start_time"),
        "end_time": _datetime(params, "end_time"),
        "user_id": _int(params, "user_id"),
    }
    if export_type == "llm":
        selected_models = _strings(params, "models")
        result = await usage_log_service.list_llm_logs(
            session,
            **common,
            ai_key_id=_int(params, "ai_key_id"),
            model=None if selected_models else _text(params, "model"),
            models=selected_models,
            provider=_text(params, "provider"),
            status=_text(params, "status"),
        )
        filters = await usage_log_service.llm_filters(session)
        model_active = {item["value"]: item["active"] for item in filters["models"]}
        return ['时间', '用户', '部门', 'Key', '模型', '模型是否在用', 'Provider', '状态', '输入Token', '输出Token', '缓存读Token', '缓存写Token', '总Token', '外部输入成本(元)', '外部输出成本(元)', '外部缓存命中成本(元)', '外部缓存创建成本(元)', '外部成本(元)', '内部输入成本(元)', '内部输出成本(元)', '内部缓存命中成本(元)', '内部缓存创建成本(元)', '内部成本(元)', '错误'], [
            [item["started_at"], _flatten_name(item.get("user")), (item.get("user") or {}).get("department_name", "") if isinstance(item.get("user"), dict) else "", _key_name(item.get("ai_key")), item["model"], "是" if model_active.get(item["model"], False) else "否", item["provider"], item["status"], item["prompt_tokens"], item["completion_tokens"], item["cache_read_tokens"], item["cache_creation_tokens"], item["total_tokens"], item["external_input_cost"], item["external_output_cost"], item["external_cache_read_cost"], item["external_cache_creation_cost"], item["external_cost"], item["internal_input_cost"], item["internal_output_cost"], item["internal_cache_read_cost"], item["internal_cache_creation_cost"], item["internal_cost"], item["error_message"] or ""]
            for item in result["items"]
        ]
    if export_type == "mcp":
        result = await usage_log_service.list_mcp_logs(
            session,
            **common,
            ai_key_id=_int(params, "ai_key_id"),
            server_id=_int(params, "server_id"),
            tool_name=_text(params, "tool_name"),
            status=_text(params, "status"),
        )
        return ["时间", "用户", "部门", "Key", "MCP Server", "工具", "状态", "外部成本(元)", "内部成本(元)", "响应摘要", "错误"], [
            [item["called_at"], _flatten_name(item.get("user")), (item.get("user") or {}).get("department_name", "") if isinstance(item.get("user"), dict) else "", _key_name(item.get("ai_key")), _flatten_name(item.get("server")), item["tool_name"], item["status"], item["external_cost"], item["internal_cost"], item["response_summary"], item["error_message"] or ""]
            for item in result["items"]
        ]
    if export_type == "skill":
        result = await usage_log_service.list_skill_logs(
            session,
            **common,
            skill_id=_int(params, "skill_id"),
            action=_text(params, "action"),
        )
        return ["时间", "用户", "部门", "Skill", "动作"], [
            [item["created_at"], _flatten_name(item.get("user")), (item.get("user") or {}).get("department_name", "") if isinstance(item.get("user"), dict) else "", _flatten_name(item.get("skill")), item["action"]]
            for item in result["items"]
        ]
    if export_type == "agent":
        result = await usage_log_service.list_agent_logs(
            session,
            **common,
            agent_id=_int(params, "agent_id"),
            platform=_text(params, "platform"),
        )
        return ["时间", "用户", "部门", "智能体", "平台", "会话ID"], [
            [item["created_at"], _flatten_name(item.get("user")), (item.get("user") or {}).get("department_name", "") if isinstance(item.get("user"), dict) else "", _flatten_name(item.get("agent")), item["platform"] or "", item.get("session_id", "")]
            for item in result["items"]
        ]
    raise ValueError("不支持的日志导出类型")


async def _build_efficiency_rows(
    session: AsyncSession,
    export_type: str,
    params: dict[str, object],
) -> tuple[list[str], list[list[object]]]:
    start, end = _date_range(params)
    dimension = _text(params, "dimension", "department")
    resource_type = _text(params, "resource_type", "all") or "all"
    if export_type == "overview_scope":
        result = await efficiency_service.get_overview(session, start, end, "day", dimension)
        return ["名称", "层级路径", "总人数", "活跃人数", "覆盖率(%)", "内部总成本(元)", "活跃人均成本(元)", "内部总成本环比(%)", "活跃人均成本环比(%)"], [
            [row["name"], row.get("path", ""), row["total_members"], row["active_members"], row["coverage_rate"], row["total_cost"], row["active_per_capita_cost"], row["cost_change"] if row["cost_change"] is not None else "", row["active_per_capita_change"] if row["active_per_capita_change"] is not None else ""]
            for row in result["department_table"]
        ]
    if export_type == "adoption_scope":
        result = await efficiency_service.get_adoption(session, start, end, dimension)
        return ["名称", "总人数", "活跃人数", "覆盖率(%)", "日均调用", "重度用户占比(%)", "活跃人数环比(%)"], [
            [row["name"], row["total_members"], row["active_members"], row["coverage_rate"], row["daily_avg_calls"], row["heavy_user_ratio"], row["change"] if row["change"] is not None else ""]
            for row in result["department_table"]
        ]
    if export_type == "adoption_agents":
        rows = await efficiency_service.get_adoption_agents(session, start, end, dimension)
        return ["排名", "智能体", "平台", "归属", "用户数", "调用次数"], [[row["rank"], row["name"], row["platform"], row["department"], row["user_count"], row["monthly_calls"]] for row in rows]
    if export_type in {"adoption_mcp", "adoption_skill"}:
        item_type = "mcp" if export_type == "adoption_mcp" else "skill"
        rows = await efficiency_service.get_adoption_resources(session, start, end, item_type, dimension)
        first = "MCP Server" if item_type == "mcp" else "Skill"
        second = "使用人数" if item_type == "mcp" else "安装人数"
        third = "调用次数" if item_type == "mcp" else "下载次数"
        return [first, second, third], [[row["name"], row["user_count"], row["monthly_calls"]] for row in rows]
    if export_type == "adoption_unused_users":
        rows = await efficiency_service.get_unused_users(session, start, end, dimension)
        return ["姓名", "归属", "职位", "已分配Key", "最后活跃"], [[row["name"], row["department"], row["position"], row["assigned_key"], row["last_active"] or "从未使用"] for row in rows]
    if export_type.startswith("cost_"):
        tab = export_type.removeprefix("cost_")
        scope_ids = _ids(params, "scope_ids", "scope_id", "department")
        department_id = scope_ids if dimension == "department" else None
        project_id = scope_ids if dimension == "project" else None
        detail = await efficiency_service.get_cost_detail(
            session, start, end, tab, resource_type, department_id, dimension, project_id
        )
        if tab == "model":
            header = ["平台模型", "模型ID", "层级", "凭证", "供应商", "路由模型", "请求数", "Token数", "缓存读Token", "缓存写Token", "内部成本(元)", "外部成本(元)", "差额(元)", "占比(%)", "均次成本(元)"]
            rows: list[list[object]] = []
            for row in detail.get("model", []):
                rows.append([row["model"], row["model_id"], "模型汇总", "", "", "", row["requests"], row["tokens"], row["cache_read_tokens"], row["cache_creation_tokens"], row["internal_cost"], row["external_cost"], row["cost_diff"], round(row["ratio"] * 100, 1), row["avg_cost"]])
                for credential in row.get("credentials", []):
                    rows.append([row["model"], row["model_id"], "凭证", credential.get("credential_name", ""), credential.get("provider_name", ""), credential.get("route_model", ""), credential["requests"], credential["tokens"], credential["cache_read_tokens"], credential["cache_creation_tokens"], credential["internal_cost"], credential["external_cost"], credential["cost_diff"], "", credential["avg_cost"]])
            return header, rows
        if tab == "mcp":
            header = ["MCP服务", "Server Name", "层级", "Tool", "调用数", "Tool数", "内部成本(元)", "外部成本(元)", "差额(元)", "占比(%)", "均次成本(元)"]
            rows: list[list[object]] = []
            for row in detail.get("mcp", []):
                rows.append([row["server"], row.get("server_code", ""), "服务汇总", "", row["requests"], row["tool_count"], row["internal_cost"], row["external_cost"], row["cost_diff"], round(row["ratio"] * 100, 1), row["avg_cost"]])
                for tool in row.get("tools", []):
                    rows.append([row["server"], row.get("server_code", ""), "Tool", tool.get("tool_name", ""), tool["requests"], "", tool["internal_cost"], tool["external_cost"], tool["cost_diff"], "", tool["avg_cost"]])
            return header, rows
        if tab == "date":
            return ["日期", "LLM内部成本(元)", "MCP内部成本(元)", "内部总成本(元)", "外部总成本(元)", "差额(元)", "请求数", "活跃用户"], [[row["date"], row["llm_cost"], row["mcp_cost"], row["total_cost"], row["external_cost"], row["cost_diff"], row["requests"], row["active_users"]] for row in detail.get("date", [])]
        if tab == "attribution":
            return ["日期", "资源类型", "成本对象", "使用人", "AI Key", "归属", "调用数", "输入Token", "输出Token", "缓存读Token", "缓存写Token", "内部输入成本(元)", "内部输出成本(元)", "内部缓存命中成本(元)", "内部缓存创建成本(元)", "内部成本(元)", "外部输入成本(元)", "外部输出成本(元)", "外部缓存命中成本(元)", "外部缓存创建成本(元)", "外部成本(元)", "差额(元)"], [[row["date"], row["resource_type"], row["cost_object"], row["user_name"], row["key_name"], row["scope_name"], row["requests"], row["input_tokens"], row["output_tokens"], row["cache_read_tokens"], row["cache_creation_tokens"], row["internal_input_cost"], row["internal_output_cost"], row["internal_cache_read_cost"], row["internal_cache_creation_cost"], row["internal_cost"], row["external_input_cost"], row["external_output_cost"], row["external_cache_read_cost"], row["external_cache_creation_cost"], row["external_cost"], row["cost_diff"]] for row in detail.get("attribution", [])]
        scope_key = "department"
        return ["归属", "LLM内部成本(元)", "MCP内部成本(元)", "内部总成本(元)", "外部总成本(元)", "差额(元)", "请求数", "输入Token", "输出Token", "缓存读Token", "缓存写Token", "人均成本(元)", "活跃人均成本(元)", "内部总成本环比(%)"], [[row.get("scope_name") or row.get("department"), row["llm_cost"], row["mcp_cost"], row["total_cost"], row["external_cost"], row["cost_diff"], row["requests"], row["input_tokens"], row["output_tokens"], row["cache_read_tokens"], row["cache_creation_tokens"], row["per_capita_cost"], row["active_per_capita_cost"], row["cost_change"] if row["cost_change"] is not None else ""] for row in detail.get(scope_key, [])]
    if export_type.startswith("budget_"):
        result = await efficiency_service.get_budget(session, _text(params, "month") or None)
        if export_type == "budget_key":
            return ["Key名", "归属对象", "归属类型", "Key类型", "预算(元)", "已用(元)", "执行率(%)"], [[row["key_name"], row["owner"], row["owner_type"], row["key_type"], row["budget"], row["used"], row["execution_rate"]] for row in result["keys"]]
        if export_type == "budget_user":
            header = ["姓名", "Key", "Key类型", "预算(元)", "已用(元)", "执行率(%)"]
            rows = [
                [
                    row["user_name"],
                    row["key_name"],
                    "主" if row["is_main"] else "场景",
                    row["budget"],
                    row["used"],
                    row["execution_rate"],
                ]
                for row in result["user_keys"]
            ]
            return header, rows
        key = "departments" if export_type == "budget_department" else "projects"
        name_key = "department" if export_type == "budget_department" else "project"
        return ["名称", "总预算(元)", "总已用(元)", "执行率(%)", "人员Key数", "人员Key预算(元)", "人员Key已用(元)", "归属Key数", "归属Key预算(元)", "归属Key已用(元)", "预测月底(元)", "风险"], [[row[name_key], row["monthly_budget"], row["used"], row["execution_rate"], row["user_key_count"], row["user_key_budget"], row["user_key_used"], row["scope_key_count"], row["scope_key_budget"], row["scope_key_used"], row["predicted_end"], row["risk"]] for row in result[key]]
    if export_type.startswith("health_"):
        result = await efficiency_service.get_ai_health(session)
        if export_type == "health_model":
            return ["模型", "模型ID", "类型", "发布", "启用部署", "部署总数", "状态", "更新时间"], [[row["name"], row["model_id"], row["category"], "是" if row["is_published"] else "否", row["active_deployments"], row["total_deployments"], row["status"], row["last_update"] or ""] for row in result["models"]]
        if export_type == "health_docker":
            return ["检查项", "状态", "结果"], [[row["name"], row["status"], row["value"]] for row in result["docker"]]
        return ["MCP名称", "Server Name", "工具数", "发布", "状态", "最后检查", "错误信息"], [[row["name"], row["server_name"], row["tool_count"], "是" if row["is_published"] else "否", row["status"], row["last_check"] or "", row["error"]] for row in result["mcp_servers"]]
    raise ValueError("不支持的效能导出类型")

"""Efficiency cost repository."""

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _normalize_ids(value) -> list[int]:
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        return [int(v) for v in value if str(v).isdigit()]
    return [int(value)] if str(value).isdigit() else []


def _append_id_filter(filters: str, params: dict, column: str, name: str, value) -> str:
    ids = _normalize_ids(value)
    if not ids:
        return filters
    keys = []
    for idx, item in enumerate(ids):
        key = f"{name}_{idx}"
        params[key] = item
        keys.append(f":{key}")
    return f"{filters} AND {column} IN ({', '.join(keys)})"


def _price_expr(key: str) -> str:
    return f"COALESCE(NULLIF(md.model_info->>'{key}', '')::numeric, 0)"


def _llm_cost_component_expr(price_key: str, tokens_expr: str) -> str:
    return (
        "CASE WHEN c.cost_type = 'llm'"
        " AND COALESCE(md.billing_type, 'token') = 'token'"
        f" THEN {_price_expr(price_key)} * {tokens_expr} / 1000000 ELSE 0 END"
    )


def _build_cost_filters(
    start_date: date, end_date: date, cost_type: str | None, department_id,
    table_alias: str = "", project_id=None,
) -> tuple[str, dict]:
    prefix = f"{table_alias}." if table_alias else ""
    user_col = f"{prefix}user_id"
    filters = f"WHERE {prefix}summary_date >= :start AND {prefix}summary_date <= :end"
    params: dict = {"start": start_date, "end": end_date}
    if cost_type and cost_type != "all":
        filters += f" AND {prefix}cost_type = :cost_type"
        params["cost_type"] = cost_type
    dept_ids = _normalize_ids(department_id)
    if dept_ids:
        keys = []
        for idx, item in enumerate(dept_ids):
            key = f"dept_id_{idx}"
            params[key] = item
            keys.append(f":{key}")
        filters += (
            " AND EXISTS (SELECT 1 FROM aihelms.user_departments ud_filter"
            f" WHERE ud_filter.user_id = {user_col}"
            f" AND ud_filter.department_id IN ({', '.join(keys)}))"
        )
    project_ids = _normalize_ids(project_id)
    if project_ids:
        keys = []
        for idx, item in enumerate(project_ids):
            key = f"project_id_{idx}"
            params[key] = item
            keys.append(f":{key}")
        filters += (
            " AND EXISTS (SELECT 1 FROM aihelms.user_projects up_filter"
            f" WHERE up_filter.user_id = {user_col}"
            f" AND up_filter.project_id IN ({', '.join(keys)}))"
        )
    return filters, params



async def get_cost_trend(
    session: AsyncSession, start_date: date, end_date: date,
    cost_type: str | None = None, department_id: int | None = None,
    project_id: int | None = None,
) -> list[dict]:
    filters, params = _build_cost_filters(start_date, end_date, cost_type, department_id, project_id=project_id)
    sql = text(
        f"SELECT summary_date::date AS d, cost_type,"
        f" COALESCE(SUM(internal_cost), 0) AS internal_cost,"
        f" COALESCE(SUM(external_cost), 0) AS external_cost"
        f" FROM aihelms.cost_summary_daily {filters} GROUP BY 1, 2 ORDER BY 1"
    )
    result = await session.execute(sql, params)
    return [
        {
            "date": str(r[0]),
            "cost_type": r[1],
            "cost": float(r[2]),
            "internal_cost": float(r[2]),
            "external_cost": float(r[3]),
        }
        for r in result.fetchall()
    ]


async def get_cost_by_type(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    department_id: int | None = None,
    cost_type: str | None = None,
    project_id: int | None = None,
) -> list[dict]:
    filters, params = _build_cost_filters(start_date, end_date, cost_type, department_id, project_id=project_id)
    sql = text(
        f"SELECT cost_type,"
        f" COALESCE(SUM(internal_cost), 0) AS internal_cost,"
        f" COALESCE(SUM(external_cost), 0) AS external_cost"
        f" FROM aihelms.cost_summary_daily {filters} GROUP BY cost_type ORDER BY internal_cost DESC"
    )
    result = await session.execute(sql, params)
    return [
        {"name": r[0], "value": float(r[1]), "internal_cost": float(r[1]), "external_cost": float(r[2])}
        for r in result.fetchall()
    ]


async def get_cost_by_dept(session: AsyncSession, start_date: date, end_date: date) -> list[dict]:
    sql = text(
        "SELECT d.name, COALESCE(SUM(c.internal_cost), 0) AS internal_cost,"
        " COALESCE(SUM(c.external_cost), 0) AS external_cost"
        " FROM aihelms.cost_summary_daily c"
        " JOIN aihelms.user_departments ud_dim ON ud_dim.user_id = c.user_id"
        " JOIN aihelms.departments d ON d.id = ud_dim.department_id"
        " WHERE c.summary_date >= :start AND c.summary_date <= :end"
        " GROUP BY d.name ORDER BY internal_cost DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    return [
        {"name": r[0], "value": float(r[1]), "internal_cost": float(r[1]), "external_cost": float(r[2])}
        for r in result.fetchall()
    ]


async def get_dept_per_capita_cost(session: AsyncSession, start_date: date, end_date: date) -> list[dict]:
    sql = text(
        "SELECT d.name, COALESCE(SUM(c.internal_cost), 0) AS cost, COUNT(DISTINCT c.user_id) AS users"
        " FROM aihelms.cost_summary_daily c"
        " JOIN aihelms.user_departments ud_dim ON ud_dim.user_id = c.user_id"
        " JOIN aihelms.departments d ON d.id = ud_dim.department_id"
        " WHERE c.summary_date >= :start AND c.summary_date <= :end AND c.user_id IS NOT NULL"
        " GROUP BY d.name ORDER BY cost DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    return [
        {"name": r[0], "value": round(float(r[1]) / int(r[2]), 2) if int(r[2]) > 0 else 0}
        for r in result.fetchall()
    ]


def _cost_dimension_config(dimension: str) -> tuple[str, str, str]:
    if dimension == "project":
        return (
            "p.name",
            "JOIN aihelms.user_projects up_dim ON up_dim.user_id = c.user_id "
            "JOIN aihelms.projects p ON p.id = up_dim.project_id",
            "项目",
        )
    return (
        "d.name",
        "JOIN aihelms.user_departments ud_dim ON ud_dim.user_id = c.user_id "
        "JOIN aihelms.departments d ON d.id = ud_dim.department_id",
        "部门",
    )


async def get_cost_by_dimension(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str = "department",
    cost_type: str | None = None,
    department_id: int | None = None,
    project_id: int | None = None,
) -> list[dict]:
    name_expr, join_sql, _ = _cost_dimension_config(dimension)
    filters, params = _build_cost_filters(start_date, end_date, cost_type, department_id, "c", project_id)
    sql = text(
        f"SELECT {name_expr} AS name,"
        f" COALESCE(SUM(c.internal_cost), 0) AS internal_cost,"
        f" COALESCE(SUM(c.external_cost), 0) AS external_cost"
        f" FROM aihelms.cost_summary_daily c {join_sql}"
        f" {filters} GROUP BY {name_expr} ORDER BY internal_cost DESC"
    )
    result = await session.execute(sql, params)
    return [
        {"name": r[0], "value": float(r[1]), "internal_cost": float(r[1]), "external_cost": float(r[2])}
        for r in result.fetchall()
    ]


async def get_per_capita_cost_by_dimension(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str = "department",
    cost_type: str | None = None,
    department_id: int | None = None,
    project_id: int | None = None,
) -> list[dict]:
    name_expr, join_sql, _ = _cost_dimension_config(dimension)
    filters, params = _build_cost_filters(start_date, end_date, cost_type, department_id, "c", project_id)
    sql = text(
        f"SELECT {name_expr} AS name, COALESCE(SUM(c.internal_cost), 0) AS cost,"
        f" COUNT(DISTINCT c.user_id) AS users"
        f" FROM aihelms.cost_summary_daily c {join_sql}"
        f" {filters} AND c.user_id IS NOT NULL"
        f" GROUP BY {name_expr} ORDER BY cost DESC"
    )
    result = await session.execute(sql, params)
    return [
        {"name": r[0], "value": round(float(r[1]) / int(r[2]), 2) if int(r[2]) > 0 else 0}
        for r in result.fetchall()
    ]


async def get_cost_detail_by_dimension(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str = "department",
    cost_type: str | None = None,
    department_id: int | None = None,
    project_id: int | None = None,
) -> list[dict]:
    name_expr, join_sql, _ = _cost_dimension_config(dimension)
    filters, params = _build_cost_filters(start_date, end_date, cost_type, department_id, "c", project_id)
    sql = text(
        f"SELECT {name_expr} AS name,"
        f" COALESCE(SUM(CASE WHEN c.cost_type = 'llm' THEN c.internal_cost ELSE 0 END), 0) AS llm_cost,"
        f" COALESCE(SUM(CASE WHEN c.cost_type = 'mcp' THEN c.internal_cost ELSE 0 END), 0) AS mcp_cost,"
        f" COALESCE(SUM(c.internal_cost), 0) AS internal_cost,"
        f" COALESCE(SUM(c.external_cost), 0) AS external_cost,"
        f" COALESCE(SUM(c.total_requests), 0) AS requests,"
        f" COUNT(DISTINCT c.user_id) AS users"
        f" FROM aihelms.cost_summary_daily c {join_sql}"
        f" {filters} GROUP BY {name_expr} ORDER BY internal_cost DESC"
    )
    result = await session.execute(sql, params)
    return [
        {
            "name": r[0],
            "llm_cost": float(r[1]),
            "mcp_cost": float(r[2]),
            "cost": float(r[3]),
            "internal_cost": float(r[3]),
            "external_cost": float(r[4]),
            "requests": int(r[5]),
            "users": int(r[6]),
            "per_capita": round(float(r[3]) / int(r[6]), 2) if int(r[6]) > 0 else 0,
            "active_per_capita": round(float(r[3]) / int(r[6]), 2) if int(r[6]) > 0 else 0,
        }
        for r in result.fetchall()
    ]


async def get_cost_detail_by_department(
    session: AsyncSession, start_date: date, end_date: date,
    cost_type: str | None = None, department_id: int | None = None,
    project_id: int | None = None,
) -> list[dict]:
    filters, params = _build_cost_filters(start_date, end_date, cost_type, department_id, "c", project_id)
    sql = text(
        f"SELECT d.name, COALESCE(SUM(c.internal_cost), 0) AS internal_cost,"
        f" COALESCE(SUM(c.external_cost), 0) AS external_cost,"
        f" COALESCE(SUM(c.total_requests), 0) AS requests, COUNT(DISTINCT c.user_id) AS users"
        f" FROM aihelms.cost_summary_daily c"
        f" JOIN aihelms.user_departments ud_dim ON ud_dim.user_id = c.user_id"
        f" JOIN aihelms.departments d ON d.id = ud_dim.department_id"
        f" {filters} GROUP BY d.name ORDER BY internal_cost DESC"
    )
    result = await session.execute(sql, params)
    return [
        {
            "name": r[0],
            "cost": float(r[1]),
            "internal_cost": float(r[1]),
            "external_cost": float(r[2]),
            "requests": int(r[3]),
            "users": int(r[4]),
            "per_capita": round(float(r[1]) / int(r[4]), 2) if int(r[4]) > 0 else 0,
            "active_per_capita": round(float(r[1]) / int(r[4]), 2) if int(r[4]) > 0 else 0,
        }
        for r in result.fetchall()
    ]


async def get_cost_detail_by_model(
    session: AsyncSession, start_date: date, end_date: date,
    cost_type: str | None = None, department_id: int | None = None,
    project_id: int | None = None,
) -> list[dict]:
    filters, params = _build_cost_filters(start_date, end_date, cost_type, department_id, "c", project_id)
    sql = text(
        f"SELECT"
        f" COALESCE('model:' || m.id::text, 'unmatched:' || COALESCE(c.model, 'unknown')) AS platform_model_key,"
        f" COALESCE(m.name, '未匹配模型/其他') AS platform_model_name,"
        f" COALESCE(m.model_id, c.model, '') AS platform_model_id,"
        f" c.model AS route_model,"
        f" c.provider_id AS credential_id,"
        f" cr.credential_name,"
        f" p.name AS provider_name,"
        f" p.provider_type,"
        f" md.deployment_id,"
        f" md.deploy_name,"
        f" COALESCE(SUM(c.internal_cost), 0) AS internal_cost,"
        f" COALESCE(SUM(c.external_cost), 0) AS external_cost,"
        f" COALESCE(SUM(c.total_requests), 0) AS requests,"
        f" COALESCE(SUM(c.input_tokens), 0) AS input_tokens,"
        f" COALESCE(SUM(c.output_tokens), 0) AS output_tokens,"
        f" COALESCE(SUM(c.cache_read_tokens), 0) AS cache_read_tokens,"
        f" COALESCE(SUM(c.cache_creation_tokens), 0) AS cache_creation_tokens"
        f" FROM aihelms.cost_summary_daily c"
        f" LEFT JOIN aihelms.credentials cr ON cr.id = c.provider_id"
        f" LEFT JOIN aihelms.providers p ON p.id = cr.provider_id"
        f" LEFT JOIN LATERAL ("
        f"   SELECT d.id AS deployment_id, d.model_id, d.deploy_name"
        f"   FROM aihelms.model_deployments d"
        f"   LEFT JOIN aihelms.models dm ON dm.id = d.model_id"
        f"   WHERE d.credential_id = c.provider_id"
        f"     AND (d.litellm_params->>'model' = c.model"
        f"       OR d.litellm_model_id = c.model"
        f"       OR d.deploy_name = c.model"
        f"       OR dm.model_id = c.model"
        f"       OR split_part(c.model, '/', 2) = dm.model_id"
        f"       OR dm.name = c.model)"
        f"   ORDER BY d.is_active DESC, d.id DESC"
        f"   LIMIT 1"
        f" ) md ON TRUE"
        f" LEFT JOIN aihelms.models m ON m.id = md.model_id"
        f" {filters} AND c.cost_type = 'llm' AND c.model IS NOT NULL"
        f" GROUP BY 1,2,3,4,5,6,7,8,9,10"
        f" ORDER BY internal_cost DESC"
    )
    result = await session.execute(sql, params)
    return [
        {
            "platform_model_key": r[0],
            "platform_model_name": r[1],
            "platform_model_id": r[2],
            "route_model": r[3],
            "credential_id": r[4],
            "credential_name": r[5] or "--",
            "provider_name": r[6] or "--",
            "provider_type": r[7] or "--",
            "deployment_id": r[8],
            "deployment_name": r[9] or "",
            "cost": float(r[10]),
            "internal_cost": float(r[10]),
            "external_cost": float(r[11]),
            "requests": int(r[12]),
            "input_tokens": int(r[13]),
            "output_tokens": int(r[14]),
            "cache_read_tokens": int(r[15]),
            "cache_creation_tokens": int(r[16]),
        }
        for r in result.fetchall()
    ]


async def get_cost_detail_by_mcp(
    session: AsyncSession, start_date: date, end_date: date,
    cost_type: str | None = None, department_id: int | None = None,
    project_id: int | None = None,
) -> list[dict]:
    if cost_type and cost_type != "mcp":
        return []
    filters = "WHERE m.called_at::date >= :start AND m.called_at::date <= :end"
    params: dict = {"start": start_date, "end": end_date}
    dept_ids = _normalize_ids(department_id)
    if dept_ids:
        keys = []
        for idx, item in enumerate(dept_ids):
            key = f"dept_id_{idx}"
            params[key] = item
            keys.append(f":{key}")
        filters += f" AND EXISTS (SELECT 1 FROM aihelms.user_departments ud WHERE ud.user_id = m.user_id AND ud.department_id IN ({', '.join(keys)}))"
    project_ids = _normalize_ids(project_id)
    if project_ids:
        keys = []
        for idx, item in enumerate(project_ids):
            key = f"project_id_{idx}"
            params[key] = item
            keys.append(f":{key}")
        filters += f" AND EXISTS (SELECT 1 FROM aihelms.user_projects up WHERE up.user_id = m.user_id AND up.project_id IN ({', '.join(keys)}))"
    sql = text(
        f"SELECT"
        f" COALESCE('mcp:' || ms.id::text, 'raw:' || m.server_id::text) AS server_key,"
        f" COALESCE(ms.name, ms.server_name, '未知MCP') AS server_name,"
        f" ms.server_name AS server_code,"
        f" m.server_id,"
        f" COALESCE(mt.display_name, NULLIF(m.tool_name, ''), m.namespaced_tool_name, '未知Tool') AS tool_name,"
        f" COALESCE(m.namespaced_tool_name, m.tool_name, '') AS namespaced_tool_name,"
        f" COALESCE(SUM(m.internal_cost), 0) AS internal_cost,"
        f" COALESCE(SUM(m.external_cost), 0) AS external_cost,"
        f" COUNT(*) AS requests"
        f" FROM aihelms.mcp_call_logs m"
        f" LEFT JOIN aihelms.mcp_servers ms ON ms.id = m.server_id"
        f" LEFT JOIN aihelms.mcp_tools mt ON mt.id = m.tool_id"
        f" {filters}"
        f" GROUP BY 1,2,3,4,5,6"
        f" ORDER BY internal_cost DESC"
    )
    result = await session.execute(sql, params)
    return [
        {
            "server_key": r[0],
            "server_name": r[1],
            "server_code": r[2] or "",
            "server_id": r[3],
            "tool_name": r[4] or "--",
            "namespaced_tool_name": r[5] or "",
            "cost": float(r[6]),
            "internal_cost": float(r[6]),
            "external_cost": float(r[7]),
            "requests": int(r[8]),
        }
        for r in result.fetchall()
    ]

async def get_cost_detail_by_date(
    session: AsyncSession, start_date: date, end_date: date,
    cost_type: str | None = None, department_id: int | None = None,
    project_id: int | None = None,
) -> list[dict]:
    filters, params = _build_cost_filters(start_date, end_date, cost_type, department_id, project_id=project_id)
    sql = text(
        f"SELECT summary_date::date AS d,"
        f" COALESCE(SUM(CASE WHEN cost_type = 'llm' THEN internal_cost ELSE 0 END), 0) AS llm_cost,"
        f" COALESCE(SUM(CASE WHEN cost_type = 'mcp' THEN internal_cost ELSE 0 END), 0) AS mcp_cost,"
        f" COALESCE(SUM(internal_cost), 0) AS internal_cost,"
        f" COALESCE(SUM(external_cost), 0) AS external_cost,"
        f" COALESCE(SUM(total_requests), 0) AS requests, COUNT(DISTINCT user_id) AS users"
        f" FROM aihelms.cost_summary_daily {filters} GROUP BY 1 ORDER BY 1"
    )
    result = await session.execute(sql, params)
    return [
        {
            "date": str(r[0]),
            "llm_cost": float(r[1]),
            "mcp_cost": float(r[2]),
            "cost": float(r[3]),
            "internal_cost": float(r[3]),
            "external_cost": float(r[4]),
            "requests": int(r[5]),
            "users": int(r[6]),
        }
        for r in result.fetchall()
    ]



async def get_cost_attribution_detail(
    session: AsyncSession, start_date: date, end_date: date,
    dimension: str = "department", cost_type: str | None = None, department_id: int | None = None,
    project_id: int | None = None,
) -> list[dict]:
    filters, params = _build_cost_filters(start_date, end_date, cost_type, department_id, "c", project_id)
    if dimension == "project":
        scope_join = (
            "LEFT JOIN aihelms.user_projects up_dim ON up_dim.user_id = c.user_id "
            "LEFT JOIN aihelms.projects p ON p.id = up_dim.project_id"
        )
        scope_expr = "p.name"
    else:
        scope_join = (
            "LEFT JOIN aihelms.user_departments ud_dim ON ud_dim.user_id = c.user_id "
            "LEFT JOIN aihelms.departments d ON d.id = ud_dim.department_id"
        )
        scope_expr = "d.name"
    billable_input = (
        "GREATEST(COALESCE(c.input_tokens, 0) - COALESCE(c.cache_read_tokens, 0)"
        " - COALESCE(c.cache_creation_tokens, 0), 0)"
    )
    output_tokens = "COALESCE(c.output_tokens, 0)"
    cache_read = "COALESCE(c.cache_read_tokens, 0)"
    cache_creation = "COALESCE(c.cache_creation_tokens, 0)"
    internal_input = _llm_cost_component_expr("internal_input_cost", billable_input)
    internal_output = _llm_cost_component_expr("internal_output_cost", output_tokens)
    internal_cache_read = _llm_cost_component_expr("internal_cache_read_cost", cache_read)
    internal_cache_creation = _llm_cost_component_expr("internal_cache_creation_cost", cache_creation)
    external_input = _llm_cost_component_expr("input_cost", billable_input)
    external_output = _llm_cost_component_expr("output_cost", output_tokens)
    external_cache_read = _llm_cost_component_expr("cache_read_cost", cache_read)
    external_cache_creation = _llm_cost_component_expr("cache_creation_cost", cache_creation)
    sql = text(
        f"SELECT c.summary_date::date, c.cost_type, COALESCE(c.model, ms.name, ''),"
        f" COALESCE(u.display_name, u.username, ''), COALESCE(k.name, ''), COALESCE({scope_expr}, ''),"
        f" COALESCE(SUM(c.total_requests),0), COALESCE(SUM(c.input_tokens),0), COALESCE(SUM(c.output_tokens),0),"
        f" COALESCE(SUM(c.cache_read_tokens),0), COALESCE(SUM(c.cache_creation_tokens),0),"
        f" COALESCE(SUM({internal_input}),0) AS internal_input_cost,"
        f" COALESCE(SUM({internal_output}),0) AS internal_output_cost,"
        f" COALESCE(SUM({internal_cache_read}),0) AS internal_cache_read_cost,"
        f" COALESCE(SUM({internal_cache_creation}),0) AS internal_cache_creation_cost,"
        f" COALESCE(SUM({external_input}),0) AS external_input_cost,"
        f" COALESCE(SUM({external_output}),0) AS external_output_cost,"
        f" COALESCE(SUM({external_cache_read}),0) AS external_cache_read_cost,"
        f" COALESCE(SUM({external_cache_creation}),0) AS external_cache_creation_cost,"
        f" COALESCE(SUM(c.internal_cost),0) AS internal_cost, COALESCE(SUM(c.external_cost),0) AS external_cost,"
        f" c.user_id, c.ai_key_id, c.model, c.server_id"
        f" FROM aihelms.cost_summary_daily c"
        f" LEFT JOIN aihelms.users u ON u.id = c.user_id"
        f" LEFT JOIN aihelms.ai_keys k ON k.id = c.ai_key_id"
        f" LEFT JOIN aihelms.mcp_servers ms ON ms.id = c.server_id"
        f" {scope_join}"
        f" LEFT JOIN LATERAL ("
        f"   SELECT d.model_info, d.billing_type"
        f"   FROM aihelms.model_deployments d"
        f"   LEFT JOIN aihelms.models dm ON dm.id = d.model_id"
        f"   WHERE c.cost_type = 'llm' AND d.credential_id = c.provider_id"
        f"     AND (d.litellm_params->>'model' = c.model"
        f"       OR d.litellm_model_id = c.model"
        f"       OR d.deploy_name = c.model"
        f"       OR dm.model_id = c.model"
        f"       OR split_part(c.model, '/', 2) = dm.model_id"
        f"       OR dm.name = c.model)"
        f"   ORDER BY d.is_active DESC, d.id DESC"
        f"   LIMIT 1"
        f" ) md ON TRUE"
        f" {filters}"
        f" GROUP BY c.summary_date::date, c.cost_type, c.model, ms.name, u.display_name, u.username, k.name, {scope_expr}, c.user_id, c.ai_key_id, c.server_id"
        f" ORDER BY internal_cost DESC LIMIT 500"
    )
    result = await session.execute(sql, params)
    return [
        {
            "date": str(r[0]), "resource_type": r[1], "cost_object": r[2] or r[1],
            "user_name": r[3] or "--", "key_name": r[4] or "--", "scope_name": r[5] or "--",
            "requests": int(r[6] or 0), "input_tokens": int(r[7] or 0), "output_tokens": int(r[8] or 0),
            "cache_read_tokens": int(r[9] or 0), "cache_creation_tokens": int(r[10] or 0),
            "internal_input_cost": float(r[11] or 0), "internal_output_cost": float(r[12] or 0),
            "internal_cache_read_cost": float(r[13] or 0), "internal_cache_creation_cost": float(r[14] or 0),
            "external_input_cost": float(r[15] or 0), "external_output_cost": float(r[16] or 0),
            "external_cache_read_cost": float(r[17] or 0), "external_cache_creation_cost": float(r[18] or 0),
            "internal_cost": float(r[19] or 0), "external_cost": float(r[20] or 0),
            "cost_diff": round(float(r[19] or 0) - float(r[20] or 0), 4),
            "user_id": r[21], "ai_key_id": r[22], "model": r[23] or "", "server_id": r[24],
        }
        for r in result.fetchall()
    ]

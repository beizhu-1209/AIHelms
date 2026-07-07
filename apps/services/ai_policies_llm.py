import json
import re
import zipfile
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from repositories import ai_key_repo, model_repo, user_repo
from services import litellm_client

MAX_REVIEW_FILES = 8
MAX_FILE_CHARS = 3000
MAX_TOTAL_FILE_CHARS = 12000


def _clean_llm_text(text: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S | re.I)
    return cleaned.strip()


def _policy_safe_text(text: str, limit: int) -> str:
    """Fallback wording guard; primary policy control lives in the LLM prompt."""
    cleaned = str(text or "")
    replacements = {
        "应立即拒绝并隔离": "建议暂缓使用并处理风险",
        "立即拒绝并隔离": "建议暂缓使用并处理风险",
        "应立即拒绝": "建议暂缓使用",
        "立即拒绝": "建议暂缓使用",
        "建议拒绝发布": "建议暂缓发布并处理风险",
        "应拒绝发布": "建议暂缓发布并处理风险",
        "拒绝发布": "暂缓发布",
        "阻断发布": "暂缓发布",
        "自动阻断": "提示风险",
        "系统已拒绝": "系统已提示风险",
        "系统已阻断": "系统已提示风险",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    return cleaned[:limit]


def _json_candidates(text: str) -> list[str]:
    cleaned = _clean_llm_text(text)
    candidates: list[str] = []
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.S | re.I)
    candidates.extend(fenced)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        candidates.append(cleaned[start : end + 1])

    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        depth = 0
        in_string = False
        escaped = False
        for offset, current in enumerate(cleaned[index:], index):
            if in_string:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    in_string = False
                continue
            if current == '"':
                in_string = True
            elif current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(cleaned[index : offset + 1])
                    break
    return candidates


def _finding_brief(item: dict, index: int, category_labels: dict[str, str]) -> dict:
    loc = item.get("location") or {}
    locations = item.get("locations") or []
    evidence = item.get("evidence") or {}
    if locations and isinstance(locations, list):
        first_location = locations[0] if isinstance(locations[0], dict) else {}
        loc = {
            "file": first_location.get("file"),
            "start_line": first_location.get("start_line"),
        }
        snippet = str(first_location.get("snippet") or "")[:300]
    else:
        snippet = str(evidence.get("snippet") or evidence.get("matched_text") or "")[
            :300
        ]
    return {
        "index": index,
        "group_id": item.get("group_id") or f"group-{index}",
        "category": item.get("category") or "AST08",
        "category_name": category_labels.get(item.get("category"), "安全风险"),
        "scanner_severity": item.get("scanner_severity")
        or item.get("severity")
        or "unknown",
        "effective_severity": item.get("effective_severity")
        or item.get("severity")
        or "unknown",
        "finding_type": item.get("finding_type") or "true_risk",
        "file_role": item.get("file_role") or "unknown",
        "path_bucket": item.get("path_bucket") or "",
        "title": item.get("title") or "安全风险",
        "description": item.get("description") or "",
        "recommendation": item.get("recommendation") or "",
        "hit_count": item.get("hit_count") or 1,
        "file": loc.get("file") or "",
        "line": loc.get("start_line"),
        "evidence": snippet,
        "command_context": item.get("command_context") or {},
        "redline": bool(item.get("redline")),
    }


def _selection_finding_brief(item: dict) -> dict:
    locations = item.get("locations") or []
    first_location = (
        locations[0] if locations and isinstance(locations[0], dict) else {}
    )
    return {
        "group_id": item.get("group_id") or "",
        "category": item.get("category") or "",
        "severity": item.get("severity") or "",
        "title": item.get("title") or "",
        "file_role": item.get("file_role") or "",
        "file": first_location.get("file") or "",
        "hit_count": item.get("hit_count") or 1,
    }


def _compact_file_tree(file_tree: list[dict]) -> list[dict]:
    return [
        {
            "path": item.get("path"),
            "role": item.get("role"),
            "size": item.get("size"),
        }
        for item in file_tree[:200]
    ]


def _zip_file_tree(zip_path: str | None) -> list[dict]:
    if not zip_path or not zipfile.is_zipfile(zip_path):
        return []
    files: list[dict] = []
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                path = info.filename.lstrip("/")
                files.append(
                    {
                        "path": path,
                        "size": info.file_size,
                        "role": _file_role_for_prompt(path),
                    }
                )
    except Exception:  # noqa: BLE001
        return []
    return sorted(
        files,
        key=lambda item: (item["role"] != "runtime_entry", item["path"]),
    )


def _file_role_for_prompt(path: str) -> str:
    clean = (path or "").replace("\\", "/").lower()
    name = PurePosixPath(clean).name
    suffix = PurePosixPath(clean).suffix
    parts = set(PurePosixPath(clean).parts)
    if name in {"skill.md", "manifest.json", "ai-plugin.json"}:
        return "runtime_entry"
    if name in {"requirements.txt", "package.json", "package-lock.json"}:
        return "dependency_manifest"
    if suffix in {".py", ".sh", ".js", ".ts", ".mjs", ".cjs"}:
        return "executable_script"
    if parts & {"assets", "templates", "static", "public"} or suffix in {
        ".html",
        ".svg",
        ".css",
    }:
        return "template_asset"
    if suffix in {".md", ".txt", ".rst"} or name.startswith("readme"):
        return "documentation"
    return "unknown"


def _deterministic_selected_files(
    file_tree: list[dict], finding_briefs: list[dict]
) -> list[str]:
    paths: list[str] = []
    known = {item["path"] for item in file_tree}
    for item in file_tree:
        if item["role"] == "runtime_entry":
            paths.append(item["path"])
    for finding in finding_briefs:
        path = str(finding.get("file") or "")
        if path in known:
            paths.append(path)
    for item in file_tree:
        if item["role"] in {"executable_script", "dependency_manifest"}:
            paths.append(item["path"])
    deduped = list(dict.fromkeys(paths))
    return deduped[:MAX_REVIEW_FILES]


def _selected_paths_from_llm(parsed: dict, file_tree: list[dict]) -> list[str]:
    known = {item["path"] for item in file_tree}
    raw_items = parsed.get("selected_files") if isinstance(parsed, dict) else []
    if not isinstance(raw_items, list):
        return []
    paths: list[str] = []
    for item in raw_items:
        path = item.get("path") if isinstance(item, dict) else item
        if isinstance(path, str) and path in known:
            paths.append(path)
    return list(dict.fromkeys(paths))[:MAX_REVIEW_FILES]


def _read_review_files(zip_path: str | None, paths: list[str]) -> list[dict]:
    if not zip_path or not zipfile.is_zipfile(zip_path) or not paths:
        return []
    remaining = MAX_TOTAL_FILE_CHARS
    files: list[dict] = []
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for path in paths:
                if remaining <= 0:
                    break
                try:
                    raw = zf.read(path)
                except KeyError:
                    continue
                text = raw.decode("utf-8", errors="replace")
                content = text[: min(MAX_FILE_CHARS, remaining)]
                remaining -= len(content)
                files.append(
                    {
                        "path": path,
                        "role": _file_role_for_prompt(path),
                        "truncated": len(content) < len(text),
                        "content": content,
                    }
                )
    except Exception:  # noqa: BLE001
        return []
    return files


def _intent_review_files(files: list[dict]) -> list[dict]:
    remaining = 5000
    compact: list[dict] = []
    for item in files[:5]:
        if remaining <= 0:
            break
        content = str(item.get("content") or "")
        excerpt = content[: min(1200, remaining)]
        remaining -= len(excerpt)
        compact.append(
            {
                "path": item.get("path"),
                "role": item.get("role"),
                "truncated": bool(item.get("truncated") or len(excerpt) < len(content)),
                "content": excerpt,
            }
        )
    return compact


def _file_selection_prompt(prompt_payload: dict, retry: bool = False) -> list[dict]:
    user_prefix = "上一次输出未解析为合法 JSON。请重新输出。" if retry else ""
    schema = (
        '{"selected_files":[{"path":"SKILL.md","reason":"入口说明"}],'
        '"declared_intent":"Skill 声明用途"}'
    )
    return [
        {
            "role": "system",
            "content": (
                "你是 AIHelms 的 Skill 安全审查文件选择助手。请基于文件树、"
                "Skill 基本信息和规则命中摘要，选择后续需要读取原文的文件。"
                "优先选择入口说明、manifest、被命中文件、可执行脚本和依赖文件。"
                f"最多选择 {MAX_REVIEW_FILES} 个文件。只输出 JSON，不要解释。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"{user_prefix}请按此 JSON 结构输出：{schema}\n\n"
                f"输入：{json.dumps(prompt_payload, ensure_ascii=False)}"
            ),
        },
    ]


async def _select_review_files(
    model_name: str,
    api_key: str,
    user_id: str,
    metadata: dict,
    prompt_payload: dict,
    file_tree: list[dict],
    finding_briefs: list[dict],
) -> tuple[list[str], dict]:
    if not file_tree:
        return ([], {})
    result = await _chat_json(
        model_name,
        _file_selection_prompt(prompt_payload),
        api_key,
        user_id,
        metadata,
    )
    parsed = extract_json_object(result["content"])
    if not parsed:
        result = await _chat_json(
            model_name,
            _file_selection_prompt(prompt_payload, retry=True),
            api_key,
            user_id,
            metadata,
            True,
        )
        parsed = extract_json_object(result["content"])
    selected = _selected_paths_from_llm(parsed, file_tree)
    if not selected:
        selected = _deterministic_selected_files(file_tree, finding_briefs)
    return (selected, parsed if parsed else {})


def _intent_analysis_prompt(prompt_payload: dict, retry: bool = False) -> list[dict]:
    user_prefix = "上一次输出未解析为合法 JSON。请重新输出。" if retry else ""
    schema = {
        "intent_analysis": {
            "declared_intent": "该 Skill 声明用于把法规、合同或资料转换为结构化文档。",
            "actual_behavior": (
                "读取 Skill 包内入口说明、脚本和模板文件，生成 Markdown 或 HTML 报告。"
            ),
            "consistency": "基本一致",
            "basis": (
                "入口说明、被选中文件原文和规则扫描摘要均指向文档生成流程，"
                "未发现与声明用途明显不一致的行为。"
            ),
        }
    }
    return [
        {
            "role": "system",
            "content": (
                "你是 AIHelms 的 Skill 意图与行为分析助手。"
                "本次只做意图与行为分析，不做风险分类，不做逐条复核。"
                "只输出一个 JSON 对象，且必须包含 intent_analysis 字段；"
                "intent_analysis 下必须包含 declared_intent、actual_behavior、"
                "consistency、basis 四个字段，缺一不可。"
                "不要思维链，不要 markdown，不要解释。"
                "不要使用阻断、封禁、下架、驳回等执行性措辞。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"{user_prefix}请严格按以下 JSON 示例的字段结构输出，"
                "替换为基于输入证据得到的中文内容："
                f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
                f"输入：{json.dumps(prompt_payload, ensure_ascii=False)}"
            ),
        },
    ]


def _intent_analysis_from_parsed(parsed: dict) -> dict:
    if not isinstance(parsed, dict):
        return {}
    return llm_intent_analysis(parsed)


async def _run_intent_analysis(
    model_name: str,
    api_key: str,
    user_id: str,
    metadata: dict,
    prompt_payload: dict,
) -> tuple[dict, dict]:
    result = await _chat_json(
        model_name,
        _intent_analysis_prompt(prompt_payload),
        api_key,
        user_id,
        metadata,
        max_tokens=1000,
    )
    parsed = extract_json_object(result["content"])
    if not parsed:
        result = await _chat_json(
            model_name,
            _intent_analysis_prompt(prompt_payload, retry=True),
            api_key,
            user_id,
            metadata,
            True,
            max_tokens=1000,
        )
        parsed = extract_json_object(result["content"])
    intent_analysis = _intent_analysis_from_parsed(parsed)
    return intent_analysis, _part_state(intent_analysis, result)




def is_supported_review_model(model: Any) -> bool:
    if not model or not getattr(model, "is_active", False):
        return False
    if (getattr(model, "category", "chat") or "chat") != "chat":
        return False
    for deployment in getattr(model, "deployments", []) or []:
        if not getattr(deployment, "is_active", False):
            continue
        credential = getattr(deployment, "credential", None)
        if not credential or not getattr(credential, "is_active", False):
            continue
        credential_info = getattr(credential, "credential_info", None) or {}
        if str(credential_info.get("format") or "openai").lower() == "openai":
            return True
    return False


async def get_supported_review_model(
    session: AsyncSession,
    model_id: int | None,
) -> Any | None:
    if not model_id:
        return None
    model = await model_repo.find_by_id(session, model_id)
    return model if is_supported_review_model(model) else None


def _parse_json_candidate(candidate: str) -> dict:
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def extract_json_object(text: str) -> dict:
    for candidate in _json_candidates(text):
        parsed = _parse_json_candidate(candidate)
        if parsed:
            return parsed
    return {}


def _normalize_lookup(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_severity(value: Any) -> str:
    raw = _normalize_lookup(value)
    mapping = {
        "critical": "critical",
        "严重": "critical",
        "严重风险": "critical",
        "高严重": "critical",
        "high": "high",
        "高": "high",
        "高危": "high",
        "高风险": "high",
        "medium": "medium",
        "中": "medium",
        "中危": "medium",
        "中风险": "medium",
        "low": "low",
        "低": "low",
        "低危": "low",
        "低风险": "low",
        "info": "info",
        "提示": "info",
        "建议复核": "info",
        "review": "info",
        "review_note": "info",
        "none": "none",
        "无": "none",
        "未发现": "none",
        "未发现明确风险": "none",
    }
    if raw in {"critical", "high", "medium", "low", "info", "none"}:
        return raw
    return mapping.get(raw, "info")


def _normalize_confidence(value: Any) -> str:
    raw = _normalize_lookup(value)
    mapping = {
        "high": "high",
        "高": "high",
        "高置信": "high",
        "medium": "medium",
        "中": "medium",
        "中等": "medium",
        "low": "low",
        "低": "low",
    }
    return mapping.get(raw, "low")


def _normalize_finding_type(value: Any) -> str:
    raw = _normalize_lookup(value)
    mapping = {
        "true_risk": "true_risk",
        "risk": "true_risk",
        "real_risk": "true_risk",
        "需处理": "true_risk",
        "建议处理": "true_risk",
        "存在风险": "true_risk",
        "确认风险": "true_risk",
        "false_positive": "false_positive",
        "falsepositive": "false_positive",
        "误报": "false_positive",
        "未发现明确风险": "false_positive",
        "review_note": "review_note",
        "review": "review_note",
        "needs_review": "review_note",
        "建议复核": "review_note",
        "需复核": "review_note",
        "扫描限制": "review_note",
    }
    return mapping.get(raw, "review_note")


def _normalize_consistency(value: Any) -> str:
    raw = str(value or "").strip()
    normalized = _normalize_lookup(raw)
    mapping = {
        "highly_consistent": "高度一致",
        "consistent": "基本一致",
        "mostly_consistent": "基本一致",
        "partial": "存在偏差",
        "partially_consistent": "存在偏差",
        "inconsistent": "不一致",
        "needs_review": "建议复核",
        "review": "建议复核",
        "高度一致": "高度一致",
        "基本一致": "基本一致",
        "存在偏差": "存在偏差",
        "不一致": "不一致",
        "建议复核": "建议复核",
    }
    return mapping.get(normalized, raw[:40])


def _part_state(parsed_value: Any, response_state: dict) -> dict:
    if parsed_value:
        return {"status": "completed", "message": ""}
    if response_state.get("truncated"):
        return {"status": "unparsed", "message": "模型输出被截断，未形成可展示内容"}
    if response_state.get("empty"):
        return {"status": "unparsed", "message": "模型未返回可展示内容"}
    return {"status": "unparsed", "message": "模型输出未解析为合法 JSON"}


def llm_category_reviews(
    parsed: dict, findings: list[dict], category_labels: dict[str, str]
) -> list[dict]:
    raw_items = parsed.get("category_reviews") if isinstance(parsed, dict) else []
    reviews: list[dict] = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code") or "").upper()
            if code not in category_labels:
                continue
            result = str(item.get("result") or "").strip()
            reason = str(item.get("reason") or "").strip()
            recommendation = str(item.get("recommendation") or "").strip()
            if not result and not reason and not recommendation:
                continue
            reviews.append(
                {
                    "code": code,
                    "name": category_labels[code],
                    "result": _policy_safe_text(result, 32),
                    "reason": _policy_safe_text(reason, 500),
                    "recommendation": _policy_safe_text(recommendation, 500),
                }
            )
    reviewed_codes = {item["code"] for item in reviews}
    for code in sorted(
        {item.get("category") for item in findings if item.get("category")}
    ):
        if code not in category_labels or code in reviewed_codes:
            continue
        reviews.append(
            {
                "code": code,
                "name": category_labels[code],
                "result": "LLM 未单独研判",
                "reason": "",
                "recommendation": "",
            }
        )
    return reviews


def llm_finding_reviews(parsed: dict, findings: list[dict]) -> list[dict]:
    raw_items = parsed.get("finding_reviews") if isinstance(parsed, dict) else []
    if not isinstance(raw_items, list):
        return []
    known_ids = {str(item.get("group_id")) for item in findings if item.get("group_id")}
    reviews: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        group_id = str(
            item.get("group_id")
            or item.get("groupId")
            or item.get("id")
            or ""
        )
        if group_id not in known_ids:
            continue
        finding_type = _normalize_finding_type(
            item.get("finding_type") or item.get("findingType") or item.get("result")
        )
        effective_severity = _normalize_severity(
            item.get("effective_severity")
            or item.get("effectiveSeverity")
            or item.get("severity")
        )
        confidence = _normalize_confidence(item.get("confidence"))
        reviews.append(
            {
                "group_id": group_id,
                "finding_type": finding_type,
                "effective_severity": effective_severity,
                "counts_toward_score": bool(item.get("counts_toward_score")),
                "confidence": confidence,
                "reason": _policy_safe_text(item.get("reason") or "", 700),
                "recommendation": _policy_safe_text(
                    item.get("recommendation") or "", 700
                ),
            }
        )
    return reviews


def llm_intent_analysis(parsed: dict) -> dict:
    raw = parsed.get("intent_analysis") if isinstance(parsed, dict) else None
    if not isinstance(raw, dict):
        return {}
    declared_intent = _policy_safe_text(
        raw.get("declared_intent") or raw.get("declaredIntent") or "", 400
    )
    actual_behavior = _policy_safe_text(
        raw.get("actual_behavior") or raw.get("actualBehavior") or "", 700
    )
    consistency = _normalize_consistency(raw.get("consistency") or "")
    basis = _policy_safe_text(raw.get("basis") or raw.get("evidence") or "", 900)
    if not any([declared_intent, actual_behavior, consistency, basis]):
        return {}
    return {
        "declared_intent": declared_intent,
        "actual_behavior": actual_behavior,
        "consistency": consistency,
        "basis": basis,
    }


def _content_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
                elif isinstance(text, dict) and isinstance(text.get("value"), str):
                    parts.append(text["value"])
        return "".join(parts)
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        if isinstance(value.get("value"), str):
            return value["value"]
    return ""


def _response_content(response: dict) -> str:
    choices = response.get("choices") if isinstance(response, dict) else None
    if isinstance(choices, list) and choices:
        choice = choices[0] if isinstance(choices[0], dict) else {}
        message = choice.get("message") if isinstance(choice, dict) else None
        if isinstance(message, dict):
            content = _content_text(message.get("content"))
            if content:
                return content
        content = _content_text(choice.get("text"))
        if content:
            return content
    output_text = (
        _content_text(response.get("output_text"))
        if isinstance(response, dict)
        else ""
    )
    if output_text:
        return output_text
    output = response.get("output") if isinstance(response, dict) else None
    if isinstance(output, list):
        return _content_text(
            [
                content
                for item in output
                if isinstance(item, dict)
                for content in [item.get("content") or item.get("text")]
            ]
        )
    return ""


def _finish_reason(response: dict) -> str:
    choices = response.get("choices") if isinstance(response, dict) else None
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        return str(
            choices[0].get("finish_reason")
            or choices[0].get("finishReason")
            or ""
        )
    return str(response.get("finish_reason") or response.get("status") or "")


def _response_state(response: dict, content: str) -> dict:
    finish_reason = _normalize_lookup(_finish_reason(response))
    return {
        "content": content,
        "finish_reason": finish_reason,
        "empty": not bool(content.strip()),
        "truncated": finish_reason in {"length", "max_tokens", "incomplete"},
    }


def _review_metadata(audit: Any, user: Any, key: Any) -> dict:
    return {
        "aihelms_feature": "ai_policies_skill_audit",
        "aihelms_audit_id": getattr(audit, "audit_id", ""),
        "aihelms_skill_id": getattr(audit, "skill_id", None),
        "aihelms_skill_name": getattr(audit, "skill_name", ""),
        "aihelms_user_id": getattr(user, "id", None),
        "aihelms_username": getattr(user, "username", ""),
        "aihelms_ai_key_id": getattr(key, "id", None),
        "aihelms_ai_key_alias": getattr(key, "litellm_key_alias", ""),
    }


async def _chat_json(
    model_name: str,
    messages: list[dict],
    api_key: str,
    user_id: str,
    metadata: dict,
    retry: bool = False,
    max_tokens: int = 1600,
) -> dict:
    common_kwargs = {
        "temperature": 0,
        "max_tokens": max_tokens,
        "timeout": 90,
        "api_key": api_key,
        "user": user_id,
        "metadata": metadata,
        "extra_body": {"thinking": {"type": "disabled"}},
    }
    try:
        response = await litellm_client.chat_completion(
            model_name,
            messages,
            response_format={"type": "json_object"},
            **common_kwargs,
        )
    except Exception as exc:
        message = str(exc).lower()
        can_retry_without_options = any(
            marker in message
            for marker in ("response_format", "json_object", "extra_body", "thinking")
        )
        if not can_retry_without_options:
            raise
        response = await litellm_client.chat_completion(
            model_name,
            messages,
            **{
                key: value
                for key, value in common_kwargs.items()
                if key != "extra_body"
            },
        )
    content = _response_content(response)
    if content:
        return _response_state(response, content)
    response = await litellm_client.chat_completion(
        model_name,
        messages,
        **{key: value for key, value in common_kwargs.items() if key != "extra_body"},
    )
    return _response_state(response, _response_content(response))


def _review_prompt(prompt_payload: dict, retry: bool = False) -> list[dict]:
    schema = {
        "overall_judgement": "发现 1 处供应链依赖风险，建议固定依赖版本。",
        "reason": "规则命中的 npx 命令未固定版本，安装时可能拉取到不同版本的包。",
        "finding_reviews": [
            {
                "group_id": "AIPG_xxx",
                "finding_type": "true_risk",
                "effective_severity": "low",
                "counts_toward_score": True,
                "confidence": "high",
                "reason": "该命令会在运行时解析依赖版本，证据与供应链风险一致。",
                "recommendation": "固定到明确版本，例如 npx @scope/server@1.2.3。",
            }
        ],
    }
    user_prefix = "上一次输出未解析为合法 JSON。请重新输出。" if retry else ""
    return [
        {
            "role": "system",
            "content": (
                "你是 AIHelms 的 Skill 安全审查复核助手。扫描器命中只是线索，"
                "不等于最终风险。你的任务不是复述扫描结果，而是基于 Skill 用途、"
                "文件角色、证据片段和规则命中，判断每个风险组是否构成"
                "真实可执行的安全风险。"
                "本次只做逐条风险复核，不做意图分析，不输出分类摘要。"
                "只输出一个 JSON 对象，且必须包含 finding_reviews 字段。"
                "finding_reviews 中必须使用输入里的 group_id，不要自造 id。"
                "AIHelms 只提供审查建议，不自动阻断发布；不要使用系统已拒绝、"
                "系统已阻断、必须隔离、封禁、禁止上线、下架、驳回等执行性措辞，"
                "只能表达建议处理、建议复核、建议暂缓并确认、未发现明确风险。"
                "证据不足必须降为建议复核，不得推断高危。扫描器诊断、网络超时、"
                "漏洞库不可达不是 Skill 风险，不得作为安全结论。"
                "documentation、template_asset、example_or_test 中的普通说明、"
                "模板占位符、HTML/SVG 文本、README 示例通常不是提示注入。"
                "subprocess 使用 list 参数且 shell=False，调用 pandoc、mmdc、"
                "ffmpeg 等本地固定工具，并且参数是静态值或文件路径时，通常"
                "未发现明确命令注入风险。只有用户可控值可能被工具当成选项、"
                "片段不完整或字符串拼接混入外部输入时，才标为建议复核。"
                "反向 shell、curl|bash、wget|sh、nc -e、凭证外传、破坏性"
                "系统命令、eval/exec/pickle.loads 且数据来自外部输入属于红线，"
                "不能降为误报。"
                "不要暴露 file_role、shell=True、finding group、false_positive "
                "等内部字段名。"
                "只输出一个 JSON 对象，不要思维链，不要 markdown，不要解释文字。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"{user_prefix}请按 OWASP Agentic Skills Top 10 风险分类，"
                "对以下 Skill 审查结果逐个风险组做 AI 深度复核。"
                "输出必须严格按以下 JSON 示例的字段结构，"
                "替换为基于输入证据得到的中文内容："
                f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
                f"输入：{json.dumps(prompt_payload, ensure_ascii=False)}"
            ),
        },
    ]


async def run_llm_review(
    session: AsyncSession,
    model_id: int | None,
    audit: Any,
    findings: list[dict],
    category_labels: dict[str, str],
    zip_path: str | None = None,
) -> dict:
    if not model_id:
        return {"status": "skipped", "message": "未选择审查模型"}
    model = await get_supported_review_model(session, model_id)
    if not model:
        return {"status": "skipped", "message": "配置的审查模型不可用"}
    model_name = model.model_id or model.name
    if not model_name:
        return {"status": "skipped", "message": "配置的审查模型不可用"}
    user = await user_repo.find_user_by_id(
        session, int(getattr(audit, "created_by", 0) or 0)
    )
    if not user or not getattr(user, "is_active", False):
        return {"status": "skipped", "message": "发起审查的管理员账号不可用"}
    key = await ai_key_repo.find_personal_main(session, user.id)
    if not key or not key.is_active or not key.litellm_key_id:
        return {
            "status": "skipped",
            "message": "发起审查的管理员未配置可用的个人主 Key",
        }
    if "*" not in (key.models or []) and model_name not in (key.models or []):
        return {
            "status": "skipped",
            "message": "发起审查的管理员主 Key 无权访问审查模型",
        }
    litellm_user_id = user.litellm_user_id or f"aihelms_user_{user.id}"
    metadata = _review_metadata(audit, user, key)

    reviewable_findings = [
        item for item in findings if not item.get("redline")
    ][:10]
    finding_briefs = [
        _finding_brief(item, index, category_labels)
        for index, item in enumerate(reviewable_findings, 1)
    ]
    file_tree = _zip_file_tree(zip_path)
    prompt_payload = {
        "audit_id": audit.audit_id,
        "skill_name": audit.skill_name,
        "skill_version": audit.skill_version,
        "declared_purpose": getattr(audit, "skill_description", "") or "",
        "risk_score": audit.risk_score,
        "severity": audit.severity,
        "findings": finding_briefs,
        "categories": category_labels,
    }
    if not finding_briefs and not file_tree:
        return {
            "status": "skipped",
            "model_id": model.id,
            "model": model.name or model_name,
            "message": "没有需要 AI 复核的风险组",
            "finding_reviews": [],
            "category_reviews": [],
            "intent_analysis": {},
        }
    selection_payload = {
        "skill_name": audit.skill_name,
        "skill_version": audit.skill_version,
        "declared_purpose": getattr(audit, "skill_description", "") or "",
        "file_tree": _compact_file_tree(file_tree),
        "findings": [_selection_finding_brief(item) for item in reviewable_findings],
    }
    selected_files, selection_result = await _select_review_files(
        model_name,
        key.litellm_key_id,
        litellm_user_id,
        metadata,
        selection_payload,
        file_tree,
        finding_briefs,
    )
    prompt_payload["selected_files"] = _read_review_files(zip_path, selected_files)
    prompt_payload["file_selection"] = {
        "selected_paths": selected_files,
        "declared_intent": selection_result.get("declared_intent", ""),
    }
    intent_payload = {
        "skill_name": audit.skill_name,
        "skill_version": audit.skill_version,
        "declared_purpose": getattr(audit, "skill_description", "") or "",
        "file_selection_declared_intent": selection_result.get("declared_intent", ""),
        "selected_files": _intent_review_files(prompt_payload["selected_files"]),
        "findings": finding_briefs,
    }
    intent_analysis, intent_state = await _run_intent_analysis(
        model_name,
        key.litellm_key_id,
        litellm_user_id,
        metadata,
        intent_payload,
    )
    parsed: dict = {}
    review_result = {"content": "", "empty": True, "truncated": False}
    if finding_briefs:
        review_result = await _chat_json(
            model_name,
            _review_prompt(prompt_payload),
            key.litellm_key_id,
            litellm_user_id,
            metadata,
            max_tokens=2200,
        )
        parsed = extract_json_object(review_result["content"])
    if finding_briefs and not parsed:
        review_result = await _chat_json(
            model_name,
            _review_prompt(prompt_payload, retry=True),
            key.litellm_key_id,
            litellm_user_id,
            metadata,
            True,
            max_tokens=2200,
        )
        parsed = extract_json_object(review_result["content"])
    finding_reviews = llm_finding_reviews(parsed, reviewable_findings) if parsed else []
    finding_state = (
        _part_state(finding_reviews, review_result)
        if finding_briefs
        else {"status": "skipped", "message": "没有需要复核的风险组"}
    )
    status = "completed" if finding_reviews or intent_analysis else "unparsed"
    messages = [
        state["message"]
        for state in (intent_state, finding_state)
        if state.get("status") != "completed" and state.get("message")
    ]
    return {
        "status": status,
        "model_id": model.id,
        "model": model.name or model_name,
        "overall_judgement": _policy_safe_text(
            parsed.get("overall_judgement") or "", 500
        ),
        "reason": _policy_safe_text(parsed.get("reason") or "", 1000),
        "finding_reviews": finding_reviews if status == "completed" else [],
        "category_reviews": [],
        "intent_analysis": intent_analysis if status == "completed" else {},
        "selected_files": selected_files if status == "completed" else [],
        "parts": {
            "intent_analysis": intent_state,
            "finding_reviews": finding_state,
        },
        "message": ""
        if status == "completed"
        else "；".join(messages)
        or "LLM 语义研判未完成（结果未解析），本报告以静态审查结果为准",
        "raw_text": _clean_llm_text(review_result["content"])[:1200]
        if status != "completed"
        else "",
    }

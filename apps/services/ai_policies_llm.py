import json
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from repositories import ai_key_repo, model_repo, user_repo
from services import litellm_client


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
        snippet = str(first_location.get("snippet") or "")[:800]
    else:
        snippet = str(evidence.get("snippet") or evidence.get("matched_text") or "")[
            :800
        ]
    return {
        "index": index,
        "category": item.get("category") or "AST08",
        "category_name": category_labels.get(item.get("category"), "安全风险"),
        "severity": item.get("severity") or "unknown",
        "title": item.get("title") or "安全风险",
        "description": item.get("description") or "",
        "recommendation": item.get("recommendation") or "",
        "hit_count": item.get("hit_count") or 1,
        "file": loc.get("file") or "",
        "line": loc.get("start_line"),
        "evidence": snippet,
    }




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


def _response_content(response: dict) -> str:
    choices = response.get("choices") if isinstance(response, dict) else None
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return ""
    return str(message.get("content") or "")


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
) -> str:
    try:
        response = await litellm_client.chat_completion(
            model_name,
            messages,
            temperature=0,
            max_tokens=1600,
            timeout=90,
            response_format={"type": "json_object"},
            api_key=api_key,
            user=user_id,
            metadata=metadata,
        )
    except Exception as exc:
        message = str(exc).lower()
        if "response_format" not in message and "json_object" not in message:
            raise
        response = await litellm_client.chat_completion(
            model_name,
            messages,
            temperature=0,
            max_tokens=1600,
            timeout=90,
            api_key=api_key,
            user=user_id,
            metadata=metadata,
        )
    content = _response_content(response)
    if content or retry:
        return content
    return ""


def _review_prompt(prompt_payload: dict, retry: bool = False) -> list[dict]:
    schema = (
        '{"overall_judgement":"一句总体判断",'
        '"reason":"基于输入证据给出具体原因",'
        '"category_reviews":[{"code":"AST02",'
        '"result":"需处理/建议复核/未发现问题",'
        '"reason":"模型对该分类的具体研判",'
        '"recommendation":"处理建议"}]}'
    )
    user_prefix = "上一次输出未解析为合法 JSON。请重新输出。" if retry else ""
    return [
        {
            "role": "system",
            "content": (
                "你是 AIHelms 的 Skill 安全审查助手。只能基于输入的规则扫描结果、"
                "文件位置和证据片段做中文研判，不要编造未给出的文件内容。"
                "本产品只提供审查建议，不自动阻断发布；不要使用系统已拒绝、"
                "系统已阻断、必须隔离、封禁、禁止上线、下架、驳回等执行性措辞，"
                "只能表达建议处理、建议复核。"
                "只输出一个 JSON 对象，不要思维链，不要 markdown，不要解释文字。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"{user_prefix}请按 OWASP Agentic Skills Top 10 风险分类，"
                "对以下 Skill 审查结果做 AI 深度分析。"
                f"输出必须严格符合此 JSON 结构：{schema}\n\n"
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

    finding_briefs = [
        _finding_brief(item, index, category_labels)
        for index, item in enumerate(findings[:30], 1)
    ]
    prompt_payload = {
        "audit_id": audit.audit_id,
        "skill_name": audit.skill_name,
        "skill_version": audit.skill_version,
        "risk_score": audit.risk_score,
        "severity": audit.severity,
        "findings": finding_briefs,
        "categories": category_labels,
    }
    content = await _chat_json(
        model_name,
        _review_prompt(prompt_payload),
        key.litellm_key_id,
        litellm_user_id,
        metadata,
    )
    parsed = extract_json_object(content)
    if not parsed:
        content = await _chat_json(
            model_name,
            _review_prompt(prompt_payload, retry=True),
            key.litellm_key_id,
            litellm_user_id,
            metadata,
            True,
        )
        parsed = extract_json_object(content)
    reviews = llm_category_reviews(parsed, findings, category_labels) if parsed else []
    has_valid_reviews = any(
        item.get("result") != "LLM 未单独研判"
        and (item.get("result") or item.get("reason") or item.get("recommendation"))
        for item in reviews
    )
    status = "completed" if parsed and has_valid_reviews else "unparsed"
    return {
        "status": status,
        "model_id": model.id,
        "model": model.name or model_name,
        "overall_judgement": _policy_safe_text(
            parsed.get("overall_judgement") or "", 500
        ),
        "reason": _policy_safe_text(parsed.get("reason") or "", 1000),
        "category_reviews": reviews if status == "completed" else [],
        "message": ""
        if status == "completed"
        else "LLM 语义研判未完成（结果未解析），本报告以静态审查结果为准",
        "raw_text": _clean_llm_text(content)[:1200] if status != "completed" else "",
    }

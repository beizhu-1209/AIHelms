import hashlib
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_worker_session_factory
from exceptions import ConflictError, NotFoundError, ValidationError
from models.db import AiPoliciesAudit
from repositories import ai_policies_repo, skill_repo
from services import ai_policies_llm, ai_policies_report, ai_policies_scanner_client

logger = logging.getLogger(__name__)

SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0, "": 0}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt_time(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scanner_target(zip_path: str) -> str:
    return f"skills/{Path(zip_path).name}"


def _decision(risk_score: int, severity: str, findings: list[dict]) -> str:
    if risk_score >= 70 or severity == "CRITICAL":
        return "high_risk"
    if findings:
        return "attention_required"
    return "passed"


def _map_category(raw: dict) -> str:
    category = str(raw.get("category") or "")
    rule_id = str(raw.get("id") or "")
    pattern = str(raw.get("pattern") or "")
    tags = " ".join(str(tag) for tag in raw.get("tags") or [])
    text = f"{category} {rule_id} {pattern} {tags}".lower()
    if "prompt injection" in text:
        return "AST05"
    if (
        "data exfiltration" in text
        or "data flow" in text
        or "tainted flow" in text
        or "external transmission" in text
    ):
        return "AST10"
    if "reverse_shell" in text or "dangerous code" in text or "tool misuse" in text:
        return "AST06"
    if (
        "rug pull" in text
        or "npx" in text
        or "supply chain" in text
        or "unpinned dependencies" in text
        or "remote script" in text
        or "external script" in text
    ):
        return "AST02"
    if "privilege" in text or "least privilege" in text:
        return "AST03"
    if "metadata" in text or "manifest" in text:
        return "AST04"
    return "AST08"


def _finding_text(raw: dict, category: str) -> tuple[str, str, str]:
    raw_category = str(raw.get("category") or "")
    rule_id = str(raw.get("id") or "")
    pattern = str(raw.get("pattern") or "")
    text = f"{raw_category} {rule_id} {pattern}".lower()

    if "rug pull" in text or rule_id == "RP1":
        return (
            "未固定 npx 包版本",
            "依赖未固定版本，存在被替换或投毒的风险。",
            "固定到明确版本，如 npx @scope/server@1.2.3。",
        )
    if rule_id == "SC1":
        return (
            "依赖版本未固定",
            "依赖未锁定明确版本，后续安装可能引入非预期版本。",
            "固定依赖版本，并在升级版本时重新审查。",
        )
    if rule_id == "SC2":
        return (
            "从外部地址拉取脚本",
            "安装或运行过程中会从外部地址下载脚本，存在被替换或投毒的风险。",
            "移除远程脚本执行；确需保留时固定来源、校验哈希并说明用途。",
        )
    if rule_id == "PE2":
        return (
            "使用 sudo 或 root 权限",
            "Skill 中存在提权执行行为，可能影响宿主环境或扩大操作范围。",
            "删除不必要的提权命令；确需使用时限定命令范围并补充权限说明。",
        )
    if rule_id == "PE3":
        return (
            "读取凭证或敏感文件",
            "检测到读取密钥、凭证或系统敏感路径的行为。",
            "移除凭证读取逻辑；确需访问时限定文件范围并避免外传。",
        )
    if "prompt injection" in text:
        return (
            "存在提示注入相关风险",
            "检测到可能影响系统指令边界的提示内容，可能导致模型忽略原有规则或执行非预期任务。",
            "明确区分系统指令、用户输入和外部内容，对不可信内容增加边界说明和转义处理。",
        )
    if rule_id == "AST4":
        return (
            "调用系统命令执行代码",
            "检测到脚本或程序调用系统命令，存在执行非预期命令的风险。",
            "减少系统命令调用；保留必要调用时校验输入并限制命令范围。",
        )
    if "data exfiltration" in text or rule_id in {"E1", "TT4"}:
        return (
            "存在数据外传风险",
            "检测到可能向外部位置发送文件、上下文或敏感字段的行为。",
            "核实外传目的、范围和必要性，补充权限说明；不必要的外传逻辑应删除。",
        )
    if rule_id == "TM1":
        return (
            "工具参数权限过宽",
            "工具调用包含高权限或宽范围参数，可能扩大 Skill 的实际操作能力。",
            "收紧工具参数，删除不必要的 root、全量环境变量或全局写入权限。",
        )
    if rule_id == "TM2":
        return (
            "工具链串联执行风险",
            "多个工具或命令被串联执行，失败边界和输入边界不清晰。",
            "拆分高风险链路，限制每一步输入输出，并保留必要的错误处理。",
        )
    if rule_id == "YR1" and "reverse_shell" in text:
        return (
            "检测到反向 Shell 特征",
            "文件中包含反向连接或远程控制相关片段，存在严重执行风险。",
            "删除相关 payload，并检查 Skill 包内是否还有同类后门代码。",
        )
    if rule_id == "YR1" and "remote_bootstrap" in text:
        return (
            "远程脚本下载后执行",
            "检测到下载远程脚本或代码后继续执行的行为，存在供应链投毒风险。",
            "移除远程下载执行链路；确需保留时固定来源并校验内容完整性。",
        )
    if rule_id == "YR4":
        return (
            "隐藏提示注入指令",
            "Skill 文本中存在隐藏或绕过类指令，可能干扰模型遵循平台策略。",
            "删除隐藏指令，明确外部内容边界，并避免要求模型忽略既有规则。",
        )
    if "dangerous code" in text or "tool misuse" in text:
        return (
            "存在高风险工具或代码调用",
            "检测到可能执行系统命令、脚本或高权限工具的内容。",
            "限制工具调用范围，删除不必要的系统命令；保留必要能力时应说明使用边界和输入校验方式。",
        )

    title = raw_category or "安全风险"
    if pattern:
        title = f"{title} - {pattern}"
    return (
        title,
        raw.get("explanation")
        or "规则扫描发现风险，请结合文件位置和业务用途复核。",
        raw.get("remediation") or "请结合文件和业务用途复核。",
    )


def _zip_snippet(
    zip_path: str, file_name: str, start_line: int | None, end_line: int | None = None
) -> str:
    if (
        not file_name
        or not start_line
        or not zip_path
        or not zipfile.is_zipfile(zip_path)
    ):
        return ""
    normalized = file_name.lstrip("/")
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            member = next((name for name in names if name == normalized), None)
            if not member:
                member = next(
                    (name for name in names if name.endswith(f"/{normalized}")), None
                )
            if not member:
                return ""
            content = zf.read(member).decode("utf-8", errors="replace").splitlines()
    except Exception:  # noqa: BLE001
        return ""

    start = max(1, int(start_line) - 2)
    stop_line = int(end_line or start_line)
    stop = min(len(content), stop_line + 2)
    width = len(str(stop))
    return "\n".join(
        f"{line_no:>{width}} | {content[line_no - 1]}"
        for line_no in range(start, stop + 1)
    )


def _normalize_finding(raw: dict, zip_path: str = "") -> dict:
    location = raw.get("location") or {}
    severity = str(raw.get("severity") or "LOW").upper()
    category = _map_category(raw)
    title, description, recommendation = _finding_text(raw, category)
    file_name = location.get("file") or ""
    start_line = location.get("start_line")
    end_line = location.get("end_line")
    snippet = raw.get("code_snippet") or _zip_snippet(
        zip_path, file_name, start_line, end_line
    )
    return {
        "source": "static",
        "rule_id": raw.get("id") or "",
        "category": category,
        "raw_category": raw.get("category") or "",
        "severity": severity.lower(),
        "confidence": raw.get("confidence") or 0,
        "title": title,
        "description": description,
        "recommendation": recommendation,
        "location": {
            "file": file_name,
            "start_line": start_line,
            "end_line": end_line,
        },
        "evidence": {
            "snippet": snippet,
            "matched_text": raw.get("finding") or "",
        },
        "must_review": severity in {"HIGH", "CRITICAL"},
    }


def _normalize_findings(raw_findings: list[dict], zip_path: str = "") -> list[dict]:
    return [_normalize_finding(item, zip_path) for item in raw_findings]


def _severity_max(current: str, candidate: str) -> str:
    if SEVERITY_RANK.get(candidate, 0) > SEVERITY_RANK.get(current, 0):
        return candidate
    return current


def _finding_location(item: dict) -> dict:
    loc = item.get("location") or {}
    evidence = item.get("evidence") or {}
    return {
        "file": loc.get("file") or "",
        "start_line": loc.get("start_line"),
        "end_line": loc.get("end_line"),
        "snippet": evidence.get("snippet") or evidence.get("matched_text") or "",
    }


def _aggregate_findings(findings: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str, str], dict] = {}
    for item in findings:
        key = (
            str(item.get("rule_id") or ""),
            str(item.get("category") or ""),
            str(item.get("title") or ""),
        )
        if key not in groups:
            groups[key] = {
                "source": item.get("source") or "static",
                "rule_id": item.get("rule_id") or "",
                "category": item.get("category") or "",
                "raw_category": item.get("raw_category") or "",
                "severity": item.get("severity") or "unknown",
                "confidence": item.get("confidence") or 0,
                "title": item.get("title") or "安全风险",
                "description": item.get("description") or "",
                "recommendation": item.get("recommendation") or "",
                "hit_count": 0,
                "locations": [],
                "must_review": False,
            }
        group = groups[key]
        group["severity"] = _severity_max(group["severity"], item.get("severity") or "")
        group["confidence"] = max(
            group.get("confidence") or 0,
            item.get("confidence") or 0,
        )
        group["hit_count"] += 1
        group["locations"].append(_finding_location(item))
        group["must_review"] = bool(group["must_review"] or item.get("must_review"))

    return sorted(
        groups.values(),
        key=lambda item: (
            -SEVERITY_RANK.get(item.get("severity") or "", 0),
            item.get("category") or "",
            item.get("title") or "",
        ),
    )


def _is_grouped_finding(item: dict) -> bool:
    return "hit_count" in item or isinstance(item.get("locations"), list)


def _localized_finding(item: dict) -> dict:
    raw = {
        "id": item.get("rule_id") or "",
        "category": item.get("raw_category") or item.get("category") or "",
        "pattern": item.get("pattern") or item.get("title") or "",
    }
    category = _map_category(raw)
    title, description, recommendation = _finding_text(raw, category)
    return {
        **item,
        "category": category,
        "raw_category": item.get("raw_category") or raw["category"],
        "title": title,
        "description": description,
        "recommendation": recommendation,
    }


def _display_findings(findings: list[dict]) -> list[dict]:
    if not findings:
        return []
    if all(_is_grouped_finding(item) for item in findings):
        return sorted(
            findings,
            key=lambda item: (
                -SEVERITY_RANK.get(item.get("severity") or "", 0),
                item.get("category") or "",
                item.get("title") or "",
            ),
        )
    localized = [_localized_finding(item) for item in findings]
    return _aggregate_findings(localized)


def _severity_counts(findings: list[dict]) -> dict:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for item in findings:
        severity = item.get("severity") or "unknown"
        if severity in counts:
            counts[severity] += int(item.get("hit_count") or 1)
    return counts


def _llm_review_completed(llm_review: dict | None) -> bool:
    if not llm_review or llm_review.get("status") != "completed":
        return False
    reviews = llm_review.get("category_reviews")
    if not isinstance(reviews, list):
        return False
    return any(
        isinstance(item, dict)
        and item.get("result") != "LLM 未单独研判"
        and (item.get("result") or item.get("reason") or item.get("recommendation"))
        for item in reviews
    )


def _display_llm_review(llm_review: dict | None, used: bool) -> dict | None:
    if not isinstance(llm_review, dict):
        return None
    cleaned = {**llm_review}
    if not used or cleaned.get("status") != "completed":
        cleaned["category_reviews"] = []
        cleaned["overall_judgement"] = ""
        cleaned["reason"] = ""
        cleaned["message"] = cleaned.get("message") or (
            "LLM 语义研判未完成，本报告以规则扫描结果为准"
        )
    return cleaned


def _display_summary(audit: AiPoliciesAudit, findings: list[dict]) -> dict:
    summary = {**(audit.summary or {})}
    llm_review = _display_llm_review(
        summary.get("llm_review") if isinstance(summary, dict) else None,
        audit.llm_review_used,
    )
    if llm_review:
        summary["llm_review"] = llm_review
    summary["severity_counts"] = _severity_counts(findings)
    summary["llm_review_used"] = audit.llm_review_used
    summary["llm_review_model"] = audit.llm_review_model
    return summary


def _serialize_catalog_item(item) -> dict:
    return {
        "code": item.code,
        "name_en": item.name_en,
        "name_zh": item.name_zh,
        "severity": item.severity,
        "description_zh": item.description_zh,
        "check_points": item.check_points or [],
        "sort_order": item.sort_order,
    }


async def _catalog_items(session: AsyncSession) -> list:
    return await ai_policies_repo.list_catalog(session)


async def _category_labels(session: AsyncSession) -> dict[str, str]:
    return {item.code: item.name_zh for item in await _catalog_items(session)}


def _serialize_audit(audit: AiPoliciesAudit, include_findings: bool = False) -> dict:
    display_findings = (
        _display_findings(audit.findings or []) if include_findings else []
    )
    summary_findings = display_findings if include_findings else _display_findings(
        audit.findings or []
    )
    data = {
        "id": audit.id,
        "audit_id": audit.audit_id,
        "audit_type": audit.audit_type,
        "skill_id": audit.skill_id,
        "skill_name": audit.skill_name,
        "skill_version": audit.skill_version,
        "status": audit.status,
        "decision": audit.decision,
        "severity": audit.severity,
        "risk_score": audit.risk_score,
        "findings_count": audit.findings_count,
        "high_risk_count": audit.high_risk_count,
        "must_review_count": audit.must_review_count,
        "llm_review_used": audit.llm_review_used,
        "llm_review_model": audit.llm_review_model,
        "summary": _display_summary(audit, summary_findings),
        "error_message": audit.error_message,
        "started_at": _fmt_time(audit.started_at),
        "finished_at": _fmt_time(audit.finished_at),
        "created_at": _fmt_time(audit.created_at),
        "updated_at": _fmt_time(audit.updated_at),
    }
    if include_findings:
        data["findings"] = display_findings
        data["markdown_report"] = audit.markdown_report
    return data


def _report_audit(audit: AiPoliciesAudit) -> SimpleNamespace:
    display_findings = _display_findings(audit.findings or [])
    summary = _display_summary(audit, display_findings)
    attrs = {
        column.name: getattr(audit, column.name)
        for column in AiPoliciesAudit.__table__.columns
    }
    attrs["findings"] = display_findings
    attrs["summary"] = summary
    return SimpleNamespace(**attrs)


def _progress(value: int, completed: int, step: str) -> dict:
    return {"value": value, "completed": completed, "total": 4, "step": step}


async def _commit_progress(
    session: AsyncSession,
    audit: AiPoliciesAudit,
    value: int,
    completed: int,
    step: str,
) -> None:
    current_summary = audit.summary if isinstance(audit.summary, dict) else {}
    next_summary = ai_policies_report.build_summary(audit)
    if isinstance(current_summary.get("llm_review"), dict):
        next_summary["llm_review"] = current_summary["llm_review"]
    next_summary["progress"] = _progress(value, completed, step)
    audit.summary = next_summary
    await session.commit()


async def create_skill_audit(
    session: AsyncSession, skill_id: int, current_user: dict
) -> dict:
    skill = await skill_repo.find_by_id(session, skill_id)
    if not skill:
        raise NotFoundError("skill", skill_id)
    if not skill.zip_path or not os.path.exists(skill.zip_path):
        raise ValidationError("Skill zip 文件不存在，无法发起审查")
    active = await ai_policies_repo.find_active_by_skill(session, skill_id)
    if active:
        raise ConflictError("该 Skill 已有审查任务正在进行中")

    audit = AiPoliciesAudit(
        audit_id=f"AIP-{uuid4().hex[:12]}",
        audit_type="skill",
        skill_id=skill.id,
        skill_name=skill.name,
        skill_version=skill.version,
        source_sha256=_sha256_file(skill.zip_path),
        scanner="skillspector",
        mode="static",
        status="queued",
        created_by=int(current_user["id"]),
    )
    audit = await ai_policies_repo.create_audit(session, audit)
    skill.security_status = "queued"
    skill.security_decision = ""
    skill.security_severity = ""
    skill.security_risk_score = 0
    skill.latest_ai_policies_audit_id = audit.id
    await session.commit()
    await session.refresh(audit)

    from tasks.ai_policies_tasks import run_skill_audit

    run_skill_audit.delay(audit.id)
    return _serialize_audit(audit, include_findings=True)


async def process_skill_audit(session: AsyncSession, audit_pk: int) -> None:
    audit = await ai_policies_repo.find_by_id(session, audit_pk)
    if not audit or audit.status not in {"queued", "running"}:
        return
    skill = (
        await skill_repo.find_by_id(session, audit.skill_id) if audit.skill_id else None
    )
    if not skill or not skill.zip_path or not os.path.exists(skill.zip_path):
        await _fail_audit(session, audit, "Skill zip 文件不存在，无法完成审查")
        return

    audit.status = "running"
    audit.started_at = audit.started_at or _now()
    audit.error_message = ""
    skill.security_status = "running"
    await _commit_progress(session, audit, 20, 1, "正在扫描 Skill")
    category_labels = await _category_labels(session)

    try:
        response = await ai_policies_scanner_client.scan_skill_zip(
            _scanner_target(skill.zip_path)
        )
        await _commit_progress(session, audit, 50, 2, "正在整理风险结果")
        payload = response.get("data") or {}
        raw_findings = payload.get("findings") or []
        normalized_findings = _normalize_findings(raw_findings, skill.zip_path)
        findings = _aggregate_findings(normalized_findings)
        await _commit_progress(session, audit, 65, 3, "正在归类风险")
        severity = str(payload.get("severity") or "LOW").upper()
        risk_score = int(payload.get("risk_score") or 0)
        decision = _decision(risk_score, severity, normalized_findings)
        audit.severity = severity.lower()
        audit.risk_score = risk_score
        settings_row = await ai_policies_repo.get_settings(session)
        llm_review: dict | None = None
        if settings_row.llm_review_enabled:
            await _commit_progress(session, audit, 75, 3, "正在进行 AI 深度审查")
            try:
                llm_review = await ai_policies_llm.run_llm_review(
                    session,
                    settings_row.llm_review_model_id,
                    audit,
                    findings,
                    category_labels,
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "AI Policies LLM review failed: audit_id=%s", audit.audit_id
                )
                llm_review = {
                    "status": "failed",
                    "message": "LLM 审查引擎执行失败，静态审查结果已保留",
                }

        await _commit_progress(session, audit, 90, 4, "正在生成报告")
        audit.status = "completed"
        audit.decision = decision
        audit.severity = severity.lower()
        audit.risk_score = risk_score
        audit.findings = findings
        audit.findings_count = len(normalized_findings)
        audit.high_risk_count = sum(
            1
            for item in normalized_findings
            if item["severity"] in {"high", "critical"}
        )
        audit.must_review_count = sum(
            1 for item in normalized_findings if item.get("must_review")
        )
        audit.scanner_version = str(payload.get("version") or "")
        audit.raw_report = {**response, "normalized_findings": normalized_findings}
        if llm_review:
            audit.raw_report = {**audit.raw_report, "llm_review": llm_review}
            audit.llm_review_used = _llm_review_completed(llm_review)
            audit.llm_review_model = str(llm_review.get("model") or "")
        else:
            audit.llm_review_used = False
            audit.llm_review_model = ""
        audit.finished_at = _now()
        audit.summary = ai_policies_report.build_summary(audit)
        if llm_review:
            audit.summary = {**audit.summary, "llm_review": llm_review}
        audit.markdown_report = ai_policies_report.build_markdown(
            audit, category_labels
        )

        skill.security_status = "completed"
        skill.security_decision = decision
        skill.security_severity = audit.severity
        skill.security_risk_score = risk_score
        skill.latest_ai_policies_audit_id = audit.id
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("AI Policies skill audit failed: audit_id=%s", audit.audit_id)
        await _fail_audit(session, audit, _safe_error_message(exc))


def _safe_error_message(exc: Exception) -> str:
    if isinstance(exc, ai_policies_scanner_client.AiPoliciesScannerError):
        return str(exc) or "安全审查引擎执行失败"
    if isinstance(exc, ValidationError):
        return str(exc) or "审查输入不符合要求"
    return "安全审查任务执行失败，请稍后重新发起审查"


async def fail_audit_by_id(audit_pk: int, message: str) -> None:
    async with get_worker_session_factory()() as session:
        audit = await ai_policies_repo.find_by_id(session, audit_pk)
        if audit and audit.status in {"queued", "running"}:
            await _fail_audit(session, audit, message)


async def _fail_audit(
    session: AsyncSession, audit: AiPoliciesAudit, message: str
) -> None:
    audit.status = "failed"
    audit.decision = "failed"
    audit.severity = "unknown"
    audit.error_message = message
    audit.finished_at = _now()
    category_labels = await _category_labels(session)
    audit.summary = ai_policies_report.build_summary(audit)
    audit.markdown_report = ai_policies_report.build_markdown(audit, category_labels)
    if audit.skill_id:
        skill = await skill_repo.find_by_id(session, audit.skill_id)
        if skill:
            skill.security_status = "failed"
            skill.security_decision = "failed"
            skill.security_severity = "unknown"
            skill.latest_ai_policies_audit_id = audit.id
    await session.commit()


async def list_audits(
    session: AsyncSession,
    page: int,
    page_size: int,
    audit_type: str | None = "skill",
    skill_id: int | None = None,
    status: str | None = None,
    decision: str | None = None,
    q: str | None = None,
    finished_from: datetime | None = None,
    finished_to: datetime | None = None,
    unfinished: bool | None = None,
) -> dict:
    total = await ai_policies_repo.count_all(
        session,
        audit_type,
        skill_id,
        status,
        decision,
        q,
        finished_from,
        finished_to,
        unfinished,
    )
    items = await ai_policies_repo.find_all(
        session,
        page,
        page_size,
        audit_type,
        skill_id,
        status,
        decision,
        q,
        finished_from,
        finished_to,
        unfinished,
    )
    return {
        "items": [_serialize_audit(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_audit(session: AsyncSession, audit_id: str) -> dict:
    audit = await ai_policies_repo.find_by_audit_id(session, audit_id)
    if not audit:
        raise NotFoundError("ai_policies_audit", audit_id)
    return _serialize_audit(audit, include_findings=True)


async def get_audit_export(
    session: AsyncSession, audit_id: str
) -> tuple[str, str, str]:
    audit = await ai_policies_repo.find_by_audit_id(session, audit_id)
    if not audit:
        raise NotFoundError("ai_policies_audit", audit_id)
    category_labels = await _category_labels(session)
    return (
        ai_policies_report.build_markdown(_report_audit(audit), category_labels),
        f"{audit.audit_id}.md",
        "text/markdown",
    )


async def list_catalog(session: AsyncSession) -> list[dict]:
    return [_serialize_catalog_item(item) for item in await _catalog_items(session)]


async def get_settings(session: AsyncSession) -> dict:
    settings_row = await ai_policies_repo.get_settings(session)
    return {
        "llm_review_enabled": settings_row.llm_review_enabled,
        "llm_review_model_id": settings_row.llm_review_model_id,
        "updated_by": settings_row.updated_by,
        "updated_at": _fmt_time(settings_row.updated_at),
    }


async def update_settings(
    session: AsyncSession,
    llm_review_enabled: bool,
    llm_review_model_id: int | None,
    current_user: dict,
) -> dict:
    if llm_review_enabled and not llm_review_model_id:
        raise ValidationError("启用 LLM 审查引擎时必须选择 OpenAI 格式的对话模型")
    if llm_review_model_id:
        model = await ai_policies_llm.get_supported_review_model(
            session, llm_review_model_id
        )
        if not model:
            raise ValidationError("只能选择已启用且包含 OpenAI 格式渠道的对话模型")

    settings_row = await ai_policies_repo.get_settings(session)
    settings_row.llm_review_enabled = llm_review_enabled
    settings_row.llm_review_model_id = llm_review_model_id
    settings_row.updated_by = int(current_user["id"])
    settings_row.updated_at = _now()
    await session.commit()
    await session.refresh(settings_row)
    return await get_settings(session)

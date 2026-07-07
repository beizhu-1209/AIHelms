import hashlib
import logging
import os
import re
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
from services import (
    ai_policies_denoise,
    ai_policies_llm,
    ai_policies_report,
    ai_policies_scanner_client,
)

logger = logging.getLogger(__name__)

SEVERITY_RANK = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "info": 1,
    "none": 0,
    "unknown": 0,
    "": 0,
}

URL_RE = re.compile(r"(?:https?://|mailto:)[^\s\]\"'<>`]+", re.I)
URL_TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".rst",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".py",
    ".js",
    ".ts",
    ".mjs",
    ".cjs",
    ".html",
    ".htm",
    ".css",
    ".svg",
    ".sh",
}


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


def _english_heavy(text: str) -> bool:
    if not text:
        return False
    letters = sum(1 for char in text if char.isascii() and char.isalpha())
    chinese = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    return letters >= 16 and letters > chinese * 2


def _category_fallback_text(category: str) -> tuple[str, str, str]:
    fallback = {
        "AST02": (
            "供应链依赖风险",
            "规则扫描发现依赖来源、版本或安装过程存在需要确认的风险。",
            "核实依赖来源和版本，固定版本并在升级后重新审查。",
        ),
        "AST03": (
            "权限边界需要复核",
            "规则扫描发现权限声明、执行权限或访问范围存在需要确认的风险。",
            "补充权限边界说明，删除不必要的高权限访问或执行能力。",
        ),
        "AST05": (
            "提示指令边界风险",
            "规则扫描发现可能影响模型指令边界的内容，需要结合运行场景确认。",
            "明确区分系统指令、用户输入和外部内容，对不可信内容做边界隔离。",
        ),
        "AST06": (
            "危险代码或命令调用风险",
            "规则扫描发现脚本、命令或工具调用存在需要确认的执行风险。",
            "限制命令和工具调用范围，校验输入并移除不必要的执行链路。",
        ),
        "AST08": (
            "上下文或范围异常",
            "规则扫描发现上下文、状态或能力范围存在需要确认的异常行为。",
            "收窄 Skill 能力边界，限制不可信内容进入长期上下文或关键状态。",
        ),
        "AST10": (
            "数据流转风险",
            "规则扫描发现文件、上下文或配置数据可能进入敏感调用或外部位置。",
            "核实数据流转目的和范围，对敏感数据做校验、脱敏和最小化传递。",
        ),
    }
    return fallback.get(
        category,
        (
            "安全风险",
            "规则扫描发现风险，请结合文件位置和业务用途复核。",
            "请结合文件内容、运行场景和业务用途确认是否需要调整。",
        ),
    )


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
    if "least privilege" in text or rule_id == "LP3":
        return (
            "权限声明不完整",
            "扫描器未能确认 Skill 的权限边界，建议结合实际用途复核所需能力。",
            "在 Skill 说明中补充必要能力、工具范围和权限边界，避免超出用途的访问。",
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
    if "data flow" in text or "tainted flow" in text:
        return (
            "不可信数据进入高风险调用",
            "检测到来自环境变量、外部输入或配置的数据被传入命令执行、网络请求等敏感位置。",
            "对进入敏感调用的数据做白名单校验，避免直接拼接到命令、路径或请求参数中。",
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
    if "agent snooping" in text or "skill enumeration" in text:
        return (
            "读取其他 Skill 信息",
            "检测到枚举或读取其他 Skill 文件的行为，"
            "可能暴露其他 Skill 的提示词、能力或配置。",
            "移除跨 Skill 枚举或读取逻辑；确需访问时应明确权限范围和业务用途。",
        )
    if "rogue agent" in text or "session persistence" in text:
        return (
            "异常持久化行为",
            "检测到跨会话保持状态、启动项或定时任务相关行为，"
            "可能让 Skill 超出单次任务边界。",
            "移除未授权的持久化机制；确需保存状态时应说明范围并取得明确授权。",
        )
    if "context window stuffing" in text:
        return (
            "上下文填充风险",
            "检测到大量填充上下文或挤占有效指令空间的内容，可能影响模型遵循原有规则。",
            "限制输入长度和重复内容，对外部文本做截断、摘要或分段处理。",
        )
    if "memory manipulation" in text or "memory poisoning" in text:
        return (
            "记忆或状态篡改风险",
            "检测到修改记忆、状态或长期上下文的行为，可能影响后续任务判断。",
            "保护关键记忆和状态字段，避免不可信内容直接写入长期上下文。",
        )
    if "output handling" in text or "unvalidated output injection" in text:
        return (
            "模型输出未校验",
            "检测到模型输出未经校验就进入后续命令、页面或结构化上下文，可能造成注入风险。",
            "对模型输出做类型校验、转义和白名单约束，再传入下游系统。",
        )
    if "excessive agency" in text or "scope creep" in text:
        return (
            "能力范围超出声明用途",
            "检测到 Skill 行为可能超出说明中的用途边界，增加误用或越权操作风险。",
            "收窄 Skill 的工具和指令范围，删除与声明用途无关的能力描述。",
        )
    if "dangerous code" in text or "tool misuse" in text:
        return (
            "存在高风险工具或代码调用",
            "检测到可能执行系统命令、脚本或高权限工具的内容。",
            "限制工具调用范围，删除不必要的系统命令；保留必要能力时应说明使用边界和输入校验方式。",
        )

    fallback_title, fallback_description, fallback_recommendation = (
        _category_fallback_text(category)
    )
    title = raw_category or fallback_title
    if pattern:
        title = f"{title} - {pattern}"
    description = raw.get("explanation") or fallback_description
    recommendation = raw.get("remediation") or fallback_recommendation
    if _english_heavy(title):
        title = fallback_title
    if _english_heavy(description):
        description = fallback_description
    if _english_heavy(recommendation):
        recommendation = fallback_recommendation
    return (title, description, recommendation)


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
    file_role = ai_policies_denoise.file_role_for(file_name, raw)
    item = {
        "source": "static",
        "rule_id": raw.get("id") or "",
        "category": category,
        "raw_category": raw.get("category") or "",
        "scanner_severity": severity.lower(),
        "severity": severity.lower(),
        "confidence": raw.get("confidence") or 0,
        "title": title,
        "description": description,
        "recommendation": recommendation,
        "file_role": file_role,
        "path_bucket": ai_policies_denoise.normalized_path_bucket(
            file_name, file_role
        ),
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
    item["command_context"] = ai_policies_denoise.command_context_for(item)
    item["redline"] = ai_policies_denoise.is_redline(item)
    return ai_policies_denoise.classify_item(item)


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
    groups: dict[tuple[str, str, str, str, str], dict] = {}
    for item in findings:
        if item.get("file_role") == "scanner_diagnostic":
            continue
        key = (
            str(item.get("rule_id") or ""),
            str(item.get("category") or ""),
            str(item.get("title") or ""),
            str(item.get("file_role") or ""),
            str(item.get("path_bucket") or ""),
        )
        if key not in groups:
            groups[key] = {
                "source": item.get("source") or "static",
                "rule_id": item.get("rule_id") or "",
                "category": item.get("category") or "",
                "raw_category": item.get("raw_category") or "",
                "severity": item.get("severity") or "unknown",
                "scanner_severity": item.get("scanner_severity") or "unknown",
                "effective_severity": item.get("effective_severity") or "unknown",
                "confidence": item.get("confidence") or 0,
                "title": item.get("title") or "安全风险",
                "description": item.get("description") or "",
                "recommendation": item.get("recommendation") or "",
                "file_role": item.get("file_role") or "unknown",
                "path_bucket": item.get("path_bucket") or "",
                "finding_type": item.get("finding_type") or "true_risk",
                "counts_toward_score": bool(item.get("counts_toward_score")),
                "command_context": item.get("command_context") or {},
                "denoise_reason": item.get("denoise_reason") or "",
                "redline": bool(item.get("redline")),
                "hit_count": 0,
                "locations": [],
                "must_review": False,
            }
        group = groups[key]
        group["severity"] = _severity_max(group["severity"], item.get("severity") or "")
        group["effective_severity"] = group["severity"]
        group["scanner_severity"] = _severity_max(
            group["scanner_severity"], item.get("scanner_severity") or ""
        )
        group["confidence"] = max(
            group.get("confidence") or 0,
            item.get("confidence") or 0,
        )
        group["hit_count"] += 1
        group["locations"].append(_finding_location(item))
        group["must_review"] = bool(group["must_review"] or item.get("must_review"))
        group["redline"] = bool(group["redline"] or item.get("redline"))

    for group in groups.values():
        group["group_id"] = ai_policies_denoise.group_id_for(group)

    return sorted(
        groups.values(),
        key=lambda item: (
            -SEVERITY_RANK.get(item.get("severity") or "", 0),
            item.get("finding_type") or "",
            item.get("category") or "",
            item.get("title") or "",
        ),
    )


def _scan_limitations(findings: list[dict]) -> list[dict]:
    limitations: list[dict] = []
    for item in findings:
        if item.get("file_role") != "scanner_diagnostic":
            continue
        evidence = item.get("evidence") or {}
        limitations.append(
            {
                "title": "依赖漏洞库查询未完成",
                "message": "依赖漏洞库查询未完成，供应链漏洞结果可能不完整。",
                "source": evidence.get("matched_text")
                or evidence.get("snippet")
                or item.get("title")
                or "",
            }
        )
    return limitations


def _file_role_label(file_role: str) -> str:
    return {
        "runtime_entry": "入口",
        "executable_script": "脚本",
        "dependency_manifest": "依赖",
        "template_asset": "模板",
        "documentation": "文档",
        "example_or_test": "示例",
    }.get(file_role, "文件")


def _file_status_for(file_name: str, file_role: str, findings: list[dict]) -> dict:
    related: list[dict] = []
    seen: set[str] = set()
    for item in findings:
        if not any(
            location.get("file") == file_name
            for location in item.get("locations") or []
        ):
            continue
        key = str(item.get("group_id") or id(item))
        if key in seen:
            continue
        seen.add(key)
        related.append(item)
    counted = [item for item in related if item.get("counts_toward_score") is not False]
    if counted:
        severity = max(
            (item.get("severity") or "unknown" for item in counted),
            key=lambda severity: SEVERITY_RANK.get(severity, 0),
        )
        return {
            "status": severity,
            "severity": severity,
            "risk_count": sum(int(item.get("hit_count") or 1) for item in counted),
        }
    if any(item.get("finding_type") == "review_note" for item in related):
        return {"status": "review", "severity": "info", "risk_count": 0}
    if file_role == "runtime_entry":
        return {"status": "entry", "severity": "none", "risk_count": 0}
    return {"status": "clean", "severity": "none", "risk_count": 0}


def _file_sort_key(item: dict) -> tuple[int, int, str]:
    status_rank = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
        "review": 4,
        "entry": 5,
        "clean": 6,
    }
    role_rank = {
        "runtime_entry": 0,
        "executable_script": 1,
        "dependency_manifest": 2,
        "template_asset": 3,
        "documentation": 4,
        "example_or_test": 5,
    }
    return (
        status_rank.get(str(item.get("status") or ""), 9),
        role_rank.get(str(item.get("role") or ""), 9),
        str(item.get("path") or ""),
    )


def _zip_file_summaries(zip_path: str, findings: list[dict]) -> list[dict]:
    if not zip_path or not zipfile.is_zipfile(zip_path):
        return []
    items: list[dict] = []
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                file_name = info.filename.lstrip("/")
                file_role = ai_policies_denoise.file_role_for(file_name, {})
                status = _file_status_for(file_name, file_role, findings)
                items.append(
                    {
                        "path": file_name,
                        "role": file_role,
                        "role_label": _file_role_label(file_role),
                        "size": info.file_size,
                        **status,
                    }
                )
    except Exception:  # noqa: BLE001
        logger.exception("AI Policies zip file list failed: zip_path=%s", zip_path)
        return []
    return sorted(items, key=_file_sort_key)


def _clean_url(raw_url: str) -> str:
    url = raw_url.strip()
    while url:
        cleaned = url.rstrip(".,;:!?，。；：！？*_~")
        while cleaned.endswith(")") and cleaned.count(")") > cleaned.count("("):
            cleaned = cleaned[:-1].rstrip(".,;:!?，。；：！？*_~")
        if cleaned == url:
            return cleaned
        url = cleaned
    return url


def _should_scan_url_file(file_name: str) -> bool:
    suffix = Path(file_name).suffix.lower()
    name = Path(file_name).name.lower()
    return suffix in URL_TEXT_SUFFIXES or name in {"dockerfile", "makefile"}


def _zip_external_links(zip_path: str) -> list[dict]:
    if not zip_path or not zipfile.is_zipfile(zip_path):
        return []
    links: list[dict] = []
    seen: set[str] = set()
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                file_name = info.filename.lstrip("/")
                if not _should_scan_url_file(file_name):
                    continue
                text = zf.read(info.filename).decode("utf-8", errors="ignore")
                for raw_url in URL_RE.findall(text):
                    url = _clean_url(raw_url)
                    if not url or url in seen:
                        continue
                    seen.add(url)
                    links.append({"url": url, "label": url, "file": file_name})
    except Exception:  # noqa: BLE001
        logger.exception("AI Policies external link scan failed: zip_path=%s", zip_path)
        return []
    return links


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


def _legacy_group_to_items(group: dict) -> list[dict]:
    localized = _localized_finding(group)
    locations = localized.get("locations") or []
    if not locations:
        locations = [_finding_location(localized)]

    items: list[dict] = []
    for location in locations:
        file_name = location.get("file") or ""
        snippet = location.get("snippet") or ""
        raw = {
            "id": localized.get("rule_id") or "",
            "category": localized.get("raw_category")
            or localized.get("category")
            or "",
            "pattern": localized.get("pattern") or localized.get("title") or "",
            "location": {
                "file": file_name,
                "start_line": location.get("start_line"),
                "end_line": location.get("end_line"),
            },
            "finding": snippet,
            "code_snippet": snippet,
            "severity": str(
                localized.get("scanner_severity")
                or localized.get("severity")
                or "low"
            ).upper(),
        }
        file_role = ai_policies_denoise.file_role_for(file_name, raw)
        item = {
            "source": localized.get("source") or "static",
            "rule_id": localized.get("rule_id") or "",
            "category": localized.get("category") or "",
            "raw_category": localized.get("raw_category") or "",
            "scanner_severity": localized.get("scanner_severity")
            or localized.get("severity")
            or "unknown",
            "severity": localized.get("severity") or "unknown",
            "confidence": localized.get("confidence") or 0,
            "title": localized.get("title") or "安全风险",
            "description": localized.get("description") or "",
            "recommendation": localized.get("recommendation") or "",
            "file_role": file_role,
            "path_bucket": ai_policies_denoise.normalized_path_bucket(
                file_name, file_role
            ),
            "location": raw["location"],
            "evidence": {
                "snippet": snippet,
                "matched_text": snippet,
            },
            "must_review": (localized.get("severity") or "") in {
                "critical",
                "high",
            },
        }
        item["command_context"] = ai_policies_denoise.command_context_for(item)
        item["redline"] = ai_policies_denoise.is_redline(item)
        items.append(ai_policies_denoise.classify_item(item))
    return items


def _display_findings(findings: list[dict]) -> list[dict]:
    if not findings:
        return []
    if all(_is_grouped_finding(item) for item in findings):
        rebuilt: list[dict] = []
        for item in findings:
            if item.get("file_role") and item.get("finding_type"):
                rebuilt.append(_localized_finding(item))
            else:
                rebuilt.extend(_legacy_group_to_items(item))
        return _aggregate_findings(rebuilt)
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
    reviews = llm_review.get("finding_reviews")
    has_finding_review = isinstance(reviews, list) and any(
        isinstance(item, dict)
        and item.get("group_id")
        and (
            item.get("finding_type")
            or item.get("effective_severity")
            or item.get("reason")
        )
        for item in reviews
    )
    intent_analysis = llm_review.get("intent_analysis")
    has_intent_analysis = isinstance(intent_analysis, dict) and any(
        intent_analysis.get(key)
        for key in ("declared_intent", "actual_behavior", "consistency", "basis")
    )
    return has_finding_review or has_intent_analysis


def _display_llm_review(llm_review: dict | None, used: bool) -> dict | None:
    if not isinstance(llm_review, dict):
        return None
    cleaned = {**llm_review}
    if not used or cleaned.get("status") != "completed":
        cleaned["category_reviews"] = []
        cleaned["finding_reviews"] = []
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


def _display_metrics(audit: AiPoliciesAudit, findings: list[dict]) -> dict:
    if audit.status in {"queued", "running"}:
        return {
            "decision": "",
            "severity": "",
            "risk_score": 0,
            "findings_count": 0,
            "high_risk_count": 0,
            "must_review_count": 0,
        }
    if audit.status != "completed":
        return {
            "decision": audit.decision,
            "severity": audit.severity,
            "risk_score": audit.risk_score,
            "findings_count": audit.findings_count,
            "high_risk_count": audit.high_risk_count,
            "must_review_count": audit.must_review_count,
        }

    score = ai_policies_denoise.score_groups(findings)
    return {
        "decision": score.decision,
        "severity": score.severity,
        "risk_score": score.risk_score,
        "findings_count": score.findings_count,
        "high_risk_count": score.high_risk_count,
        "must_review_count": score.must_review_count,
    }


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


def _serialize_audit(
    audit: AiPoliciesAudit,
    include_findings: bool = False,
    category_labels: dict[str, str] | None = None,
) -> dict:
    display_findings = (
        _display_findings(audit.findings or []) if include_findings else []
    )
    summary_findings = display_findings if include_findings else _display_findings(
        audit.findings or []
    )
    metrics = _display_metrics(audit, summary_findings)
    data = {
        "id": audit.id,
        "audit_id": audit.audit_id,
        "audit_type": audit.audit_type,
        "skill_id": audit.skill_id,
        "skill_name": audit.skill_name,
        "skill_version": audit.skill_version,
        "status": audit.status,
        "decision": metrics["decision"],
        "severity": metrics["severity"],
        "risk_score": metrics["risk_score"],
        "findings_count": metrics["findings_count"],
        "high_risk_count": metrics["high_risk_count"],
        "must_review_count": metrics["must_review_count"],
        "llm_review_used": audit.llm_review_used,
        "llm_review_model": audit.llm_review_model,
        "source_sha256": audit.source_sha256,
        "summary": _display_summary(audit, summary_findings),
        "error_message": audit.error_message,
        "started_at": _fmt_time(audit.started_at),
        "finished_at": _fmt_time(audit.finished_at),
        "created_at": _fmt_time(audit.created_at),
        "updated_at": _fmt_time(audit.updated_at),
    }
    if include_findings:
        data["findings"] = display_findings
        data["markdown_report"] = ai_policies_report.build_markdown(
            _report_audit(audit), category_labels or {}
        )
    return data


def _report_audit(audit: AiPoliciesAudit) -> SimpleNamespace:
    display_findings = _display_findings(audit.findings or [])
    summary = _display_summary(audit, display_findings)
    attrs = {
        column.name: getattr(audit, column.name)
        for column in AiPoliciesAudit.__table__.columns
    }
    attrs.update(_display_metrics(audit, display_findings))
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
        scan_limitations = _scan_limitations(normalized_findings)
        findings = _aggregate_findings(normalized_findings)
        file_summaries = _zip_file_summaries(skill.zip_path, findings)
        external_links = _zip_external_links(skill.zip_path)
        await _commit_progress(session, audit, 65, 3, "正在归类风险")
        score_result = ai_policies_denoise.score_groups(findings)
        audit.severity = score_result.severity
        audit.risk_score = score_result.risk_score
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
                    skill.zip_path,
                )
                findings = ai_policies_denoise.apply_finding_reviews(
                    findings, llm_review
                )
                score_result = ai_policies_denoise.score_groups(findings)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "AI Policies LLM review failed: audit_id=%s", audit.audit_id
                )
                llm_review = {
                    "status": "failed",
                    "message": "LLM 审查引擎执行失败，静态审查结果已保留",
                }

        await _commit_progress(session, audit, 90, 3, "正在生成报告")
        audit.status = "completed"
        audit.decision = score_result.decision
        audit.severity = score_result.severity
        audit.risk_score = score_result.risk_score
        audit.findings = findings
        audit.findings_count = score_result.findings_count
        audit.high_risk_count = score_result.high_risk_count
        audit.must_review_count = score_result.must_review_count
        audit.scanner_version = str(payload.get("version") or "")
        audit.raw_report = {
            **response,
            "normalized_findings": normalized_findings,
            "scan_limitations": scan_limitations,
        }
        if llm_review:
            audit.raw_report = {**audit.raw_report, "llm_review": llm_review}
            audit.llm_review_used = _llm_review_completed(llm_review)
            audit.llm_review_model = str(llm_review.get("model") or "")
        else:
            audit.llm_review_used = False
            audit.llm_review_model = ""
        audit.finished_at = _now()
        audit.summary = ai_policies_report.build_summary(audit)
        audit.summary = {
            **audit.summary,
            "files": file_summaries,
            "file_count": len(file_summaries),
            "external_links": external_links,
            "source_size_bytes": Path(skill.zip_path).stat().st_size,
        }
        if scan_limitations:
            audit.summary = {**audit.summary, "scan_limitations": scan_limitations}
        if llm_review:
            audit.summary = {**audit.summary, "llm_review": llm_review}
            intent_analysis = llm_review.get("intent_analysis")
            if isinstance(intent_analysis, dict) and intent_analysis:
                audit.summary = {
                    **audit.summary,
                    "intent_analysis": intent_analysis,
                }
        audit.markdown_report = ai_policies_report.build_markdown(
            audit, category_labels
        )

        skill.security_status = "completed"
        skill.security_decision = score_result.decision
        skill.security_severity = audit.severity
        skill.security_risk_score = score_result.risk_score
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
    return _serialize_audit(
        audit,
        include_findings=True,
        category_labels=await _category_labels(session),
    )


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

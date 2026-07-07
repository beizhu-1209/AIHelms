import ast
import hashlib
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

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

SHELL_DANGER_RE = re.compile(
    r"(curl\s+[^|;&]+[|]\s*(?:bash|sh)|wget\s+[^|;&]+[|]\s*(?:bash|sh)|"
    r"nc\s+-e|bash\s+-i|/dev/tcp/|rm\s+-rf\s+/(?:\s|$)|"
    r"chmod\s+777\s+/(?:\w|$))",
    re.I,
)
DIAGNOSTIC_RE = re.compile(
    r"(osv\.dev|unreachable|timeout|timed out|fallback|network error|"
    r"connection refused|failed to connect|service unavailable)",
    re.I,
)
FIXED_LOCAL_TOOLS = {
    "convert",
    "dot",
    "ffmpeg",
    "mermaid",
    "mmdc",
    "osascript",
    "pandoc",
}
COMMAND_TOKEN_RE = re.compile(
    r"\b(subprocess|os\.system|shell|curl|wget|pandoc|mmdc|mermaid|"
    r"osascript|build_cmd|eval|exec|__import__|pickle\.loads)\b",
    re.I,
)
SUBPROCESS_LIST_RE = re.compile(r"subprocess\.\w+\s*\(\s*\[", re.I)
ASSIGNED_LIST_COMMAND_RE = re.compile(
    r"\b(\w+)\s*=\s*\[[\s\S]{0,500}?subprocess\.\w+\s*\(\s*\1\b",
    re.I,
)
DOWNLOAD_EXECUTE_RE = re.compile(r"(curl|wget)\b[^|;&]+[|]\s*(bash|sh)", re.I)
EXTERNAL_DATA_RE = re.compile(
    r"\b(input|request|args|argv|stdin|environ|getenv|read|loads?)\b",
    re.I,
)


@dataclass
class ScoreResult:
    risk_score: int
    severity: str
    decision: str
    high_risk_count: int
    must_review_count: int
    findings_count: int


def _text(raw: dict) -> str:
    parts = [
        raw.get("id"),
        raw.get("category"),
        raw.get("pattern"),
        raw.get("finding"),
        raw.get("code_snippet"),
        raw.get("explanation"),
        raw.get("remediation"),
    ]
    location = raw.get("location") or {}
    parts.append(location.get("file"))
    return " ".join(str(part or "") for part in parts).lower()


def is_scanner_diagnostic(raw: dict) -> bool:
    return bool(DIAGNOSTIC_RE.search(_text(raw)))


def file_role_for(path: str, raw: dict | None = None) -> str:
    raw = raw or {}
    if is_scanner_diagnostic(raw):
        return "scanner_diagnostic"

    clean_path = (path or "").replace("\\", "/").lstrip("/")
    lower = clean_path.lower()
    name = PurePosixPath(lower).name
    suffix = PurePosixPath(lower).suffix
    parts = set(PurePosixPath(lower).parts)

    if name in {
        "requirements.txt",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "poetry.lock",
        "pipfile",
        "pipfile.lock",
    }:
        return "dependency_manifest"
    if name in {"skill.md", "manifest.json", "ai-plugin.json"}:
        return "runtime_entry"
    if parts & {"test", "tests", "demo", "demos", "example", "examples", "fixture"}:
        return "example_or_test"
    if name in {"readme.md", "license", "license.txt", "changelog.md"}:
        return "documentation"
    if parts & {"docs", "doc", "references", "reference", "checklist"}:
        return "documentation"
    if suffix in {".md", ".txt", ".rst"}:
        return "documentation"
    if parts & {"assets", "asset", "templates", "template", "static", "public"}:
        return "template_asset"
    if suffix in {".html", ".svg", ".css"}:
        return "template_asset"
    if suffix in {".py", ".sh", ".js", ".ts", ".mjs", ".cjs", ".rb", ".go"}:
        return "executable_script"
    return "unknown"


def normalized_path_bucket(path: str, file_role: str) -> str:
    clean_path = (path or "").replace("\\", "/").lstrip("/")
    if not clean_path:
        return file_role or "unknown"
    parts = PurePosixPath(clean_path.lower()).parts
    if file_role in {"documentation", "template_asset", "dependency_manifest"}:
        return file_role
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return parts[0]


def command_context_for(item: dict) -> dict:
    evidence = item.get("evidence") or {}
    snippet_text = " ".join(
        str(part or "")
        for part in [evidence.get("snippet"), evidence.get("matched_text")]
    )
    text = " ".join(
        str(part or "")
        for part in [
            item.get("title"),
            item.get("description"),
            snippet_text,
        ]
    )
    if not COMMAND_TOKEN_RE.search(text):
        return {}
    ast_context = _python_command_context(_strip_line_numbers(snippet_text))
    list_args = ast_context["list_args"] or _has_list_command(snippet_text)
    return {
        "shell_true": ast_context["shell_true"] or bool(_shell_true_re().search(text)),
        "list_args": list_args,
        "fixed_tool": ast_context["fixed_tool"] or _has_fixed_tool(text),
        "external_download_execute": bool(DOWNLOAD_EXECUTE_RE.search(text)),
        "dangerous_exec": ast_context["dangerous_exec"],
    }


def _strip_line_numbers(text: str) -> str:
    return "\n".join(
        re.sub(r"^\s*\d+\s*[|:]\s?", "", line) for line in text.splitlines()
    )


def _shell_true_re() -> re.Pattern:
    return re.compile(r"shell\s*=\s*true", re.I)


def _has_fixed_tool(text: str) -> bool:
    return bool(
        re.search(
            r"\b(" + "|".join(FIXED_LOCAL_TOOLS) + r"|build_cmd)\b",
            text,
            re.I,
        )
    )


def _has_list_command(text: str) -> bool:
    return bool(
        SUBPROCESS_LIST_RE.search(text) or ASSIGNED_LIST_COMMAND_RE.search(text)
    )


def _python_command_context(source: str) -> dict:
    context = {
        "shell_true": False,
        "list_args": False,
        "fixed_tool": False,
        "dangerous_exec": False,
    }
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return context
    list_vars = _assigned_list_tools(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = _call_name(node.func)
        if func_name in {"eval", "exec", "__import__", "pickle.loads"}:
            context["dangerous_exec"] = True
        if func_name not in {
            "subprocess.run",
            "subprocess.call",
            "subprocess.Popen",
            "os.system",
        }:
            continue
        context["shell_true"] = context["shell_true"] or _call_shell_true(node)
        list_args, fixed_tool = _call_uses_fixed_list_tool(node, list_vars)
        context["list_args"] = context["list_args"] or list_args
        context["fixed_tool"] = context["fixed_tool"] or fixed_tool
    return context


def _assigned_list_tools(tree: ast.AST) -> dict[str, str]:
    items: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(
            node.value, (ast.List, ast.Tuple)
        ):
            continue
        tool = _first_list_tool(node.value)
        if not tool:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                items[target.id] = tool
    return items


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _call_shell_true(node: ast.Call) -> bool:
    return any(
        keyword.arg == "shell"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is True
        for keyword in node.keywords
    )


def _call_uses_fixed_list_tool(
    node: ast.Call, list_vars: dict[str, str]
) -> tuple[bool, bool]:
    if not node.args:
        return (False, False)
    first = node.args[0]
    if isinstance(first, (ast.List, ast.Tuple)):
        tool = _first_list_tool(first)
        return (True, tool in FIXED_LOCAL_TOOLS)
    if isinstance(first, ast.Name) and first.id in list_vars:
        return (True, list_vars[first.id] in FIXED_LOCAL_TOOLS)
    return (False, False)


def _first_list_tool(node: ast.List | ast.Tuple) -> str:
    if not node.elts:
        return ""
    first = node.elts[0]
    if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
        return ""
    return PurePosixPath(first.value.lower()).name


def is_redline(item: dict) -> bool:
    evidence = item.get("evidence") or {}
    text = " ".join(
        str(part or "")
        for part in [
            item.get("rule_id"),
            item.get("raw_category"),
            item.get("title"),
            item.get("description"),
            evidence.get("snippet"),
            evidence.get("matched_text"),
        ]
    )
    command_context = item.get("command_context") or {}
    dangerous_external_exec = bool(
        command_context.get("dangerous_exec") and EXTERNAL_DATA_RE.search(text)
    )
    shell_external_command = bool(
        command_context.get("shell_true") and EXTERNAL_DATA_RE.search(text)
    )
    return (
        bool(SHELL_DANGER_RE.search(text))
        or "reverse_shell" in text.lower()
        or dangerous_external_exec
        or shell_external_command
    )


def classify_item(item: dict) -> dict:
    file_role = item.get("file_role") or "unknown"
    category = item.get("category") or ""
    rule_id = str(item.get("rule_id") or "")
    scanner_severity = item.get("scanner_severity") or item.get("severity") or "low"
    scanner_severity = str(scanner_severity).lower()
    command_context = item.get("command_context") or {}
    redline = bool(item.get("redline"))
    evidence = item.get("evidence") or {}
    evidence_text = " ".join(
        str(part or "")
        for part in [
            item.get("title"),
            item.get("description"),
            evidence.get("snippet"),
            evidence.get("matched_text"),
        ]
    ).lower()

    finding_type = "true_risk"
    effective_severity = scanner_severity
    counts_toward_score = True
    denoise_reason = ""

    if file_role == "scanner_diagnostic":
        finding_type = "scanner_diagnostic"
        effective_severity = "none"
        counts_toward_score = False
        denoise_reason = "扫描器运行诊断，不作为 Skill 风险。"
    elif redline:
        finding_type = "true_risk"
        effective_severity = "critical" if scanner_severity == "critical" else "high"
    elif file_role in {
        "documentation",
        "template_asset",
        "example_or_test",
    } and category in {"AST05", "AST07", "AST08", "AST09"}:
        finding_type = "false_positive"
        effective_severity = "none"
        counts_toward_score = False
        denoise_reason = "命中位于文档、模板或示例文件，不属于运行时可执行风险。"
    elif file_role in {"documentation", "template_asset", "example_or_test"}:
        finding_type = "review_note"
        effective_severity = "info"
        counts_toward_score = False
        denoise_reason = "命中位于非运行时文件，仅作为复核提示。"
    elif (
        category == "AST03"
        and rule_id == "LP3"
        and not evidence.get("matched_text")
    ):
        finding_type = "review_note"
        effective_severity = "info"
        counts_toward_score = False
        denoise_reason = "扫描器未给出具体权限证据，仅作为权限配置复核提示。"
    elif (
        category == "AST03"
        and rule_id == "PE2"
        and ("请先安装" in evidence_text or "print(" in evidence_text)
    ):
        finding_type = "review_note"
        effective_severity = "info"
        counts_toward_score = False
        denoise_reason = "提权命令位于安装提示或错误信息中，未发现实际提权执行。"
    elif command_context and (
        command_context.get("fixed_tool")
        and command_context.get("list_args")
        and not command_context.get("shell_true")
        and not command_context.get("external_download_execute")
        and not command_context.get("dangerous_exec")
        and category in {"AST06", "AST08", "AST10"}
    ):
        finding_type = "false_positive"
        effective_severity = "none"
        counts_toward_score = False
        denoise_reason = "调用的是本地固定工具，暂未发现明显命令注入风险。"
    elif command_context and (
        command_context.get("fixed_tool")
        and not command_context.get("external_download_execute")
        and not command_context.get("dangerous_exec")
        and category in {"AST06", "AST08", "AST10"}
    ):
        finding_type = "review_note"
        effective_severity = "info"
        counts_toward_score = False
        denoise_reason = "命令参数构造信息不足，建议确认是否包含外部输入。"
    elif (
        category == "AST02"
        and scanner_severity in {"high", "critical"}
        and (
            rule_id in {"SC1", "RP1"}
            or "unpinned" in evidence_text
            or "未固定" in evidence_text
            or "未锁定" in evidence_text
        )
    ):
        finding_type = "true_risk"
        effective_severity = "low"
        denoise_reason = "依赖未锁定版本按供应链建议项计入，默认不按高危处理。"

    return {
        **item,
        "finding_type": finding_type,
        "effective_severity": effective_severity,
        "severity": effective_severity,
        "counts_toward_score": counts_toward_score,
        "denoise_reason": denoise_reason,
        "must_review": finding_type == "review_note"
        or effective_severity in {"critical", "high"},
    }


def _group_hash(parts: tuple[str, ...]) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"AIPG-{digest}"


def group_id_for(group: dict) -> str:
    parts = (
        str(group.get("rule_id") or ""),
        str(group.get("category") or ""),
        str(group.get("title") or ""),
        str(group.get("file_role") or ""),
        str(group.get("path_bucket") or ""),
    )
    return _group_hash(parts)


def _score_for(group: dict) -> int:
    if not group.get("counts_toward_score"):
        return 0
    if group.get("redline"):
        return 75 if group.get("severity") == "critical" else 45
    severity = group.get("severity")
    base = {
        "critical": 70,
        "high": 35,
        "medium": 15,
        "low": 5,
        "info": 1,
    }.get(severity, 0)
    hit_count = max(1, int(group.get("hit_count") or 1))
    return min(base + max(0, hit_count - 1), base + 10)


def score_groups(groups: list[dict]) -> ScoreResult:
    score = min(100, sum(_score_for(group) for group in groups))
    counted = [
        group
        for group in groups
        if group.get("counts_toward_score")
        and group.get("severity") in {"critical", "high", "medium", "low", "info"}
    ]
    max_severity = max(
        (group.get("severity") or "none" for group in counted),
        key=lambda severity: SEVERITY_RANK.get(severity, 0),
        default="none",
    )
    if max_severity in {"critical", "high"}:
        decision = "high_risk"
    elif score > 0 or any(
        group.get("finding_type") == "review_note" for group in groups
    ):
        decision = "attention_required"
    else:
        decision = "passed"

    return ScoreResult(
        risk_score=score,
        severity=max_severity if max_severity != "none" else "low",
        decision=decision,
        high_risk_count=sum(
            int(group.get("hit_count") or 1)
            for group in counted
            if group.get("severity") in {"critical", "high"}
        ),
        must_review_count=sum(
            int(group.get("hit_count") or 1)
            for group in groups
            if group.get("must_review")
        ),
        findings_count=sum(
            int(group.get("hit_count") or 1)
            for group in counted
            if group.get("severity") in {"critical", "high", "medium", "low"}
        ),
    )


def apply_finding_reviews(groups: list[dict], llm_review: dict | None) -> list[dict]:
    if not llm_review or llm_review.get("status") != "completed":
        return groups
    raw_reviews = llm_review.get("finding_reviews")
    if not isinstance(raw_reviews, list):
        return groups

    reviews = {
        str(item.get("group_id")): item
        for item in raw_reviews
        if isinstance(item, dict) and item.get("group_id")
    }
    updated: list[dict] = []
    for group in groups:
        review = reviews.get(str(group.get("group_id")))
        if not review:
            updated.append(group)
            continue
        next_group = {**group, "llm_review": review}
        if group.get("redline"):
            updated.append(next_group)
            continue

        requested_type = str(review.get("finding_type") or "").strip()
        requested_severity = str(review.get("effective_severity") or "").strip()
        current_rank = SEVERITY_RANK.get(group.get("severity") or "", 0)
        requested_rank = SEVERITY_RANK.get(requested_severity, current_rank)

        if requested_type in {"false_positive", "review_note", "true_risk"}:
            next_group["finding_type"] = requested_type
        if requested_rank <= current_rank:
            next_group["severity"] = requested_severity or group.get("severity")
            next_group["effective_severity"] = next_group["severity"]
        if requested_type == "false_positive" or next_group["severity"] in {
            "none",
            "info",
        }:
            next_group["counts_toward_score"] = False
            next_group["must_review"] = False
        elif requested_type == "review_note":
            next_group["counts_toward_score"] = False
            next_group["must_review"] = True
        updated.append(next_group)
    return updated

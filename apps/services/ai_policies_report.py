from typing import Any

OWASP_NOTICE = (
    "风险分类参考 OWASP Agentic Skills Top 10。OWASP 内容遵循 CC BY-SA 4.0，"
    "OWASP 不对本产品或审查结果作认证或背书。"
)

SEVERITY_LABELS = {
    "critical": "严重",
    "high": "高危",
    "medium": "中危",
    "low": "低危",
    "unknown": "未知",
    "": "未分级",
}

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0, "": 0}


def progress_for(audit: Any) -> dict:
    summary = audit.summary if isinstance(audit.summary, dict) else {}
    saved_progress = summary.get("progress")
    if audit.status == "running" and isinstance(saved_progress, dict):
        return saved_progress
    if audit.status == "queued":
        return {"value": 0, "completed": 0, "total": 4, "step": "等待审查任务启动"}
    if audit.status == "running":
        return {"value": 25, "completed": 1, "total": 4, "step": "正在扫描 Skill"}
    if audit.status == "failed":
        return {
            "value": 100,
            "completed": 0,
            "total": 4,
            "step": audit.error_message or "审查失败",
        }
    return {"value": 100, "completed": 4, "total": 4, "step": "报告已生成"}


def _hit_count(item: dict) -> int:
    value = item.get("hit_count")
    if isinstance(value, int) and value > 0:
        return value
    locations = item.get("locations")
    if isinstance(locations, list) and locations:
        return len(locations)
    return 1


def _severity_counts(findings: list[dict]) -> dict:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for item in findings:
        severity = item.get("severity") or "unknown"
        if severity in counts:
            counts[severity] += _hit_count(item)
    return counts


def _highest_severity(items: list[dict]) -> str:
    return max(
        (item.get("severity") or "unknown" for item in items),
        key=lambda severity: SEVERITY_ORDER.get(severity, 0),
        default="",
    )


def build_summary(audit: Any) -> dict:
    findings = audit.findings or []
    return {
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
        "severity_counts": _severity_counts(findings),
        "progress": progress_for(audit),
    }


def _llm_review(summary: dict) -> dict | None:
    raw = summary.get("llm_review") if isinstance(summary, dict) else None
    return raw if isinstance(raw, dict) else None


def _llm_category_review(llm_review: dict | None, code: str) -> dict | None:
    reviews = llm_review.get("category_reviews") if isinstance(llm_review, dict) else []
    if not isinstance(reviews, list):
        return None
    for item in reviews:
        if isinstance(item, dict) and item.get("code") == code:
            return item
    return None


def _review_method(audit: Any) -> str:
    return "规则扫描 + AI 深度审查" if audit.llm_review_used else "规则扫描"


def _review_note(audit: Any, llm_review: dict | None) -> str:
    if audit.llm_review_used:
        model = audit.llm_review_model or (llm_review or {}).get("model") or "所选模型"
        return (
            f"已完成规则扫描，并由 {model} 做 AI 深度分析。"
            "结果供决策参考，不阻断发布，不改动文件。"
        )
    if llm_review and llm_review.get("status") in {"failed", "unparsed", "skipped"}:
        return "已完成规则扫描。AI 深度分析未完成，本报告以规则扫描结果为准。"
    return "已对 Skill 压缩包完成规则扫描。结果供决策参考，不阻断发布，不改动文件。"


def _summary_text(audit: Any) -> str:
    if audit.status == "failed" or audit.decision == "failed":
        return "审查未完成，请排查后重新发起。"
    if audit.decision == "high_risk":
        return "高危风险集中在供应链依赖与权限控制，建议优先处理后再评估使用。"
    if audit.decision == "attention_required":
        return "存在若干风险，建议逐项确认后决定是否调整。"
    return "未发现明显高危风险。"


def _group_by_category(findings: list[dict]) -> list[tuple[str, list[dict]]]:
    categories: dict[str, list[dict]] = {}
    for item in findings:
        categories.setdefault(item.get("category") or "AST08", []).append(item)
    return sorted(
        categories.items(),
        key=lambda pair: (
            -SEVERITY_ORDER.get(_highest_severity(pair[1]), 0),
            pair[0],
        ),
    )


def _location_line(location: dict) -> str:
    line = location.get("start_line")
    end_line = location.get("end_line")
    suffix = ""
    if line:
        suffix = f":{line}"
        if end_line and end_line != line:
            suffix = f"{suffix}-{end_line}"
    return f"{location.get('file') or '未标明文件'}{suffix}"


def _locations(item: dict) -> list[dict]:
    locations = item.get("locations")
    if isinstance(locations, list) and locations:
        return locations
    loc = item.get("location") or {}
    evidence = item.get("evidence") or {}
    return [
        {
            "file": loc.get("file"),
            "start_line": loc.get("start_line"),
            "end_line": loc.get("end_line"),
            "snippet": evidence.get("snippet") or evidence.get("matched_text") or "",
        }
    ]


def _llm_line(review: dict | None) -> str:
    if not review:
        return ""
    parts = [
        str(review.get("result") or "").strip(),
        str(review.get("reason") or "").strip(),
        str(review.get("recommendation") or "").strip(),
    ]
    return "；".join(part for part in parts if part)


def _category_label(category_labels: dict[str, str], code: str) -> str:
    return category_labels.get(code) or "安全风险"


def build_markdown(audit: Any, category_labels: dict[str, str] | None = None) -> str:
    category_labels = category_labels or {}
    summary = audit.summary or {}
    llm_review = _llm_review(summary)
    findings = audit.findings or []
    categories_with_findings = {item.get("category") for item in findings}
    missed_count = max(0, len(category_labels) - len(categories_with_findings))
    severity_counts = _severity_counts(findings)
    severity_label = SEVERITY_LABELS.get(
        audit.severity or "", audit.severity or "未分级"
    )
    lines = [
        "# AI Policies Skill 安全审查报告",
        "",
        "## 1. 概览",
        f"- 报告编号：{audit.audit_id}",
        f"- Skill：{audit.skill_name}",
        f"- 版本：{audit.skill_version}",
        f"- 风险分：{audit.risk_score}",
        f"- 风险等级：{severity_label}",
        f"- 风险：{len(categories_with_findings)} 类 · {audit.findings_count} 处",
        f"- 审查方式：{_review_method(audit)}",
        "",
        "## 2. 审查说明",
        _review_note(audit, llm_review),
        "",
        "## 3. 审查对象",
        f"- Skill 名称：{audit.skill_name}",
        f"- Skill 版本：{audit.skill_version}",
        f"- 源文件 SHA256：{audit.source_sha256}",
        "",
        "## 4. 风险等级分布",
        f"- 严重：{severity_counts['critical']}",
        f"- 高危：{severity_counts['high']}",
        f"- 中危：{severity_counts['medium']}",
        f"- 低危：{severity_counts['low']}",
        "",
        "## 5. 详细结果",
    ]
    if not findings:
        lines.append("未发现问题。")
    for code, items in _group_by_category(findings):
        category_severity = _highest_severity(items)
        category_count = sum(_hit_count(item) for item in items)
        category_review = _llm_category_review(llm_review, code)
        lines.extend(
            [
                "",
                (
                    f"### {code} {_category_label(category_labels, code)} · "
                    f"{SEVERITY_LABELS.get(category_severity, category_severity)} · "
                    f"{category_count} 处"
                ),
            ]
        )
        for index, item in enumerate(items, 1):
            item_severity = SEVERITY_LABELS.get(
                item.get("severity"), item.get("severity", "")
            )
            lines.extend(
                [
                    "",
                    f"#### {index}. {item.get('title') or '安全风险'}",
                    f"- 风险等级：{item_severity}",
                    f"- 发现：{_hit_count(item)} 处",
                    f"- 风险说明：{item.get('description') or ''}",
                    f"- 处理建议：{item.get('recommendation') or ''}",
                ]
            )
            llm_text = _llm_line(category_review) if audit.llm_review_used else ""
            if llm_text:
                lines.append(f"- AI 研判：{llm_text}")
            lines.append("- 文件：")
            for location in _locations(item):
                lines.append(f"  - {_location_line(location)}")
                snippet = location.get("snippet")
                if snippet:
                    lines.extend(["", "````", snippet, "````"])
                else:
                    lines.append("    未提取到代码片段，可打开上方文件位置查看。")
    if missed_count:
        lines.extend(["", f"其余 {missed_count} 类未发现问题。"])
    lines.extend(["", "## 6. 总结"])
    lines.append(_summary_text(audit))
    lines.extend(
        [
            "",
            "## 7. 声明",
            OWASP_NOTICE,
            "",
            "## 8. 参考",
            "OWASP Agentic Skills Top 10 · AIHelms 审查规则与报告模板",
            "",
        ]
    )
    return "\n".join(lines)

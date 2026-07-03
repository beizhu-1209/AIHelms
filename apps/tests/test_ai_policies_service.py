from types import SimpleNamespace

import pytest

from core.config import settings
from services import (
    ai_policies_llm,
    ai_policies_report,
    ai_policies_scanner_client,
    ai_policies_service,
)
from tasks import ai_policies_tasks

CATEGORY_LABELS = {"AST02": "供应链投毒或依赖风险"}


def test_safe_error_message_hides_generic_exception_details() -> None:
    message = ai_policies_service._safe_error_message(
        RuntimeError("token=secret-value host=10.0.0.1")
    )

    assert message == "安全审查任务执行失败，请稍后重新发起审查"
    assert "secret-value" not in message
    assert "10.0.0.1" not in message


def test_safe_error_message_allows_scanner_safe_message() -> None:
    message = ai_policies_service._safe_error_message(
        ai_policies_scanner_client.AiPoliciesScannerError("安全审查引擎连接失败")
    )

    assert message == "安全审查引擎连接失败"


def test_build_markdown_contains_eight_sections_and_owasp_notice() -> None:
    audit = SimpleNamespace(
        audit_id="AIP-test",
        skill_name="demo-skill",
        skill_version="1.0.0",
        status="completed",
        decision="attention_required",
        severity="low",
        risk_score=7,
        source_sha256="abc",
        scanner="skillspector",
        scanner_version="2.3.9",
        findings_count=2,
        high_risk_count=0,
        must_review_count=0,
        llm_review_used=False,
        llm_review_model="",
        summary={},
        findings=[
            {
                "title": "未固定 npx 包版本，存在供应链替换风险",
                "severity": "low",
                "category": "AST02",
                "hit_count": 2,
                "locations": [
                    {
                        "file": "SKILL.md",
                        "start_line": 23,
                        "snippet": "23 | npx skills",
                    },
                    {
                        "file": "SKILL.md",
                        "start_line": 24,
                        "snippet": "24 | npx tools",
                    },
                ],
                "description": "检测到 npx 调用未固定明确版本。",
                "recommendation": "固定到明确版本。",
            }
        ],
    )

    markdown = ai_policies_report.build_markdown(audit, CATEGORY_LABELS)

    assert "## 5. 详细结果" in markdown
    assert "## 8. 参考" in markdown
    assert "OWASP Agentic Skills Top 10" in markdown
    assert "AST02 供应链投毒或依赖风险" in markdown
    assert "发现：2 处" in markdown
    assert "23 | npx skills" in markdown


def test_running_progress_uses_saved_progress() -> None:
    audit = SimpleNamespace(
        status="running",
        summary={
            "progress": {
                "value": 75,
                "completed": 3,
                "total": 4,
                "step": "正在进行 AI 深度审查",
            }
        },
    )

    assert ai_policies_report.progress_for(audit) == {
        "value": 75,
        "completed": 3,
        "total": 4,
        "step": "正在进行 AI 深度审查",
    }


def test_llm_category_reviews_marks_uncovered_categories_without_fake_result() -> None:
    reviews = ai_policies_llm.llm_category_reviews(
        {"category_reviews": []},
        [{"category": "AST02"}, {"category": "AST02"}],
        CATEGORY_LABELS,
    )

    assert reviews == [
        {
            "code": "AST02",
            "name": "供应链投毒或依赖风险",
            "result": "LLM 未单独研判",
            "reason": "",
            "recommendation": "",
        }
    ]


def test_llm_policy_safe_text_avoids_publish_blocking_language() -> None:
    text = ai_policies_llm._policy_safe_text(
        "该技能风险极高，建议拒绝发布；系统不应自动阻断发布；应立即拒绝并隔离。",
        200,
    )

    assert "拒绝发布" not in text
    assert "阻断发布" not in text
    assert "应立即拒绝" not in text
    assert "暂缓发布" in text


@pytest.mark.asyncio
async def test_run_llm_review_uses_platform_model_and_returns_category_reviews(
    monkeypatch,
) -> None:
    captured_kwargs = {}

    async def fake_find_by_id(session, model_id):
        credential = SimpleNamespace(
            is_active=True,
            credential_info={"format": "openai"},
        )
        deployment = SimpleNamespace(is_active=True, credential=credential)
        return SimpleNamespace(
            id=model_id,
            model_id="qwen-audit",
            name="Qwen",
            is_active=True,
            category="chat",
            deployments=[deployment],
        )

    async def fake_chat_completion(model, messages, **kwargs):
        captured_kwargs.update(kwargs)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"overall_judgement":"建议复核供应链风险",'
                            '"reason":"存在未固定版本",'
                            '"category_reviews":[{"code":"AST02",'
                            '"result":"需处理","reason":"npx 未固定版本",'
                            '"recommendation":"固定版本"}]}'
                        )
                    }
                }
            ]
        }

    async def fake_find_user_by_id(session, user_id):
        return SimpleNamespace(
            id=user_id,
            username="testadmin",
            is_active=True,
            litellm_user_id=f"aihelms_user_{user_id}",
        )

    async def fake_find_personal_main(session, user_id):
        return SimpleNamespace(
            id=47,
            is_active=True,
            litellm_key_id="sk-user-main",
            litellm_key_alias="user:testadmin/main",
            models=["qwen-audit"],
        )

    monkeypatch.setattr(ai_policies_llm.model_repo, "find_by_id", fake_find_by_id)
    monkeypatch.setattr(
        ai_policies_llm.user_repo, "find_user_by_id", fake_find_user_by_id
    )
    monkeypatch.setattr(
        ai_policies_llm.ai_key_repo,
        "find_personal_main",
        fake_find_personal_main,
    )
    monkeypatch.setattr(
        ai_policies_llm.litellm_client,
        "chat_completion",
        fake_chat_completion,
    )
    audit = SimpleNamespace(
        audit_id="AIP-test",
        skill_name="demo-skill",
        skill_version="1.0.0",
        risk_score=7,
        severity="low",
        skill_id=18,
        created_by=48,
    )

    result = await ai_policies_llm.run_llm_review(
        None,
        9,
        audit,
        [{"category": "AST02", "title": "未固定 npx 包版本"}],
        CATEGORY_LABELS,
    )

    assert result["status"] == "completed"
    assert result["model"] == "Qwen"
    assert result["category_reviews"][0]["code"] == "AST02"
    assert result["category_reviews"][0]["recommendation"] == "固定版本"
    assert captured_kwargs["api_key"] == "sk-user-main"
    assert captured_kwargs["user"] == "aihelms_user_48"
    assert captured_kwargs["metadata"]["aihelms_user_id"] == 48
    assert captured_kwargs["metadata"]["aihelms_ai_key_id"] == 47


@pytest.mark.asyncio
async def test_run_llm_review_does_not_fake_category_reviews_when_unparsed(
    monkeypatch,
) -> None:
    async def fake_find_by_id(session, model_id):
        credential = SimpleNamespace(
            is_active=True,
            credential_info={"format": "openai"},
        )
        deployment = SimpleNamespace(is_active=True, credential=credential)
        return SimpleNamespace(
            id=model_id,
            model_id="qwen-audit",
            name="Qwen",
            is_active=True,
            category="chat",
            deployments=[deployment],
        )

    async def fake_chat_completion(model, messages, **kwargs):
        return {"choices": [{"message": {"content": "无法给出 JSON"}}]}

    async def fake_find_user_by_id(session, user_id):
        return SimpleNamespace(
            id=user_id,
            username="testadmin",
            is_active=True,
            litellm_user_id=f"aihelms_user_{user_id}",
        )

    async def fake_find_personal_main(session, user_id):
        return SimpleNamespace(
            id=47,
            is_active=True,
            litellm_key_id="sk-user-main",
            litellm_key_alias="user:testadmin/main",
            models=["qwen-audit"],
        )

    monkeypatch.setattr(ai_policies_llm.model_repo, "find_by_id", fake_find_by_id)
    monkeypatch.setattr(
        ai_policies_llm.user_repo, "find_user_by_id", fake_find_user_by_id
    )
    monkeypatch.setattr(
        ai_policies_llm.ai_key_repo,
        "find_personal_main",
        fake_find_personal_main,
    )
    monkeypatch.setattr(
        ai_policies_llm.litellm_client,
        "chat_completion",
        fake_chat_completion,
    )

    result = await ai_policies_llm.run_llm_review(
        None,
        9,
        SimpleNamespace(
            audit_id="AIP-test",
            skill_name="demo-skill",
            skill_version="1.0.0",
            risk_score=70,
            severity="high",
            skill_id=18,
            created_by=48,
        ),
        [{"category": "AST02", "title": "未固定 npx 包版本"}],
        CATEGORY_LABELS,
    )

    assert result["status"] == "unparsed"
    assert result["category_reviews"] == []
    assert "需复核" not in str(result)


@pytest.mark.asyncio
async def test_run_llm_review_skips_without_current_admin_ai_identity(
    monkeypatch,
) -> None:
    async def fake_find_by_id(session, model_id):
        credential = SimpleNamespace(
            is_active=True,
            credential_info={"format": "openai"},
        )
        deployment = SimpleNamespace(is_active=True, credential=credential)
        return SimpleNamespace(
            id=model_id,
            model_id="qwen-audit",
            name="Qwen",
            is_active=True,
            category="chat",
            deployments=[deployment],
        )

    async def fake_find_user_by_id(session, user_id):
        return SimpleNamespace(
            id=user_id,
            username="testadmin",
            is_active=True,
            litellm_user_id=f"aihelms_user_{user_id}",
        )

    async def fake_find_personal_main(session, user_id):
        return None

    async def fake_chat_completion(model, messages, **kwargs):
        raise AssertionError("LLM 调用不应在缺少管理员 AI 身份时发生")

    monkeypatch.setattr(ai_policies_llm.model_repo, "find_by_id", fake_find_by_id)
    monkeypatch.setattr(
        ai_policies_llm.user_repo, "find_user_by_id", fake_find_user_by_id
    )
    monkeypatch.setattr(
        ai_policies_llm.ai_key_repo,
        "find_personal_main",
        fake_find_personal_main,
    )
    monkeypatch.setattr(
        ai_policies_llm.litellm_client,
        "chat_completion",
        fake_chat_completion,
    )

    result = await ai_policies_llm.run_llm_review(
        None,
        9,
        SimpleNamespace(
            audit_id="AIP-test",
            skill_name="demo-skill",
            skill_version="1.0.0",
            risk_score=70,
            severity="high",
            skill_id=18,
            created_by=48,
        ),
        [{"category": "AST02", "title": "未固定 npx 包版本"}],
        CATEGORY_LABELS,
    )

    assert result == {
        "status": "skipped",
        "message": "发起审查的管理员未配置可用的个人主 Key",
    }


def test_aggregate_findings_groups_locations_and_keeps_hit_count() -> None:
    normalized = [
        {
            "source": "static",
            "rule_id": "RP1",
            "category": "AST02",
            "raw_category": "MCP Rug Pull",
            "severity": "high",
            "confidence": 90,
            "title": "未固定 npx 包版本",
            "description": "依赖未固定版本。",
            "recommendation": "固定到明确版本。",
            "location": {"file": "SKILL.md", "start_line": 10, "end_line": 10},
            "evidence": {"snippet": "10 | npx demo"},
            "must_review": True,
        },
        {
            "source": "static",
            "rule_id": "RP1",
            "category": "AST02",
            "raw_category": "MCP Rug Pull",
            "severity": "critical",
            "confidence": 80,
            "title": "未固定 npx 包版本",
            "description": "依赖未固定版本。",
            "recommendation": "固定到明确版本。",
            "location": {"file": "SKILL.md", "start_line": 12, "end_line": 12},
            "evidence": {"snippet": "12 | npx demo"},
            "must_review": True,
        },
    ]

    groups = ai_policies_service._aggregate_findings(normalized)

    assert len(groups) == 1
    assert groups[0]["hit_count"] == 2
    assert groups[0]["severity"] == "critical"
    assert groups[0]["locations"][1]["start_line"] == 12


@pytest.mark.asyncio
async def test_process_skill_audit_marks_failed_with_safe_error(monkeypatch) -> None:
    audit = SimpleNamespace(
        id=1,
        audit_id="AIP-fail",
        audit_type="skill",
        skill_id=7,
        skill_name="demo-skill",
        skill_version="1.0.0",
        source_sha256="abc",
        scanner="",
        scanner_version="",
        status="queued",
        decision="",
        severity="",
        risk_score=0,
        findings_count=0,
        high_risk_count=0,
        must_review_count=0,
        llm_review_used=False,
        llm_review_model="",
        error_message="",
        started_at=None,
        finished_at=None,
        created_at=None,
        updated_at=None,
        summary={},
        findings=[],
        raw_report={},
        markdown_report="",
    )
    skill = SimpleNamespace(
        id=7,
        zip_path="/tmp/demo-skill.zip",
        security_status="queued",
        security_decision="",
        security_severity="",
        latest_ai_policies_audit_id=None,
    )
    commit_count = 0

    class FakeSession:
        async def commit(self):
            nonlocal commit_count
            commit_count += 1

    async def fake_find_audit(session, audit_pk):
        return audit

    async def fake_find_skill(session, skill_id):
        return skill

    async def fake_scan(target):
        raise RuntimeError("token=secret-value host=10.0.0.1")

    async def fake_list_catalog(session):
        return []

    monkeypatch.setattr(
        ai_policies_service.ai_policies_repo, "find_by_id", fake_find_audit
    )
    monkeypatch.setattr(
        ai_policies_service.ai_policies_repo, "list_catalog", fake_list_catalog
    )
    monkeypatch.setattr(ai_policies_service.skill_repo, "find_by_id", fake_find_skill)
    monkeypatch.setattr(ai_policies_service.os.path, "exists", lambda path: True)
    monkeypatch.setattr(
        ai_policies_service.ai_policies_scanner_client, "scan_skill_zip", fake_scan
    )

    await ai_policies_service.process_skill_audit(FakeSession(), 1)

    assert audit.status == "failed"
    assert audit.decision == "failed"
    assert audit.error_message == "安全审查任务执行失败，请稍后重新发起审查"
    assert "secret-value" not in audit.error_message
    assert "10.0.0.1" not in audit.error_message
    assert skill.security_status == "failed"
    assert skill.security_decision == "failed"
    assert commit_count >= 2


def test_celery_time_limits_exceed_scanner_http_timeout() -> None:
    scanner_http_timeout = settings.ai_policies_timeout_seconds + 10

    assert ai_policies_tasks.AUDIT_SOFT_TIME_LIMIT > scanner_http_timeout
    assert ai_policies_tasks.AUDIT_TIME_LIMIT > ai_policies_tasks.AUDIT_SOFT_TIME_LIMIT

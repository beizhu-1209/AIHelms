CREATE TABLE aihelms.ai_policies_audits (
    id BIGSERIAL PRIMARY KEY,
    audit_id VARCHAR(64) NOT NULL UNIQUE,
    audit_type VARCHAR(32) NOT NULL DEFAULT 'skill',
    skill_id BIGINT REFERENCES aihelms.skills(id) ON DELETE SET NULL,
    skill_name VARCHAR(128) NOT NULL DEFAULT '',
    skill_version VARCHAR(64) NOT NULL DEFAULT '',
    source_sha256 VARCHAR(64) NOT NULL DEFAULT '',
    scanner VARCHAR(64) NOT NULL DEFAULT '',
    scanner_version VARCHAR(64) NOT NULL DEFAULT '',
    mode VARCHAR(32) NOT NULL DEFAULT 'static',
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    decision VARCHAR(32) NOT NULL DEFAULT '',
    severity VARCHAR(32) NOT NULL DEFAULT '',
    risk_score INTEGER NOT NULL DEFAULT 0,
    findings_count INTEGER NOT NULL DEFAULT 0,
    high_risk_count INTEGER NOT NULL DEFAULT 0,
    must_review_count INTEGER NOT NULL DEFAULT 0,
    llm_review_used BOOLEAN NOT NULL DEFAULT false,
    llm_review_model VARCHAR(128) NOT NULL DEFAULT '',
    created_by BIGINT REFERENCES aihelms.users(id) ON DELETE SET NULL,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    summary JSONB NOT NULL DEFAULT '{}',
    findings JSONB NOT NULL DEFAULT '[]',
    raw_report JSONB NOT NULL DEFAULT '{}',
    markdown_report TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT ''
);

CREATE INDEX idx_ai_policies_audits_audit_type ON aihelms.ai_policies_audits(audit_type);
CREATE INDEX idx_ai_policies_audits_skill_id ON aihelms.ai_policies_audits(skill_id);
CREATE INDEX idx_ai_policies_audits_status ON aihelms.ai_policies_audits(status);
CREATE INDEX idx_ai_policies_audits_decision ON aihelms.ai_policies_audits(decision);
CREATE INDEX idx_ai_policies_audits_finished_at ON aihelms.ai_policies_audits(finished_at DESC);

CREATE TABLE aihelms.ai_policies_risk_catalog (
    code VARCHAR(16) PRIMARY KEY,
    name_en VARCHAR(128) NOT NULL,
    name_zh VARCHAR(128) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    description_zh TEXT NOT NULL DEFAULT '',
    check_points JSONB NOT NULL DEFAULT '[]',
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE aihelms.ai_policies_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    llm_review_enabled BOOLEAN NOT NULL DEFAULT false,
    llm_review_model_id BIGINT REFERENCES aihelms.models(id) ON DELETE SET NULL,
    updated_by BIGINT REFERENCES aihelms.users(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ai_policies_settings_singleton CHECK (id = 1)
);

INSERT INTO aihelms.ai_policies_settings (id)
VALUES (1);

ALTER TABLE aihelms.skills
    ADD COLUMN security_status VARCHAR(32) NOT NULL DEFAULT 'not_scanned',
    ADD COLUMN security_decision VARCHAR(32) NOT NULL DEFAULT '',
    ADD COLUMN security_severity VARCHAR(32) NOT NULL DEFAULT '',
    ADD COLUMN security_risk_score INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN latest_ai_policies_audit_id BIGINT REFERENCES aihelms.ai_policies_audits(id) ON DELETE SET NULL;

CREATE INDEX idx_skills_security_status ON aihelms.skills(security_status);
CREATE INDEX idx_skills_latest_ai_policies_audit_id ON aihelms.skills(latest_ai_policies_audit_id);

INSERT INTO aihelms.ai_policies_risk_catalog
    (code, name_en, name_zh, severity, description_zh, check_points, sort_order)
VALUES
    ('AST01', 'Malicious Skills', '恶意技能或隐藏意图', 'critical', '检查 Skill 是否存在与描述不一致的隐藏行为、恶意指令、策略绕过或异常执行意图。', '["策略绕过指令", "敏感数据收集", "隐藏恶意意图"]', 1),
    ('AST02', 'Supply Chain Compromise', '供应链投毒或依赖风险', 'critical', '检查依赖来源、安装脚本、动态下载、包名混淆、未固定版本和远程脚本执行风险。', '["未固定依赖版本", "远程脚本执行", "不可信包来源"]', 2),
    ('AST03', 'Over-Privileged Skills', '权限过大', 'high', '检查文件、网络、shell 或工具权限是否超过 Skill 实际业务需要。', '["宽泛文件访问", "任意网络访问", "Shell 权限申请"]', 3),
    ('AST04', 'Insecure Metadata', '元数据不安全', 'high', '检查 Skill 元数据是否缺失、误导或未披露关键权限和风险边界。', '["元数据缺失", "描述与行为不一致", "缺少权限披露"]', 4),
    ('AST05', 'Untrusted External Instructions', '不可信外部指令', 'high', '检查是否从不可信远程来源加载说明、提示词、脚本或运行规则。', '["外部指令加载", "远程脚本执行", "缺少完整性校验"]', 5),
    ('AST06', 'Weak Isolation', '隔离边界薄弱', 'high', '检查 Skill 是否可能突破运行边界、影响宿主环境或绕过工具隔离。', '["危险命令", "敏感路径写入", "工具链绕过"]', 6),
    ('AST07', 'Update Drift', '更新漂移', 'medium', '检查版本、来源、依赖和更新路径是否可追踪，避免上线后行为漂移。', '["版本可追踪", "可信更新来源", "依赖固定"]', 7),
    ('AST08', 'Poor Scanning', '审查证据不足', 'medium', '检查是否缺少可复现的审查记录、文件清单、命中证据或验证材料。', '["存在审查记录", "文件清单完整", "证据可复现"]', 8),
    ('AST09', 'No Governance', '治理缺失', 'medium', '检查是否缺少所有者、版本、审批、风险处理建议或生命周期管理流程。', '["存在所有者", "存在版本", "存在处理建议"]', 9),
    ('AST10', 'Cross-Platform Risks', '跨平台传播风险', 'medium', '检查风险是否会跨 Agent、MCP、脚本或外部平台传播。', '["外部数据传输", "跨平台执行", "边界披露"]', 10);

INSERT INTO aihelms.permissions (code, name, resource, action, description)
VALUES
    ('ai_policies:read', '查看 AI Policies', 'ai_policies', 'read', '查看 AI Policies 审查任务和报告'),
    ('ai_policies:scan', '发起 AI Policies 审查', 'ai_policies', 'scan', '发起 Skill 安全审查'),
    ('ai_policies:config', '配置 AI Policies', 'ai_policies', 'config', '配置 LLM 审查引擎');


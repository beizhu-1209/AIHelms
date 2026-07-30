-- AIHelms 数据库初始化脚本
-- 创建多个 schema 隔离不同模块数据

-- LiteLLM 使用默认 public schema

-- AIHelms 业务 schema
CREATE SCHEMA IF NOT EXISTS aihelms;

-- 用户表
CREATE TABLE IF NOT EXISTS aihelms.users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    phone VARCHAR(20) DEFAULT '',
    display_name VARCHAR(100) DEFAULT '',
    avatar VARCHAR(500) DEFAULT '',
    position VARCHAR(100) DEFAULT '',
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    is_super_admin BOOLEAN DEFAULT false,
    litellm_user_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- API Key 表（管理员服务账户 Key，分发给第三方系统调用平台 API）
CREATE TABLE IF NOT EXISTS aihelms.api_keys (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT DEFAULT '',
    key_prefix VARCHAR(12) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_encrypted TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN DEFAULT true,
    created_by BIGINT NOT NULL REFERENCES aihelms.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_created_by ON aihelms.api_keys(created_by);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON aihelms.api_keys(key_hash);

-- 用量记录表
CREATE TABLE IF NOT EXISTS aihelms.usage_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES aihelms.users(id),
    model VARCHAR(128) NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost NUMERIC(10, 6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 部门表（树形多层级，所有部门同步为 LiteLLM Team）
CREATE TABLE IF NOT EXISTS aihelms.departments (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    parent_id BIGINT REFERENCES aihelms.departments(id),
    description TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    litellm_team_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 项目表（扁平一级，每个项目同步为 LiteLLM Team）
CREATE TABLE IF NOT EXISTS aihelms.projects (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT DEFAULT '',
    is_active BOOLEAN DEFAULT true,
    litellm_team_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户-部门 多对多
CREATE TABLE IF NOT EXISTS aihelms.user_departments (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES aihelms.users(id) ON DELETE CASCADE,
    department_id BIGINT NOT NULL REFERENCES aihelms.departments(id) ON DELETE CASCADE,
    is_manager BOOLEAN DEFAULT false,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, department_id)
);

-- 用户-项目 多对多
CREATE TABLE IF NOT EXISTS aihelms.user_projects (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES aihelms.users(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES aihelms.projects(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, project_id)
);

-- 角色表
CREATE TABLE IF NOT EXISTS aihelms.roles (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    display_name VARCHAR(128) NOT NULL,
    description TEXT DEFAULT '',
    is_system BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 权限点表
CREATE TABLE IF NOT EXISTS aihelms.permissions (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    resource VARCHAR(64) NOT NULL,
    action VARCHAR(32) NOT NULL,
    description TEXT DEFAULT ''
);

-- 角色-权限 多对多
CREATE TABLE IF NOT EXISTS aihelms.role_permissions (
    id BIGSERIAL PRIMARY KEY,
    role_id BIGINT NOT NULL REFERENCES aihelms.roles(id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES aihelms.permissions(id) ON DELETE CASCADE,
    UNIQUE (role_id, permission_id)
);

-- 用户-角色 多对多
CREATE TABLE IF NOT EXISTS aihelms.user_roles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES aihelms.users(id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL REFERENCES aihelms.roles(id) ON DELETE CASCADE,
    UNIQUE (user_id, role_id)
);

-- 使用场景标签
CREATE TABLE IF NOT EXISTS aihelms.key_scenarios (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 业务场景字典（AI 效能模块使用，给资源打业务场景标签）
-- 必须在 models / mcp_servers / skills / agents 之前创建（被引用）
CREATE TABLE IF NOT EXISTS aihelms.business_scenarios (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT DEFAULT '',
    icon VARCHAR(50) DEFAULT 'Target',
    icon_url VARCHAR(500),
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO aihelms.business_scenarios (code, name, icon, sort_order) VALUES
    ('code_dev',         '代码开发', 'Code2',         10),
    ('customer_service', '客户服务', 'Headphones',    20),
    ('data_analysis',    '数据分析', 'BarChart3',     30),
    ('content_creation', '内容创作', 'PenLine',       40),
    ('document',         '文档处理', 'FileText',      50),
    ('translation',      '翻译',     'Languages',     60),
    ('other',            '其他',     'Target',        999)
ON CONFLICT (code) DO NOTHING;

-- Enterprise License singleton
CREATE TABLE IF NOT EXISTS aihelms.license (
    id INTEGER PRIMARY KEY DEFAULT 1,
    licensed_to TEXT,
    features JSONB NOT NULL DEFAULT '[]',
    issued_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    license_key TEXT,
    status TEXT NOT NULL DEFAULT 'invalid',
    imported_at TIMESTAMPTZ,
    CONSTRAINT license_singleton CHECK (id = 1)
);

-- Whitelabel branding singleton
CREATE TABLE IF NOT EXISTS aihelms.branding (
    id INTEGER PRIMARY KEY DEFAULT 1,
    platform_name TEXT NOT NULL DEFAULT 'AIHelms',
    logo_path TEXT,
    square_logo_path TEXT,
    favicon_path TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT branding_singleton CHECK (id = 1)
);

INSERT INTO aihelms.branding (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- MCP 分类（必须在 mcp_servers 之前创建）
CREATE TABLE IF NOT EXISTS aihelms.mcp_categories (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO aihelms.mcp_categories (name, sort_order) VALUES
    ('general', 0),
    ('search', 10)
ON CONFLICT (name) DO NOTHING;

-- AI 身份 Key 表
CREATE TABLE IF NOT EXISTS aihelms.ai_keys (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT DEFAULT '',
    key_type VARCHAR(20) NOT NULL,          -- 'personal_main' | 'personal_scene' | 'dept_shared' | 'project_shared'
    owner_type VARCHAR(20) NOT NULL,        -- 'user' | 'department' | 'project'
    owner_id BIGINT NOT NULL,
    tags JSONB DEFAULT '[]',
    litellm_key_id VARCHAR(100),
    litellm_key_alias VARCHAR(200),
    models JSONB DEFAULT '[]',
    mcps JSONB DEFAULT '[]',                -- 允许使用的 MCP Server id 列表
    skills JSONB DEFAULT '[]',              -- 允许使用的 Skill id 列表
    agents JSONB DEFAULT '[]',              -- 允许使用的 Agent id 列表
    budget_limit NUMERIC(12,4),
    budget_used NUMERIC(12,4) DEFAULT 0,
    budget_hard_limit BOOLEAN DEFAULT false,
    budget_duration VARCHAR(10) DEFAULT '30d',  -- '30d' | '7d' | '1d'
    budget_scope VARCHAR(20) DEFAULT 'unified',  -- 'unified' | 'per_type' | 'per_resource'
    budget_models_total NUMERIC(12,4),
    budget_mcps_total NUMERIC(12,4),
    budget_models_per VARCHAR(10) DEFAULT 'unified',  -- 'unified' | 'each'
    budget_mcps_per VARCHAR(10) DEFAULT 'unified',
    model_budgets JSONB DEFAULT '{}',
    mcp_budgets JSONB DEFAULT '{}',
    rate_limit_mode VARCHAR(20) DEFAULT 'none',
    tpm_limit INT,
    rpm_limit INT,
    max_parallel_requests INT,
    scenario_id BIGINT REFERENCES aihelms.key_scenarios(id),
    is_active BOOLEAN DEFAULT false,
    created_by BIGINT REFERENCES aihelms.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ
);

-- 供应商（平台独有，组织凭证 + 额度监控）
CREATE TABLE IF NOT EXISTS aihelms.providers (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,       -- 'anthropic' | 'openai' | 'azure' | 'vertex_ai' | 'bedrock' | 'deepseek' | 'custom'
    billing_type VARCHAR(20) NOT NULL DEFAULT 'token',  -- 'token' | 'per_call' | 'monthly_quota'
    monthly_budget NUMERIC(12,4),
    monthly_used NUMERIC(12,4) DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    description TEXT DEFAULT '',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 供应商前缀映射表（LiteLLM 路由前缀对照）
CREATE TABLE IF NOT EXISTS aihelms.provider_prefix_map (
    id BIGSERIAL PRIMARY KEY,
    provider_type VARCHAR(50) NOT NULL,
    format VARCHAR(20) NOT NULL,            -- 'openai' | 'anthropic' | 'ollama'
    category VARCHAR(50) NOT NULL,          -- 'chat' | 'embedding' | 'rerank' | 'completion' | 'image' | 'audio'
    prefix VARCHAR(50) NOT NULL,            -- LiteLLM 路由前缀，如 'openai', 'anthropic', 'hosted_vllm'
    needs_v1 BOOLEAN DEFAULT false,         -- api_base 是否需要自动补 /v1
    UNIQUE(provider_type, format, category)
);

-- 初始数据
INSERT INTO aihelms.provider_prefix_map (provider_type, format, category, prefix, needs_v1) VALUES
    -- 有专属前缀的供应商
    ('openai', 'openai', 'chat', 'openai', false),
    ('openai', 'openai', 'embedding', 'openai', false),
    ('openai', 'openai', 'image', 'openai', false),
    ('openai', 'openai', 'audio', 'openai', false),
    ('anthropic', 'anthropic', 'chat', 'anthropic', false),
    ('azure', 'openai', 'chat', 'azure', false),
    ('azure', 'openai', 'embedding', 'azure', false),
    ('google', 'openai', 'chat', 'gemini', false),
    ('google', 'openai', 'embedding', 'gemini', false),
    ('deepseek', 'openai', 'chat', 'deepseek', false),
    ('deepseek', 'anthropic', 'chat', 'anthropic', false),
    ('bedrock', 'openai', 'chat', 'bedrock', false),
    ('bedrock', 'openai', 'embedding', 'bedrock', false),
    ('vertex_ai', 'openai', 'chat', 'vertex_ai', false),
    ('vertex_ai', 'openai', 'embedding', 'vertex_ai', false),
    -- 兼容多格式的供应商
    ('volcengine', 'openai', 'chat', 'openai', true),
    ('volcengine', 'openai', 'embedding', 'openai', true),
    ('volcengine', 'anthropic', 'chat', 'anthropic', false),
    ('dashscope', 'openai', 'chat', 'openai', true),
    ('dashscope', 'openai', 'embedding', 'openai', true),
    ('dashscope', 'anthropic', 'chat', 'anthropic', false),
    ('zhipu', 'openai', 'chat', 'openai', true),
    ('zhipu', 'anthropic', 'chat', 'anthropic', false),
    ('moonshot', 'openai', 'chat', 'openai', true),
    ('moonshot', 'anthropic', 'chat', 'anthropic', false),
    ('minimax', 'openai', 'chat', 'openai', true),
    ('minimax', 'anthropic', 'chat', 'anthropic', false),
    -- 自部署
    ('vllm', 'openai', 'chat', 'hosted_vllm', true),
    ('vllm', 'openai', 'embedding', 'openai', true),
    ('vllm', 'openai', 'rerank', 'hosted_vllm', true),
    ('sglang', 'openai', 'chat', 'hosted_vllm', true),
    ('sglang', 'openai', 'embedding', 'openai', true),
    ('ollama', 'ollama', 'chat', 'ollama', false),
    ('ollama', 'ollama', 'embedding', 'ollama', false),
    ('lmstudio', 'openai', 'chat', 'openai', true),
    -- 小米 MiMo
    ('xiaomi_mimo', 'openai', 'chat', 'xiaomi_mimo', false),
    ('xiaomi_mimo', 'anthropic', 'chat', 'anthropic', false),
    -- 腾讯混元与 xAI
    ('tencent', 'openai', 'chat', 'tencent', true),
    ('xai', 'openai', 'chat', 'xai', false),
    -- 其他
    ('other', 'openai', 'chat', 'openai', true),
    ('other', 'openai', 'embedding', 'openai', true),
    ('other', 'anthropic', 'chat', 'anthropic', false)
ON CONFLICT DO NOTHING;

-- 凭证（对齐 LiteLLM CredentialsTable）
CREATE TABLE IF NOT EXISTS aihelms.credentials (
    id BIGSERIAL PRIMARY KEY,
    credential_name VARCHAR(128) NOT NULL,   -- 凭证名（同步到 LiteLLM）
    provider_id BIGINT REFERENCES aihelms.providers(id) ON DELETE SET NULL,
    credential_values JSONB NOT NULL DEFAULT '{}', -- 加密存储的认证信息（api_key, api_base 等）
    credential_info JSONB DEFAULT '{}',            -- 描述/元信息
    litellm_synced BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(credential_name, provider_id)
);

-- 平台统一模型（展示层）
CREATE TABLE IF NOT EXISTS aihelms.models (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    model_id VARCHAR(128) UNIQUE,              -- 用户请求时用的名称 = LiteLLM model_name，首次添加凭证时设置
    category VARCHAR(50) DEFAULT 'chat',
    capabilities JSONB DEFAULT '[]',
    description TEXT DEFAULT '',
    logo_provider_type VARCHAR(50) DEFAULT '',
    business_scenario_id BIGINT REFERENCES aihelms.business_scenarios(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT true,
    is_published BOOLEAN DEFAULT false,       -- 是否发布到用户端
    visibility_type VARCHAR(20) DEFAULT 'all', -- 'all' | 'selected'
    requires_approval BOOLEAN DEFAULT false,  -- 用户领用是否需要审批
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 模型部署（对齐 LiteLLM ProxyModelTable）
CREATE TABLE IF NOT EXISTS aihelms.model_deployments (
    id BIGSERIAL PRIMARY KEY,
    model_id BIGINT NOT NULL REFERENCES aihelms.models(id) ON DELETE CASCADE,
    credential_id BIGINT REFERENCES aihelms.credentials(id) ON DELETE SET NULL,
    -- LiteLLM 原生字段
    litellm_model_id VARCHAR(100),                 -- LiteLLM 返回的 deployment UUID
    litellm_params JSONB NOT NULL DEFAULT '{}',    -- 完整 litellm_params JSON
    model_info JSONB DEFAULT '{}',                 -- LiteLLM model_info
    -- 平台扩展字段
    deploy_name VARCHAR(128) DEFAULT '',           -- 部署别名
    billing_type VARCHAR(20) DEFAULT 'token',      -- 'token' | 'per_call' | 'monthly_quota'
    cost_per_call NUMERIC(8,4),                    -- 按次计费单价
    monthly_call_quota INT,                        -- 包月次数上限
    monthly_call_used INT DEFAULT 0,               -- 当月已用次数
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 模型访问组
CREATE TABLE IF NOT EXISTS aihelms.model_access_groups (
    id BIGSERIAL PRIMARY KEY,
    group_name VARCHAR(128) NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    model_ids JSONB DEFAULT '[]',                  -- 关联的 models.model_id 列表
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 模型-部门可见性（发布到指定部门，批量操作快捷方式）
CREATE TABLE IF NOT EXISTS aihelms.model_department_visibility (
    id BIGSERIAL PRIMARY KEY,
    model_id BIGINT NOT NULL REFERENCES aihelms.models(id) ON DELETE CASCADE,
    department_id BIGINT NOT NULL REFERENCES aihelms.departments(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(model_id, department_id)
);

-- 模型-用户可见性（实际权限落在用户身上）
CREATE TABLE IF NOT EXISTS aihelms.model_user_visibility (
    id BIGSERIAL PRIMARY KEY,
    model_id BIGINT NOT NULL REFERENCES aihelms.models(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES aihelms.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(model_id, user_id)
);

-- 路由配置（全局单行）
CREATE TABLE IF NOT EXISTS aihelms.router_settings (
    id BIGSERIAL PRIMARY KEY,
    routing_strategy VARCHAR(50) DEFAULT 'simple-shuffle',
    fallbacks JSONB DEFAULT '[]',
    allowed_fails INT DEFAULT 3,
    cooldown_time INT DEFAULT 60,
    num_retries INT DEFAULT 2,
    timeout INT DEFAULT 30,
    config JSONB DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 插入默认路由配置
INSERT INTO aihelms.router_settings (routing_strategy) VALUES ('simple-shuffle') ON CONFLICT DO NOTHING;

-- Key 模型限制（每个 key 对每个模型的速率限制）
CREATE TABLE IF NOT EXISTS aihelms.ai_key_model_limits (
    id BIGSERIAL PRIMARY KEY,
    ai_key_id BIGINT NOT NULL REFERENCES aihelms.ai_keys(id) ON DELETE CASCADE,
    model_id BIGINT NOT NULL REFERENCES aihelms.models(id) ON DELETE CASCADE,
    tpm INT,                                  -- 每分钟 token 上限（NULL=不限制）
    rpm INT,                                  -- 每分钟请求上限（NULL=不限制）
    max_tokens INT,                           -- 单次最大 token（NULL=不限制）
    max_calls INT,                            -- 总调用次数上限（NULL=不限制）
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ai_key_id, model_id)
);

-- MCP 服务表（平台数据源，LiteLLM 超集）
CREATE TABLE IF NOT EXISTS aihelms.mcp_servers (
    id BIGSERIAL PRIMARY KEY,
    server_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    server_name VARCHAR(128) NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    url TEXT NOT NULL,
    transport VARCHAR(20) NOT NULL DEFAULT 'sse',
    auth_type VARCHAR(30) DEFAULT 'none',
    credentials JSONB DEFAULT '{}',
    instructions TEXT DEFAULT '',
    mcp_info JSONB DEFAULT '{}',
    extra_headers TEXT[] DEFAULT '{}',
    allowed_tools JSONB DEFAULT '[]',
    authorization_url TEXT,
    token_url TEXT,
    registration_url TEXT,
    category VARCHAR(50) DEFAULT 'general',
    tags JSONB DEFAULT '[]',
    business_scenario_id BIGINT REFERENCES aihelms.business_scenarios(id) ON DELETE SET NULL,
    author VARCHAR(128) DEFAULT '',
    icon_url VARCHAR(500) DEFAULT '',
    documentation_url VARCHAR(500) DEFAULT '',
    source_url VARCHAR(500) DEFAULT '',
    billing_type VARCHAR(20) DEFAULT 'per_call',
    internal_cost_per_call NUMERIC(10,6) DEFAULT 0,
    external_cost_per_call NUMERIC(10,6) DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    is_published BOOLEAN DEFAULT false,
    visibility_type VARCHAR(20) DEFAULT 'all',
    requires_approval BOOLEAN DEFAULT false,
    status VARCHAR(20) DEFAULT 'unknown',
    call_count INTEGER DEFAULT 0,
    last_health_check TIMESTAMPTZ,
    health_check_error TEXT,
    litellm_synced BOOLEAN DEFAULT false,
    litellm_sync_error TEXT,
    litellm_synced_at TIMESTAMPTZ,
    created_by BIGINT REFERENCES aihelms.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- MCP 工具表
CREATE TABLE IF NOT EXISTS aihelms.mcp_tools (
    id BIGSERIAL PRIMARY KEY,
    server_id BIGINT NOT NULL REFERENCES aihelms.mcp_servers(id) ON DELETE CASCADE,
    tool_name VARCHAR(200) NOT NULL,
    namespaced_name VARCHAR(300) NOT NULL,
    display_name VARCHAR(200) DEFAULT '',
    description TEXT DEFAULT '',
    input_schema JSONB DEFAULT '{}',
    billing_type VARCHAR(20),
    internal_cost_per_call NUMERIC(10,6),
    external_cost_per_call NUMERIC(10,6),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(server_id, tool_name)
);

-- 统一 AI 资源申请审批表
CREATE TABLE IF NOT EXISTS aihelms.resource_applications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES aihelms.users(id),
    resource_type VARCHAR(20) NOT NULL,
    resource_id BIGINT NOT NULL,
    reason TEXT DEFAULT '',
    request_config JSONB DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    celery_task_id VARCHAR(100) DEFAULT '',
    cancel_requested BOOLEAN DEFAULT FALSE,
    retry_of_task_id BIGINT,
    reviewed_by BIGINT REFERENCES aihelms.users(id),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT DEFAULT '',
    approval_config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- MCP 调用日志
CREATE TABLE IF NOT EXISTS aihelms.mcp_call_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    server_id BIGINT NOT NULL,
    tool_id BIGINT,
    tool_name VARCHAR(300) NOT NULL,
    namespaced_tool_name VARCHAR(400) NOT NULL,
    arguments JSONB DEFAULT '{}',
    request_args JSONB DEFAULT '{}',
    response_full TEXT DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'success',
    response_summary TEXT DEFAULT '',
    error_message TEXT,
    duration_ms INTEGER,
    internal_cost NUMERIC(10,6) DEFAULT 0,
    external_cost NUMERIC(10,6) DEFAULT 0,
    ai_key_id BIGINT,
    litellm_request_id VARCHAR(100),
    called_at TIMESTAMPTZ DEFAULT NOW()
);

-- LLM 调用日志（从 LiteLLM SpendLogs 定时同步）
CREATE TABLE IF NOT EXISTS aihelms.llm_call_logs (
    id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(500) UNIQUE NOT NULL,
    user_id BIGINT,
    ai_key_id BIGINT,
    deployment_id BIGINT,
    model VARCHAR(128) NOT NULL,
    provider VARCHAR(50),
    call_type VARCHAR(50),
    status VARCHAR(20),
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    cache_read_tokens INT DEFAULT 0,
    cache_creation_tokens INT DEFAULT 0,
    external_cost NUMERIC(12,6) DEFAULT 0,
    internal_cost NUMERIC(12,6) DEFAULT 0,
    duration_ms INT,
    ttft_ms INT,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    session_id VARCHAR(100),
    error_message TEXT,
    messages JSONB,
    response JSONB,
    metadata JSONB DEFAULT '{}',
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_logs_started_at ON aihelms.llm_call_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_logs_user ON aihelms.llm_call_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_logs_ai_key ON aihelms.llm_call_logs(ai_key_id);
CREATE INDEX IF NOT EXISTS idx_llm_logs_model ON aihelms.llm_call_logs(model);
CREATE INDEX IF NOT EXISTS idx_llm_logs_status ON aihelms.llm_call_logs(status);

-- LiteLLM creates public."LiteLLM_SpendLogs" via its own migrations.
-- The cursor index used by llm_log sync is managed by migration
-- 008_add_litellm_spendlogs_cursor_index.sql and by the sync task runtime guard.

-- Skill 使用日志（下载 / 安装）
CREATE TABLE IF NOT EXISTS aihelms.skill_usage_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    skill_id BIGINT NOT NULL,
    action VARCHAR(20) NOT NULL,
    ai_key_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skill_usage_created ON aihelms.skill_usage_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_usage_user ON aihelms.skill_usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_skill_usage_skill ON aihelms.skill_usage_logs(skill_id);

-- 通用同步状态表（存定时任务的增量游标）
CREATE TABLE IF NOT EXISTS aihelms.sync_state (
    key VARCHAR(64) PRIMARY KEY,
    last_sync_at TIMESTAMPTZ NOT NULL,
    last_request_id VARCHAR(500),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO aihelms.sync_state (key, last_sync_at) VALUES
    ('llm_logs', NOW() - INTERVAL '1 hour'),
    ('mcp_logs', NOW() - INTERVAL '1 hour')
ON CONFLICT DO NOTHING;

-- MCP 索引
CREATE INDEX IF NOT EXISTS idx_mcp_servers_category ON aihelms.mcp_servers(category);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_status ON aihelms.mcp_servers(status);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_is_published ON aihelms.mcp_servers(is_published);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_business_scenario ON aihelms.mcp_servers(business_scenario_id);
CREATE INDEX IF NOT EXISTS idx_mcp_tools_server ON aihelms.mcp_tools(server_id);
CREATE INDEX IF NOT EXISTS idx_mcp_tools_namespaced ON aihelms.mcp_tools(namespaced_name);
CREATE INDEX IF NOT EXISTS idx_mcp_call_logs_user ON aihelms.mcp_call_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_call_logs_server ON aihelms.mcp_call_logs(server_id);
CREATE INDEX IF NOT EXISTS idx_mcp_call_logs_called_at ON aihelms.mcp_call_logs(called_at);
CREATE INDEX IF NOT EXISTS idx_mcp_call_logs_tool_name ON aihelms.mcp_call_logs(namespaced_tool_name);

-- 资源申请索引
CREATE INDEX IF NOT EXISTS idx_resource_apps_user ON aihelms.resource_applications(user_id);
CREATE INDEX IF NOT EXISTS idx_resource_apps_type ON aihelms.resource_applications(resource_type);
CREATE INDEX IF NOT EXISTS idx_resource_apps_status ON aihelms.resource_applications(status);
CREATE INDEX IF NOT EXISTS idx_resource_apps_resource ON aihelms.resource_applications(resource_type, resource_id);

-- Skill 分类
CREATE TABLE IF NOT EXISTS aihelms.skill_categories (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO aihelms.skill_categories (name, sort_order) VALUES
    ('general', 0),
    ('legal', 10),
    ('dev', 20),
    ('office', 30)
ON CONFLICT (name) DO NOTHING;

-- Skill 主表
CREATE TABLE IF NOT EXISTS aihelms.skills (
    id BIGSERIAL PRIMARY KEY,
    skill_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    icon VARCHAR(20) DEFAULT '📦',
    icon_url VARCHAR(500),
    description TEXT DEFAULT '',
    category VARCHAR(50) DEFAULT 'general',
    business_scenario_id BIGINT REFERENCES aihelms.business_scenarios(id) ON DELETE SET NULL,
    version VARCHAR(20) DEFAULT '1.0.0',
    tags JSONB DEFAULT '[]',
    author VARCHAR(128) DEFAULT '',
    agent_install_prompt TEXT DEFAULT '',
    usage_instructions TEXT DEFAULT '',
    zip_path VARCHAR(500) DEFAULT '',
    zip_size BIGINT DEFAULT 0,
    zip_filename VARCHAR(200) DEFAULT '',
    is_active BOOLEAN DEFAULT true,
    is_published BOOLEAN DEFAULT false,
    requires_approval BOOLEAN DEFAULT false,
    install_count INTEGER DEFAULT 0,
    created_by BIGINT REFERENCES aihelms.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skills_category ON aihelms.skills(category);
CREATE INDEX IF NOT EXISTS idx_skills_published ON aihelms.skills(is_published);
CREATE INDEX IF NOT EXISTS idx_skills_business_scenario ON aihelms.skills(business_scenario_id);


-- AI Policies 审查基线
CREATE TABLE IF NOT EXISTS aihelms.ai_policies_audits (
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

CREATE INDEX IF NOT EXISTS idx_ai_policies_audits_audit_type ON aihelms.ai_policies_audits(audit_type);
CREATE INDEX IF NOT EXISTS idx_ai_policies_audits_skill_id ON aihelms.ai_policies_audits(skill_id);
CREATE INDEX IF NOT EXISTS idx_ai_policies_audits_status ON aihelms.ai_policies_audits(status);
CREATE INDEX IF NOT EXISTS idx_ai_policies_audits_decision ON aihelms.ai_policies_audits(decision);
CREATE INDEX IF NOT EXISTS idx_ai_policies_audits_finished_at ON aihelms.ai_policies_audits(finished_at DESC);

CREATE TABLE IF NOT EXISTS aihelms.ai_policies_risk_catalog (
    code VARCHAR(16) PRIMARY KEY,
    name_en VARCHAR(128) NOT NULL,
    name_zh VARCHAR(128) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    description_zh TEXT NOT NULL DEFAULT '',
    check_points JSONB NOT NULL DEFAULT '[]',
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS aihelms.ai_policies_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    llm_review_enabled BOOLEAN NOT NULL DEFAULT false,
    llm_review_model_id BIGINT REFERENCES aihelms.models(id) ON DELETE SET NULL,
    updated_by BIGINT REFERENCES aihelms.users(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ai_policies_settings_singleton CHECK (id = 1)
);

INSERT INTO aihelms.ai_policies_settings (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

ALTER TABLE aihelms.skills
    ADD COLUMN IF NOT EXISTS security_status VARCHAR(32) NOT NULL DEFAULT 'not_scanned',
    ADD COLUMN IF NOT EXISTS security_decision VARCHAR(32) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS security_severity VARCHAR(32) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS security_risk_score INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS latest_ai_policies_audit_id BIGINT REFERENCES aihelms.ai_policies_audits(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_skills_security_status ON aihelms.skills(security_status);
CREATE INDEX IF NOT EXISTS idx_skills_latest_ai_policies_audit_id ON aihelms.skills(latest_ai_policies_audit_id);

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
    ('AST10', 'Cross-Platform Risks', '跨平台传播风险', 'medium', '检查风险是否会跨 Agent、MCP、脚本或外部平台传播。', '["外部数据传输", "跨平台执行", "边界披露"]', 10)
ON CONFLICT (code) DO UPDATE SET
    name_en = EXCLUDED.name_en,
    name_zh = EXCLUDED.name_zh,
    severity = EXCLUDED.severity,
    description_zh = EXCLUDED.description_zh,
    check_points = EXCLUDED.check_points,
    sort_order = EXCLUDED.sort_order;


CREATE TABLE IF NOT EXISTS aihelms.schema_migrations (
    version VARCHAR(128) PRIMARY KEY,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO aihelms.schema_migrations (version)
VALUES ('010_create_ai_policies')
ON CONFLICT (version) DO NOTHING;

-- Agent 分类
CREATE TABLE IF NOT EXISTS aihelms.agent_categories (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent 平台
CREATE TABLE IF NOT EXISTS aihelms.agent_platforms (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL,
    label VARCHAR(64) DEFAULT '',
    description TEXT DEFAULT '',
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent 主表
CREATE TABLE IF NOT EXISTS aihelms.agents (
    id BIGSERIAL PRIMARY KEY,
    agent_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    icon VARCHAR(20) DEFAULT '🤖',
    icon_url VARCHAR(500),
    description TEXT DEFAULT '',
    platform VARCHAR(64) NOT NULL,
    category VARCHAR(50) DEFAULT 'general',
    business_scenario_id BIGINT REFERENCES aihelms.business_scenarios(id) ON DELETE SET NULL,
    department_id BIGINT REFERENCES aihelms.departments(id) ON DELETE SET NULL,
    project_id BIGINT REFERENCES aihelms.projects(id) ON DELETE SET NULL,
    cost_attribution VARCHAR(20) DEFAULT 'owner',
    ai_key_id BIGINT REFERENCES aihelms.ai_keys(id) ON DELETE SET NULL,
    chat_url VARCHAR(500) DEFAULT '',
    external_id VARCHAR(100) DEFAULT '',
    tags JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    is_published BOOLEAN DEFAULT false,
    requires_approval BOOLEAN DEFAULT false,
    status VARCHAR(20) DEFAULT 'online',
    user_count INTEGER DEFAULT 0,
    call_count INTEGER DEFAULT 0,
    created_by BIGINT REFERENCES aihelms.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agents_platform ON aihelms.agents(platform);
CREATE INDEX IF NOT EXISTS idx_agents_category ON aihelms.agents(category);
CREATE INDEX IF NOT EXISTS idx_agents_published ON aihelms.agents(is_published);
CREATE INDEX IF NOT EXISTS idx_agents_business_scenario ON aihelms.agents(business_scenario_id);
CREATE INDEX IF NOT EXISTS idx_agents_department ON aihelms.agents(department_id);

-- Agent 使用日志
CREATE TABLE IF NOT EXISTS aihelms.agent_usage_logs (
    id BIGSERIAL PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES aihelms.agents(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES aihelms.users(id),
    session_id VARCHAR(100) DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_usage_agent ON aihelms.agent_usage_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_usage_user ON aihelms.agent_usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_usage_created ON aihelms.agent_usage_logs(created_at);

-- 管理员操作审计日志
CREATE TABLE IF NOT EXISTS aihelms.admin_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,                -- 不加外键：登录失败 user_id=0；用户删除后历史日志要保留
    username VARCHAR(64) NOT NULL,
    identity_type VARCHAR(16) NOT NULL DEFAULT 'user',  -- 'user' | 'api_key'
    method VARCHAR(10) NOT NULL,            -- POST/PUT/DELETE/PATCH
    path VARCHAR(500) NOT NULL,
    action VARCHAR(200) NOT NULL,           -- summary 或 fallback "METHOD /path/{template}"
    status_code INT NOT NULL,
    ip VARCHAR(64) DEFAULT '',
    user_agent VARCHAR(500) DEFAULT '',
    duration_ms INT DEFAULT 0,
    request_summary TEXT DEFAULT '',        -- 脱敏后的 request body（完整存储，不截断）
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON aihelms.admin_audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON aihelms.admin_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON aihelms.admin_audit_logs(action);

-- 公共导出任务
CREATE TABLE IF NOT EXISTS aihelms.export_tasks (
    id BIGSERIAL PRIMARY KEY,
    task_name VARCHAR(200) NOT NULL,
    source VARCHAR(50) NOT NULL,
    export_type VARCHAR(80) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    celery_task_id VARCHAR(100) DEFAULT '',
    cancel_requested BOOLEAN DEFAULT FALSE,
    retry_of_task_id BIGINT,
    params JSONB DEFAULT '{}',
    file_name VARCHAR(255),
    file_path VARCHAR(500),
    file_size BIGINT,
    row_count INT DEFAULT 0,
    error_message TEXT DEFAULT '',
    created_by_id BIGINT NOT NULL,
    created_by_name VARCHAR(100) DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_export_tasks_created ON aihelms.export_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_export_tasks_source ON aihelms.export_tasks(source);
CREATE INDEX IF NOT EXISTS idx_export_tasks_status ON aihelms.export_tasks(status);
CREATE INDEX IF NOT EXISTS idx_export_tasks_created_by ON aihelms.export_tasks(created_by_id);
CREATE INDEX IF NOT EXISTS idx_export_tasks_retry_of ON aihelms.export_tasks(retry_of_task_id);


-- AI 效能：日聚合表
CREATE TABLE IF NOT EXISTS aihelms.cost_summary_daily (
    id BIGSERIAL PRIMARY KEY,
    summary_date DATE NOT NULL,
    user_id BIGINT,
    ai_key_id BIGINT,
    department_id BIGINT,
    project_id BIGINT,
    model VARCHAR(128),
    provider_id BIGINT,
    server_id BIGINT,
    cost_type VARCHAR(20) NOT NULL,
    key_type VARCHAR(20),
    total_requests INT DEFAULT 0,
    successful_requests INT DEFAULT 0,
    failed_requests INT DEFAULT 0,
    input_tokens BIGINT DEFAULT 0,
    output_tokens BIGINT DEFAULT 0,
    cache_tokens BIGINT DEFAULT 0,
    cache_read_tokens BIGINT DEFAULT 0,
    cache_creation_tokens BIGINT DEFAULT 0,
    external_cost NUMERIC(14,6) DEFAULT 0,
    internal_cost NUMERIC(14,6) DEFAULT 0,
    total_duration_ms BIGINT DEFAULT 0,
    last_aggregated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cost_summary_unique
    ON aihelms.cost_summary_daily(summary_date, COALESCE(user_id,0), COALESCE(ai_key_id,0), COALESCE(department_id,0), COALESCE(project_id,0), COALESCE(model,''), COALESCE(provider_id,0), COALESCE(server_id,0), cost_type, COALESCE(key_type,''));
CREATE INDEX IF NOT EXISTS idx_cost_summary_date ON aihelms.cost_summary_daily(summary_date);
CREATE INDEX IF NOT EXISTS idx_cost_summary_dept_date ON aihelms.cost_summary_daily(department_id, summary_date);
CREATE INDEX IF NOT EXISTS idx_cost_summary_user_date ON aihelms.cost_summary_daily(user_id, summary_date);
CREATE INDEX IF NOT EXISTS idx_cost_summary_model_date ON aihelms.cost_summary_daily(model, summary_date);

-- AI 效能：分析报告
CREATE TABLE IF NOT EXISTS aihelms.efficiency_reports (
    id BIGSERIAL PRIMARY KEY,
    report_type VARCHAR(20) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    filters JSONB DEFAULT '{}',
    model_used VARCHAR(128),
    summary TEXT DEFAULT '',
    content_md TEXT DEFAULT '',
    suggestions JSONB DEFAULT '[]',
    created_by BIGINT REFERENCES aihelms.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    generation_cost NUMERIC(10,4) DEFAULT 0,
    generation_duration_ms INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_reports_type_period ON aihelms.efficiency_reports(report_type, period_start DESC);

-- AI 效能：决策建议跟踪
CREATE TABLE IF NOT EXISTS aihelms.efficiency_suggestions (
    id BIGSERIAL PRIMARY KEY,
    report_id BIGINT REFERENCES aihelms.efficiency_reports(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    priority VARCHAR(20) NOT NULL,
    expected_impact VARCHAR(500) DEFAULT '',
    status VARCHAR(20) DEFAULT 'pending',
    celery_task_id VARCHAR(100) DEFAULT '',
    cancel_requested BOOLEAN DEFAULT FALSE,
    retry_of_task_id BIGINT REFERENCES aihelms.efficiency_suggestions(id),
    status_note TEXT DEFAULT '',
    status_updated_by BIGINT REFERENCES aihelms.users(id),
    status_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_suggestions_report ON aihelms.efficiency_suggestions(report_id);

-- 索引
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON aihelms.usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON aihelms.usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_departments_parent_id ON aihelms.departments(parent_id);
CREATE INDEX IF NOT EXISTS idx_user_departments_user_id ON aihelms.user_departments(user_id);
CREATE INDEX IF NOT EXISTS idx_user_departments_dept_id ON aihelms.user_departments(department_id);
CREATE INDEX IF NOT EXISTS idx_user_projects_user_id ON aihelms.user_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_user_projects_project_id ON aihelms.user_projects(project_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON aihelms.user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON aihelms.user_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON aihelms.role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_ai_keys_owner ON aihelms.ai_keys(owner_type, owner_id);
CREATE INDEX IF NOT EXISTS idx_ai_keys_type ON aihelms.ai_keys(key_type);
CREATE INDEX IF NOT EXISTS idx_ai_keys_created_by ON aihelms.ai_keys(created_by);
CREATE INDEX IF NOT EXISTS idx_providers_type ON aihelms.providers(provider_type);
CREATE INDEX IF NOT EXISTS idx_credentials_provider ON aihelms.credentials(provider_id);
CREATE INDEX IF NOT EXISTS idx_credentials_name ON aihelms.credentials(credential_name);
CREATE INDEX IF NOT EXISTS idx_models_model_id ON aihelms.models(model_id);
CREATE INDEX IF NOT EXISTS idx_models_category ON aihelms.models(category);
CREATE INDEX IF NOT EXISTS idx_models_business_scenario ON aihelms.models(business_scenario_id);
CREATE INDEX IF NOT EXISTS idx_deployments_model ON aihelms.model_deployments(model_id);
CREATE INDEX IF NOT EXISTS idx_ai_key_model_limits_key ON aihelms.ai_key_model_limits(ai_key_id);
CREATE INDEX IF NOT EXISTS idx_ai_key_model_limits_model ON aihelms.ai_key_model_limits(model_id);
CREATE INDEX IF NOT EXISTS idx_deployments_credential ON aihelms.model_deployments(credential_id);
CREATE INDEX IF NOT EXISTS idx_model_dept_visibility_model ON aihelms.model_department_visibility(model_id);
CREATE INDEX IF NOT EXISTS idx_model_dept_visibility_dept ON aihelms.model_department_visibility(department_id);
CREATE INDEX IF NOT EXISTS idx_model_user_visibility_model ON aihelms.model_user_visibility(model_id);
CREATE INDEX IF NOT EXISTS idx_model_user_visibility_user ON aihelms.model_user_visibility(user_id);

-- 初始角色
INSERT INTO aihelms.roles (name, display_name, description, is_system) VALUES
    ('super_admin', '超级管理员', '拥有所有权限', true),
    ('admin', '管理员', '管理平台日常运营', true),
    ('department_manager', '部门管理员', '管理所属部门', true),
    ('user', '普通用户', '基础使用权限', true)
ON CONFLICT (name) DO NOTHING;

-- 权限点
INSERT INTO aihelms.permissions (code, name, resource, action, description) VALUES
    ('user:create', '创建用户', 'user', 'create', '创建新用户'),
    ('user:read', '查看用户', 'user', 'read', '查看用户列表和详情'),
    ('user:update', '编辑用户', 'user', 'update', '编辑用户信息'),
    ('user:delete', '删除用户', 'user', 'delete', '删除用户'),
    ('department:create', '创建部门', 'department', 'create', '创建部门'),
    ('department:read', '查看部门', 'department', 'read', '查看部门架构'),
    ('department:update', '编辑部门', 'department', 'update', '编辑部门信息'),
    ('department:delete', '删除部门', 'department', 'delete', '删除部门'),
    ('project:create', '创建项目', 'project', 'create', '创建项目'),
    ('project:read', '查看项目', 'project', 'read', '查看项目列表'),
    ('project:update', '编辑项目', 'project', 'update', '编辑项目信息'),
    ('project:delete', '删除项目', 'project', 'delete', '删除项目'),
    ('role:create', '创建角色', 'role', 'create', '创建新角色'),
    ('role:read', '查看角色', 'role', 'read', '查看角色列表'),
    ('role:update', '编辑角色', 'role', 'update', '编辑角色和权限分配'),
    ('role:delete', '删除角色', 'role', 'delete', '删除角色'),
    ('permission:read', '查看权限', 'permission', 'read', '查看权限列表'),
    ('mcp:create', '创建MCP', 'mcp', 'create', '创建 MCP Server'),
    ('mcp:read', '查看MCP', 'mcp', 'read', '查看 MCP Server 列表和详情'),
    ('mcp:update', '编辑MCP', 'mcp', 'update', '编辑 MCP Server 和审批申请'),
    ('mcp:delete', '删除MCP', 'mcp', 'delete', '删除 MCP Server 和撤销授权'),
    ('resource_application:read', '查看资源申请', 'resource_application', 'read', '查看 AI 资源申请列表'),
    ('resource_application:approve', '审批资源申请', 'resource_application', 'approve', '审批 AI 资源申请'),
    ('skill:create', '创建Skill', 'skill', 'create', '创建 Skill'),
    ('skill:read', '查看Skill', 'skill', 'read', '查看 Skill 列表和详情'),
    ('skill:update', '编辑Skill', 'skill', 'update', '编辑 Skill'),
    ('skill:delete', '删除Skill', 'skill', 'delete', '删除 Skill'),
    ('agent:create', '创建智能体', 'agent', 'create', '创建智能体'),
    ('agent:read', '查看智能体', 'agent', 'read', '查看智能体列表和详情'),
    ('agent:update', '编辑智能体', 'agent', 'update', '编辑智能体'),
    ('agent:delete', '删除智能体', 'agent', 'delete', '删除智能体'),
    ('audit_log:read', '查看管理员日志', 'audit_log', 'read', '查看管理员操作审计日志'),
    ('api_key:create', '创建 API Key', 'api_key', 'create', '创建平台 API Key'),
    ('api_key:read', '查看 API Key', 'api_key', 'read', '查看 API Key 列表和详情'),
    ('api_key:update', '编辑 API Key', 'api_key', 'update', '启用/禁用、修改 API Key'),
    ('api_key:delete', '删除 API Key', 'api_key', 'delete', '撤销 API Key'),
    ('usage_log:read', '查看使用日志', 'usage_log', 'read', '查看 LLM/MCP/Skill/智能体调用日志'),
    ('efficiency:read', '查看AI效能', 'efficiency', 'read', '查看AI效能分析数据和报告'),
    ('efficiency:write', '管理AI效能', 'efficiency', 'write', '生成报告、更新建议状态')
ON CONFLICT (code) DO NOTHING;

-- super_admin 拥有所有权限
INSERT INTO aihelms.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM aihelms.roles r, aihelms.permissions p
WHERE r.name = 'super_admin'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- admin 拥有除角色管理外的权限
INSERT INTO aihelms.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM aihelms.roles r, aihelms.permissions p
WHERE r.name = 'admin' AND p.code NOT IN ('role:create', 'role:update', 'role:delete')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- department_manager 拥有查看权限 + 部门/项目查看
INSERT INTO aihelms.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM aihelms.roles r, aihelms.permissions p
WHERE r.name = 'department_manager' AND p.code IN ('user:read', 'department:read', 'project:read', 'role:read', 'permission:read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- user 只有基础查看权限
INSERT INTO aihelms.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM aihelms.roles r, aihelms.permissions p
WHERE r.name = 'user' AND p.code IN ('permission:read')
ON CONFLICT (role_id, permission_id) DO NOTHING;


-- AI Policies 权限点仅注册，不写入 role_permissions；管理员由 is_admin 统一放行。
INSERT INTO aihelms.permissions (code, name, resource, action, description)
VALUES
    ('ai_policies:read', '查看 AI Policies', 'ai_policies', 'read', '查看 AI Policies 审查任务和报告'),
    ('ai_policies:scan', '发起 AI Policies 审查', 'ai_policies', 'scan', '发起 Skill 安全审查'),
    ('ai_policies:config', '配置 AI Policies', 'ai_policies', 'config', '配置 LLM 审查引擎')
ON CONFLICT (code) DO NOTHING;

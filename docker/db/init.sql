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
    litellm_user_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- API Key 表
CREATE TABLE IF NOT EXISTS aihelms.api_keys (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES aihelms.users(id),
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

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
    budget_limit NUMERIC(12,4),
    budget_type VARCHAR(10) DEFAULT 'money',   -- 'money' | 'count'
    budget_hard_limit BOOLEAN DEFAULT true,
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

-- 凭证（对齐 LiteLLM CredentialsTable）
CREATE TABLE IF NOT EXISTS aihelms.credentials (
    id BIGSERIAL PRIMARY KEY,
    credential_name VARCHAR(128) NOT NULL UNIQUE,  -- 凭证名（同步到 LiteLLM）
    provider_id BIGINT REFERENCES aihelms.providers(id) ON DELETE SET NULL,
    credential_values JSONB NOT NULL DEFAULT '{}', -- 加密存储的认证信息（api_key, api_base 等）
    credential_info JSONB DEFAULT '{}',            -- 描述/元信息
    litellm_synced BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 平台统一模型（展示层）
CREATE TABLE IF NOT EXISTS aihelms.models (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    model_id VARCHAR(128) NOT NULL UNIQUE,    -- 用户请求时用的名称 = LiteLLM model_name
    category VARCHAR(50) DEFAULT 'chat',
    capabilities JSONB DEFAULT '[]',
    description TEXT DEFAULT '',
    is_active BOOLEAN DEFAULT true,
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

-- 索引
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON aihelms.usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON aihelms.usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON aihelms.api_keys(user_id);
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
CREATE INDEX IF NOT EXISTS idx_deployments_model ON aihelms.model_deployments(model_id);
CREATE INDEX IF NOT EXISTS idx_ai_key_model_limits_key ON aihelms.ai_key_model_limits(ai_key_id);
CREATE INDEX IF NOT EXISTS idx_ai_key_model_limits_model ON aihelms.ai_key_model_limits(model_id);
CREATE INDEX IF NOT EXISTS idx_deployments_credential ON aihelms.model_deployments(credential_id);

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
    ('permission:read', '查看权限', 'permission', 'read', '查看权限列表')
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

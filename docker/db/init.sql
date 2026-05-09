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
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
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

-- 组织表（department=树形部门/分支机构, group=扁平项目组）
CREATE TABLE IF NOT EXISTS aihelms.organizations (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    type VARCHAR(16) NOT NULL CHECK (type IN ('department', 'group')),
    parent_id BIGINT REFERENCES aihelms.organizations(id),
    description TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_group_no_parent CHECK (type != 'group' OR parent_id IS NULL)
);

-- 用户-组织 多对多（归属关系）
CREATE TABLE IF NOT EXISTS aihelms.user_organizations (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES aihelms.users(id),
    organization_id BIGINT NOT NULL REFERENCES aihelms.organizations(id),
    is_manager BOOLEAN DEFAULT false,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, organization_id)
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

-- 索引
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON aihelms.usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON aihelms.usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON aihelms.api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_organizations_parent_id ON aihelms.organizations(parent_id);
CREATE INDEX IF NOT EXISTS idx_organizations_type ON aihelms.organizations(type);
CREATE INDEX IF NOT EXISTS idx_user_organizations_user_id ON aihelms.user_organizations(user_id);
CREATE INDEX IF NOT EXISTS idx_user_organizations_org_id ON aihelms.user_organizations(organization_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON aihelms.user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON aihelms.user_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON aihelms.role_permissions(role_id);

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
    ('organization:create', '创建组织', 'organization', 'create', '创建部门或项目组'),
    ('organization:read', '查看组织', 'organization', 'read', '查看组织架构'),
    ('organization:update', '编辑组织', 'organization', 'update', '编辑组织信息'),
    ('organization:delete', '删除组织', 'organization', 'delete', '删除组织'),
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

-- department_manager 拥有查看权限 + 组织查看
INSERT INTO aihelms.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM aihelms.roles r, aihelms.permissions p
WHERE r.name = 'department_manager' AND p.code IN ('user:read', 'organization:read', 'role:read', 'permission:read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- user 只有基础查看权限
INSERT INTO aihelms.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM aihelms.roles r, aihelms.permissions p
WHERE r.name = 'user' AND p.code IN ('permission:read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

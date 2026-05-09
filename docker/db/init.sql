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

-- 索引
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON aihelms.usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON aihelms.usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON aihelms.api_keys(user_id);

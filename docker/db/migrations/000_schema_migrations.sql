-- 迁移记录表（跟踪已执行的迁移）
CREATE TABLE IF NOT EXISTS aihelms.schema_migrations (
    version VARCHAR(128) PRIMARY KEY,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

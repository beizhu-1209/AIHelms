ALTER TABLE aihelms.cost_summary_daily
    ADD COLUMN IF NOT EXISTS cache_read_tokens BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cache_creation_tokens BIGINT DEFAULT 0;

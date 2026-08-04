-- Add composite keyset cursor column for LLM log sync.
-- Time-only cursor deadlocks when a batch is truncated by LIMIT: the new cursor
-- equals the old one and the sync loop rescans the same rows forever.
ALTER TABLE aihelms.sync_state
    ADD COLUMN IF NOT EXISTS last_request_id VARCHAR(500);

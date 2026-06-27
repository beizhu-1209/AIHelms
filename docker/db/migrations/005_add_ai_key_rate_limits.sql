-- AI identity rate limit fields.
ALTER TABLE aihelms.ai_keys ADD COLUMN IF NOT EXISTS rate_limit_mode VARCHAR(20);
UPDATE aihelms.ai_keys SET rate_limit_mode = 'none' WHERE rate_limit_mode IS NULL;
ALTER TABLE aihelms.ai_keys ALTER COLUMN rate_limit_mode SET DEFAULT 'none';
ALTER TABLE aihelms.ai_keys ADD COLUMN IF NOT EXISTS tpm_limit INT;
ALTER TABLE aihelms.ai_keys ADD COLUMN IF NOT EXISTS rpm_limit INT;
ALTER TABLE aihelms.ai_keys ADD COLUMN IF NOT EXISTS max_parallel_requests INT;
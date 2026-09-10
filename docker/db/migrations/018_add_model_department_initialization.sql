-- Existing accounts must not gain new initialization grants after a job transfer.
ALTER TABLE aihelms.users ADD COLUMN IF NOT EXISTS model_departments_initialized BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE aihelms.users ALTER COLUMN model_departments_initialized SET DEFAULT false;

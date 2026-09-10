ALTER TABLE aihelms.resource_applications
    ADD COLUMN IF NOT EXISTS invalidated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS invalidation_reason TEXT DEFAULT '';

ALTER TABLE aihelms.resource_applications
    ADD COLUMN IF NOT EXISTS celery_task_id VARCHAR(100) DEFAULT '',
    ADD COLUMN IF NOT EXISTS cancel_requested BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS retry_of_task_id BIGINT;

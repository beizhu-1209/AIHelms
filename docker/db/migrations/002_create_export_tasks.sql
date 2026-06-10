CREATE TABLE IF NOT EXISTS aihelms.export_tasks (
    id BIGSERIAL PRIMARY KEY,
    task_name VARCHAR(200) NOT NULL,
    source VARCHAR(50) NOT NULL,
    export_type VARCHAR(80) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    celery_task_id VARCHAR(100) DEFAULT '',
    cancel_requested BOOLEAN DEFAULT FALSE,
    retry_of_task_id BIGINT,
    params JSONB DEFAULT '{}',
    file_name VARCHAR(255),
    file_path VARCHAR(500),
    file_size BIGINT,
    row_count INT DEFAULT 0,
    error_message TEXT DEFAULT '',
    created_by_id BIGINT NOT NULL,
    created_by_name VARCHAR(100) DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_export_tasks_created ON aihelms.export_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_export_tasks_source ON aihelms.export_tasks(source);
CREATE INDEX IF NOT EXISTS idx_export_tasks_status ON aihelms.export_tasks(status);
CREATE INDEX IF NOT EXISTS idx_export_tasks_created_by ON aihelms.export_tasks(created_by_id);
CREATE INDEX IF NOT EXISTS idx_export_tasks_retry_of ON aihelms.export_tasks(retry_of_task_id);

-- Add an optional cursor index for LiteLLM SpendLogs.
-- LiteLLM owns this public table and may create it after AIHelms migrations run,
-- so this migration must be a no-op when the table is not present. The sync task
-- also creates the same index with CREATE INDEX IF NOT EXISTS as a runtime guard.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'LiteLLM_SpendLogs'
    ) THEN
        CREATE INDEX IF NOT EXISTS "LiteLLM_SpendLogs_cursorTime_request_id_idx"
        ON public."LiteLLM_SpendLogs" (COALESCE("endTime", "startTime"), request_id);
    END IF;
END $$;

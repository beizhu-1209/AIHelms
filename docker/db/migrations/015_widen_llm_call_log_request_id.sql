-- Widen request_id to accommodate LiteLLM Responses API base64-encoded IDs
ALTER TABLE aihelms.llm_call_logs
    ALTER COLUMN request_id TYPE VARCHAR(500);

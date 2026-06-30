-- Add editable author fields for MCP/Skill marketplace resources.
-- Add MCP call_count and backfill it from existing call logs.

ALTER TABLE aihelms.mcp_servers
    ADD COLUMN IF NOT EXISTS author VARCHAR(128) DEFAULT '';

ALTER TABLE aihelms.mcp_servers
    ADD COLUMN IF NOT EXISTS call_count INTEGER DEFAULT 0;

ALTER TABLE aihelms.skills
    ADD COLUMN IF NOT EXISTS author VARCHAR(128) DEFAULT '';

UPDATE aihelms.mcp_servers s
SET call_count = COALESCE(c.cnt, 0)
FROM (
    SELECT server_id, COUNT(*)::integer AS cnt
    FROM aihelms.mcp_call_logs
    GROUP BY server_id
) c
WHERE c.server_id = s.id;

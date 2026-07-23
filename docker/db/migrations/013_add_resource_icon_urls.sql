ALTER TABLE aihelms.skills
    ADD COLUMN IF NOT EXISTS icon_url VARCHAR(500);

ALTER TABLE aihelms.agents
    ADD COLUMN IF NOT EXISTS icon_url VARCHAR(500);

ALTER TABLE aihelms.business_scenarios
    ADD COLUMN IF NOT EXISTS icon_url VARCHAR(500);

UPDATE aihelms.mcp_servers
SET icon_url = ''
WHERE icon_url IS NOT NULL
  AND icon_url <> ''
  AND icon_url NOT LIKE '/icons/%';

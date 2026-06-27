-- 006_add_xiaomi_mimo_prefix_map.sql
-- Add Xiaomi MiMo LiteLLM prefix mappings.
INSERT INTO aihelms.provider_prefix_map
(provider_type, format, category, prefix, needs_v1)
VALUES
  ('xiaomi_mimo', 'openai',    'chat', 'xiaomi_mimo', false),
  ('xiaomi_mimo', 'anthropic', 'chat', 'anthropic',   false)
ON CONFLICT DO NOTHING;

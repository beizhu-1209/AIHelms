-- Add Tencent Hunyuan and xAI LiteLLM prefix mappings.
-- Tencent TokenHub 端点需要显式 /v1，needs_v1=true 让平台同步时补全 api_base。
INSERT INTO aihelms.provider_prefix_map
(provider_type, format, category, prefix, needs_v1)
VALUES
  ('tencent', 'openai', 'chat', 'tencent', true),
  ('xai', 'openai', 'chat', 'xai', false)
ON CONFLICT (provider_type, format, category)
DO UPDATE SET prefix = EXCLUDED.prefix, needs_v1 = EXCLUDED.needs_v1;

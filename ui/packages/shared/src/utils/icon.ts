const PROVIDER_ICON_FILES: Record<string, string> = {
  openai: 'openai.svg',
  anthropic: 'anthropic.svg',
  azure: 'azure.svg',
  google: 'google.svg',
  deepseek: 'deepseek.svg',
  bedrock: 'bedrock.svg',
  vertex_ai: 'vertex_ai.svg',
  volcengine: 'volcengine.png',
  dashscope: 'dashscope.png',
  zhipu: 'zhipu.svg',
  moonshot: 'moonshot.svg',
  minimax: 'minimax.svg',
  xiaomi_mimo: 'xiaomi_mimo.png',
  vllm: 'vllm.png',
  sglang: 'sglang.png',
  ollama: 'ollama.svg',
  lmstudio: 'lmstudio.svg',
  xai: 'xai.svg',
  tencent: 'tencent.png',
  openai_compatible: 'openai_compatible.svg',
  custom: 'custom.svg',
  other: 'custom.svg',
}

export function getProviderIconUrl(providerType: string): string {
  const filename = PROVIDER_ICON_FILES[providerType] || PROVIDER_ICON_FILES.custom
  return `/icons/v1/providers/${filename}`
}

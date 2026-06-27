<script setup lang="ts">
import type { AiKey } from '@aihelms/shared'

interface Props {
  keyData: AiKey | null
}

function formatRateLimit(key: AiKey | null): string {
  if (!key || key.rate_limit_mode === 'none') return '限流：未设置'
  if (key.rate_limit_mode === 'per_model') return '限流：分模型'

  const parts: string[] = []
  if (key.max_parallel_requests) parts.push(`并发 ${key.max_parallel_requests}`)
  if (key.rpm_limit) parts.push(`RPM ${key.rpm_limit}`)
  if (key.tpm_limit) parts.push(`TPM ${key.tpm_limit}`)
  return parts.length ? `限流：${parts.join(' / ')}` : '限流：总限流'
}

const props = defineProps<Props>()
</script>

<template>
  <div class="mt-1 text-xs text-slate-500">{{ formatRateLimit(props.keyData) }}</div>
</template>

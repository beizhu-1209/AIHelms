<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { resyncAnthropicDeployments, testModelAccessStream, toast, usePermission } from '@aihelms/shared'
import type { AccessTestErrorDetail } from '@aihelms/shared'

interface Props {
  visible: boolean
  defaultModel?: string
  defaultCredentialName?: string
  availableModels?: string[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
}>()
const { hasPermission } = usePermission()

const modelInput = ref('')
const messageInput = ref('你好，请简单介绍一下你自己。')
const maxTokens = ref(100)
const streamEnabled = ref(true)
const outputContent = ref('')
const isStreaming = ref(false)
const errorMsg = ref('')
const errorDetail = ref<AccessTestErrorDetail | null>(null)
const showTechnicalDetail = ref(false)
const isResyncingAnthropic = ref(false)

watch(() => props.visible, (val) => {
  if (val) {
    modelInput.value = props.defaultModel || ''
    outputContent.value = ''
    errorMsg.value = ''
    errorDetail.value = null
    showTechnicalDetail.value = false
    isStreaming.value = false
    isResyncingAnthropic.value = false
  }
})

const canSend = computed(() => {
  return modelInput.value.trim() && messageInput.value.trim() && !isStreaming.value
})

const canResyncAnthropicAccess = computed(() => {
  return errorDetail.value?.category === 'upstream_permission_denied' && hasPermission('user:update')
})

async function handleSend(): Promise<void> {
  if (!canSend.value) return

  outputContent.value = ''
  errorMsg.value = ''
  errorDetail.value = null
  showTechnicalDetail.value = false
  isStreaming.value = true

  try {
    const response = await testModelAccessStream({
      model: modelInput.value.trim(),
      messages: [{ role: 'user', content: messageInput.value.trim() }],
      stream: streamEnabled.value,
      max_tokens: maxTokens.value,
    })

    if (!response.ok) {
      const text = await response.text()
      errorMsg.value = `请求失败: ${response.status} - ${text}`
      isStreaming.value = false
      return
    }

    // 非流式响应（embedding/rerank 返回 JSON）
    const contentType = response.headers.get('content-type') || ''
    if (!contentType.includes('text/event-stream')) {
      const json = await response.json()
      if (json.data?.success === false) {
        setAccessError(json.data.error_detail, json.data.error || '测试失败')
      } else if (json.data?.dimensions !== undefined) {
        outputContent.value = `测试成功\n维度: ${json.data.dimensions}\n模型: ${json.data.model}\nTokens: ${json.data.usage?.prompt_tokens || 0}`
      } else if (json.data?.results) {
        const lines = json.data.results.map((r: { index: number; relevance_score: number }) =>
          `[${r.index}] 相关度: ${r.relevance_score.toFixed(4)}`)
        outputContent.value = `测试成功\n模型: ${json.data.model}\n排序结果:\n${lines.join('\n')}`
      } else {
        outputContent.value = json.data?.content || JSON.stringify(json.data)
      }
      isStreaming.value = false
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      errorMsg.value = '无法读取响应流'
      isStreaming.value = false
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6)
        if (data === '[DONE]') {
          isStreaming.value = false
          return
        }
        if (data.startsWith('[ERROR]')) {
          setAccessErrorFromStream(data.slice(8).trim())
          isStreaming.value = false
          return
        }
        outputContent.value += data
      }
    }
  } catch (e) {
    errorMsg.value = `连接错误: ${e instanceof Error ? e.message : String(e)}`
  } finally {
    isStreaming.value = false
  }
}

function handleClose(): void {
  emit('close')
}

async function handleResyncAnthropicAccess(): Promise<void> {
  if (isResyncingAnthropic.value) return
  isResyncingAnthropic.value = true
  try {
    const result = await resyncAnthropicDeployments()
    toast.success(`同步完成，请重新测试（更新 Key：${result.keys_updated}）`)
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '同步失败')
  } finally {
    isResyncingAnthropic.value = false
  }
}

function setAccessError(detail: AccessTestErrorDetail | undefined, fallback: string): void {
  if (detail) {
    errorDetail.value = detail
    errorMsg.value = detail.title || fallback
    return
  }
  errorMsg.value = fallback
}

function setAccessErrorFromStream(payload: string): void {
  try {
    const parsed = JSON.parse(payload) as AccessTestErrorDetail
    setAccessError(parsed, parsed.title || '测试失败')
  } catch {
    errorMsg.value = payload || '测试失败'
  }
}
</script>

<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
    <div class="flex w-full max-w-2xl flex-col rounded-2xl border border-slate-200/60 bg-white/95 shadow-xl backdrop-blur-xl" style="max-height: 80vh;">
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4">
        <h3 class="text-lg font-semibold text-slate-900">访问测试</h3>
        <button
          class="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
          @click="handleClose"
        >
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto px-6 py-4">
        <!-- Model select -->
        <div class="mb-4">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">模型</label>
          <div class="flex gap-2">
            <input
              v-model="modelInput"
              type="text"
              placeholder="输入模型 ID（如 claude-opus-4-6）"
              class="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition-colors focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
            />
            <select
              v-if="availableModels && availableModels.length > 0"
              v-model="modelInput"
              class="w-48 shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition-colors focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
            >
              <option value="" disabled>选择可用模型</option>
              <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>
        </div>

        <!-- Message input -->
        <div class="mb-4">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">测试消息</label>
          <textarea
            v-model="messageInput"
            rows="3"
            placeholder="输入测试消息..."
            class="w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition-colors focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <!-- Parameters -->
        <div class="mb-4 flex items-center gap-4">
          <div class="flex items-center gap-2">
            <label class="text-xs text-slate-500">Max Tokens</label>
            <input
              v-model.number="maxTokens"
              type="number"
              min="1"
              max="4096"
              class="w-20 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900 outline-none focus:border-blue-400"
            />
          </div>
          <label class="flex items-center gap-1.5 text-xs text-slate-500">
            <input
              v-model="streamEnabled"
              type="checkbox"
              class="h-3.5 w-3.5 rounded border-slate-300 text-blue-500 focus:ring-blue-400/20"
            />
            流式响应
          </label>
        </div>

        <!-- Send button -->
        <div class="mb-4">
          <button
            :disabled="!canSend"
            class="rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
            @click="handleSend"
          >
            <span v-if="isStreaming" class="flex items-center gap-2">
              <svg class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              测试中...
            </span>
            <span v-else>发送测试</span>
          </button>
        </div>

        <!-- Output area -->
        <div v-if="outputContent || errorMsg" class="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <label class="mb-2 block text-xs font-medium text-slate-500">测试结果</label>
          <div v-if="errorMsg" class="space-y-2">
            <div class="text-sm font-medium text-red-600">{{ errorDetail?.title || errorMsg }}</div>
            <div v-if="errorDetail?.message" class="text-sm leading-6 text-slate-600">{{ errorDetail.message }}</div>
            <div
              v-if="canResyncAnthropicAccess"
              class="rounded-lg border border-amber-200 bg-amber-50 p-3"
            >
              <p class="mb-2 text-xs leading-5 text-amber-700">
                若已确认上游供应商已开通该模型仍测试失败，可能是平台与 LiteLLM 的授权未同步，点击重新同步后重试。
              </p>
              <button
                type="button"
                :disabled="isResyncingAnthropic"
                class="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-60"
                @click="handleResyncAnthropicAccess"
              >
                {{ isResyncingAnthropic ? '同步中...' : '重新同步模型授权' }}
              </button>
            </div>
            <button
              v-if="errorDetail?.technical_detail"
              type="button"
              class="text-xs font-medium text-slate-500 hover:text-slate-700"
              @click="showTechnicalDetail = !showTechnicalDetail"
            >
              {{ showTechnicalDetail ? '收起技术详情' : '查看技术详情' }}
            </button>
            <pre
              v-if="showTechnicalDetail && errorDetail?.technical_detail"
              class="max-h-32 overflow-auto whitespace-pre-wrap rounded-lg bg-white p-3 text-xs text-slate-500"
            >{{ errorDetail.technical_detail }}</pre>
          </div>
          <div v-else class="whitespace-pre-wrap text-sm text-slate-800">{{ outputContent }}<span v-if="isStreaming" class="inline-block h-4 w-1.5 animate-pulse bg-slate-400" /></div>
        </div>
      </div>
    </div>
  </div>
</template>

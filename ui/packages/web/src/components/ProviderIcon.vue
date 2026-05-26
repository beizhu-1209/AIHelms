<script setup lang="ts">
import { computed } from 'vue'

import openaiIcon from '../assets/providers/openai.svg'
import anthropicIcon from '../assets/providers/anthropic.svg'
import azureIcon from '../assets/providers/azure.svg'
import googleIcon from '../assets/providers/google.svg'
import deepseekIcon from '../assets/providers/deepseek.svg'
import bedrockIcon from '../assets/providers/bedrock.svg'
import vertexIcon from '../assets/providers/vertex_ai.svg'
import volcengineIcon from '../assets/providers/volcengine.png'
import dashscopeIcon from '../assets/providers/dashscope.png'
import zhipuIcon from '../assets/providers/zhipu.svg'
import moonshotIcon from '../assets/providers/moonshot.svg'
import minimaxIcon from '../assets/providers/minimax.svg'
import ollamaIcon from '../assets/providers/ollama.svg'
import customIcon from '../assets/providers/custom.svg'

interface Props {
  type: string
  size?: number
}

const props = withDefaults(defineProps<Props>(), { size: 24 })

const iconMap: Record<string, string> = {
  openai: openaiIcon,
  anthropic: anthropicIcon,
  azure: azureIcon,
  google: googleIcon,
  deepseek: deepseekIcon,
  bedrock: bedrockIcon,
  vertex_ai: vertexIcon,
  volcengine: volcengineIcon,
  dashscope: dashscopeIcon,
  zhipu: zhipuIcon,
  moonshot: moonshotIcon,
  minimax: minimaxIcon,
  ollama: ollamaIcon,
  custom: customIcon,
}

const iconSrc = computed(() => iconMap[props.type] || iconMap.custom)
const sizeStyle = computed(() => `${props.size}px`)
</script>

<template>
  <img
    :src="iconSrc"
    :alt="type"
    class="shrink-0 rounded"
    :style="{ width: sizeStyle, height: sizeStyle }"
  />
</template>

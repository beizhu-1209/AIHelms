<script setup lang="ts">
import { ref, watch } from 'vue'

interface Props {
  src?: string | null
  size?: number
  alt?: string
}

const props = withDefaults(defineProps<Props>(), {
  src: '',
  size: 24,
  alt: '',
})

const DEFAULT_ICON_URL = '/icons/v1/default.svg'
const displaySrc = ref(props.src || DEFAULT_ICON_URL)
const didFallback = ref(false)

watch(
  () => props.src,
  value => {
    displaySrc.value = value || DEFAULT_ICON_URL
    didFallback.value = false
  },
)

function handleError() {
  if (didFallback.value) return
  didFallback.value = true
  displaySrc.value = DEFAULT_ICON_URL
}
</script>

<template>
  <img
    :src="displaySrc"
    :alt="alt"
    :width="size"
    :height="size"
    class="shrink-0 rounded object-contain"
    @error="handleError"
  />
</template>

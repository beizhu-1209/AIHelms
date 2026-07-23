<script setup lang="ts">
import { computed } from 'vue'
import HostedIcon from '@aihelms/shared/src/components/HostedIcon.vue'
import { getProviderIconUrl } from '@aihelms/shared'

interface Props {
  type?: string
  src?: string
  size?: number
}

const props = withDefaults(defineProps<Props>(), { type: '', src: '', size: 24 })

const iconSrc = computed(() => {
  if (props.src) return props.src
  return getProviderIconUrl(props.type)
})
</script>

<template>
  <HostedIcon
    :src="iconSrc"
    :alt="type"
    :size="size"
  />
</template>

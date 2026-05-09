<script setup lang="ts">
import type { OrgTreeNode } from '@aihelms/shared'

interface Props {
  nodes: OrgTreeNode[]
  level?: number
}

defineProps<Props>()
const emit = defineEmits<{
  select: [node: OrgTreeNode]
}>()

function handleSelect(node: OrgTreeNode): void {
  emit('select', node)
}
</script>

<template>
  <ul :class="level ? 'ml-4' : ''">
    <li v-for="node in nodes" :key="node.id" class="my-1">
      <div
        class="flex cursor-pointer items-center rounded-md px-2 py-1 text-sm hover:bg-gray-100"
        @click="handleSelect(node)"
      >
        <span v-if="node.children.length" class="mr-1 text-gray-400">▸</span>
        <span v-else class="mr-1 text-gray-300">·</span>
        <span class="text-gray-800">{{ node.name }}</span>
        <span v-if="!node.is_active" class="ml-2 text-xs text-red-400">(已禁用)</span>
      </div>
      <OrgTree
        v-if="node.children.length"
        :nodes="node.children"
        :level="(level || 0) + 1"
        @select="handleSelect"
      />
    </li>
  </ul>
</template>

<script setup lang="ts">
import { useSessionStore } from '@/stores/session'
defineProps<{ source?: 'mock' | 'demo' | 'real' }>()
const session = useSessionStore()
</script>

<template>
  <span v-if="source === 'mock' || source === 'demo'" class="mock-badge">{{ session.copyBundle[source === 'mock' ? 'mock.source_notice' : 'demo.data_notice'] || '演示内容' }}</span>
</template>

<style scoped>
.mock-badge { display: inline-block; padding: var(--space-1) var(--space-3); border: 1px solid var(--color-warning-border); border-radius: var(--radius-pill); background: var(--color-warning-soft); color: var(--color-text-primary); font-size: var(--font-size-xs); }
</style>

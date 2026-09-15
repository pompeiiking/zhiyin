<script setup lang="ts">
import { computed } from 'vue'
import { useSessionStore } from '@/stores/session'
defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ select: [value: string] }>()
const session = useSessionStore()
const actions = computed(() => [
  ['conv.quick.gap_claim', session.copyBundle['conv.quick.gap_claim']],
  ['conv.quick.compare', session.copyBundle['conv.quick.compare']],
  ['conv.quick.review', session.copyBundle['conv.quick.review']],
].filter((item): item is [string, string] => Boolean(item[1])))
</script>
<template><div v-if="actions.length" class="quick-actions" aria-label="常用操作"><button v-for="item in actions" :key="item[0]" :disabled="disabled" @click="emit('select', item[1])">{{ item[1] }}</button></div></template>
<style scoped>.quick-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); }button { min-height: 40px; padding: var(--space-2) var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-pill); background: var(--color-surface); color: var(--color-text-secondary); }</style>

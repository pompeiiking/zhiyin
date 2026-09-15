<script setup lang="ts">
import TheoryTag from './TheoryTag.vue'
defineProps<{ disclosure: Record<string, unknown> | null }>()
</script>
<template>
  <div v-if="disclosure?.text" class="disclosure-row" role="status"><span aria-hidden="true">↗</span><div><p>{{ String(disclosure.text) }}</p><TheoryTag v-for="(item, index) in (disclosure.theory_refs as Record<string, unknown>[] ?? [])" :key="String(item.theory_id ?? index)" :theory="item" /></div></div>
</template>
<style scoped>
.disclosure-row { display: flex; gap: var(--space-3); padding: var(--space-3) var(--space-4); border: 1px solid var(--color-role-border); border-radius: var(--radius-md); background: var(--color-role-soft); color: var(--color-text-secondary); font-size: var(--font-size-sm); }
p { margin: 0 0 var(--space-2); }
</style>

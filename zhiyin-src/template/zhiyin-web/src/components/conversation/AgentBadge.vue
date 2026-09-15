<script setup lang="ts">
import TheoryTag from './TheoryTag.vue'
defineProps<{ badge: Record<string, unknown> }>()
</script>
<template>
  <div v-if="badge.name" class="agent-badge"><span class="avatar" aria-hidden="true">{{ String(badge.name).slice(0, 1) }}</span><div><strong>{{ String(badge.name) }}</strong><small v-if="badge.role_summary">{{ String(badge.role_summary) }}</small><div class="theories"><TheoryTag v-for="(item, index) in (badge.theory_refs as Record<string, unknown>[] ?? [])" :key="String(item.theory_id ?? index)" :theory="item" /></div></div></div>
</template>
<style scoped>
.agent-badge { display: flex; align-items: center; gap: var(--space-3); }
.avatar { width: 40px; height: 40px; display: grid; place-items: center; border-radius: var(--radius-md); background: var(--color-role-soft); color: var(--color-role); font-weight: var(--font-weight-bold); }
strong, small { display: block; } small { color: var(--color-text-secondary); margin-top: 2px; }.theories { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-2); }
</style>

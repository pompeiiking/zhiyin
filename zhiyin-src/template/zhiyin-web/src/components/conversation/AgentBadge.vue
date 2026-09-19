<script setup lang="ts">
// badge 为 null 表示"本轮还没有真实的主理信息"，此时不渲染徽章，
// 不假定某位主理在场（此前 store 里预置过一位，会被误读成真实排班）。
defineProps<{ badge: Record<string, unknown> | null }>()
</script>
<template>
  <div v-if="badge && badge.name" class="agent-badge"><span class="avatar" aria-hidden="true">{{ String(badge.name).slice(0, 1) }}</span><div><strong>{{ String(badge.name) }}</strong><small v-if="badge.role_summary">{{ String(badge.role_summary) }}</small></div></div>
</template>
<style scoped>
.agent-badge { flex: 0 1 auto; display: flex; align-items: center; gap: 11px; min-width: 0; }
.agent-badge > div { min-width: 0; overflow: hidden; }
.avatar { flex: none; width: 40px; height: 40px; display: grid; place-items: center; border-radius: 14px; background: linear-gradient(155deg, var(--blue), var(--greenD)); color: #fff; font-weight: 800; font-size: 15px; box-shadow: 0 3px 8px rgba(55, 138, 221, 0.32); }
strong, small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
strong { font-size: 14.5px; font-weight: 800; color: var(--ink); }
small { color: var(--muted); font-size: 11.5px; margin-top: 1px; }
</style>

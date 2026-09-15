<script setup lang="ts">
import { ref } from 'vue'
import { trackEvent } from '@/api/endpoints'
const props = defineProps<{ theory: Record<string, unknown> }>()
const open = ref(false)
function toggle() {
  open.value = !open.value
  if (open.value) void trackEvent('conv_disclosure_open', { theory_id: String(props.theory.theory_id ?? '') }).catch(() => {})
}
</script>
<template>
  <span class="theory"><button type="button" :aria-expanded="open" @click="toggle">依据 · {{ String(theory.name ?? theory.title ?? '方法说明') }}</button><span v-if="open" class="card" role="note"><strong>{{ String(theory.name ?? theory.title ?? '方法说明') }}</strong><span v-if="theory.school">{{ String(theory.school) }}</span><span>{{ String(theory.description ?? theory.detail ?? theory.summary ?? '详细说明将在理论卡数据接入后展示。') }}</span></span></span>
</template>
<style scoped>
.theory { position: relative; display: inline-block; }
button { min-height: 36px; border: 1px solid var(--color-brand-border); border-radius: var(--radius-pill); padding: var(--space-1) var(--space-3); background: var(--color-brand-soft); color: var(--color-link); font-size: var(--font-size-xs); }
.card { position: absolute; left: 0; top: calc(100% + var(--space-2)); z-index: 10; width: min(300px, 75vw); display: grid; gap: var(--space-2); padding: var(--space-4); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); box-shadow: var(--shadow-card); color: var(--color-text-secondary); }
.card strong { color: var(--color-text-primary); }
</style>

<script setup lang="ts">
import { computed } from 'vue'
import TheoryTag from './TheoryTag.vue'

/**
 * 显式告知行（FR-ORCH-003，后端契约 contracts/common.py::Disclosure）。
 *
 * 后端字段是 kind / text / theory_refs。这里只渲染后端真发的文案，
 * 不再用 message/reason 兜底出"本轮由新的主理继续协助你。"这种自编告知。
 */
const props = defineProps<{ disclosure?: Record<string, unknown> | null }>()

const kindLabel: Record<string, string> = {
  lead_change: '主理交接',
  theory_change: '理论依据变化',
  conclusion_change: '结论变化',
}

const title = computed(() => kindLabel[String(props.disclosure?.kind ?? '')] ?? '变更告知')
const text = computed(() => String(props.disclosure?.text ?? ''))
const theoryRefs = computed(() => {
  const raw = props.disclosure?.theory_refs
  return Array.isArray(raw) ? (raw as Array<Record<string, unknown>>) : []
})
</script>

<template>
  <div v-if="disclosure" class="disclosure-row">
    <strong>{{ title }}</strong>
    <span class="d-text">{{ text }}</span>
    <TheoryTag v-for="(item, index) in theoryRefs" :key="index" :theory="item" />
  </div>
</template>

<style scoped>
.disclosure-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-5);
  background: var(--purpleSoft);
  color: var(--gray);
  font-size: var(--font-size-sm);
  border-bottom: 1px solid var(--purpleLine);
}

strong { color: var(--violet); flex: none; }

.d-text { line-height: 1.6; }
</style>

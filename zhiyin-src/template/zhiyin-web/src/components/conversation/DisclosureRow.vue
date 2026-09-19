<script setup lang="ts">
import TheoryTag from './TheoryTag.vue'

const props = defineProps<{ disclosure?: Record<string, unknown> | null }>()
const text = () => String(props.disclosure?.message ?? props.disclosure?.reason ?? '本轮由新的主理继续协助你。')
</script>

<template>
  <div v-if="disclosure" class="disclosure-row">
    <strong>主理交接</strong>
    <span class="d-text">{{ text() }}</span>
    <TheoryTag v-if="disclosure.theory" :theory="disclosure.theory as Record<string, unknown>" />
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

<script setup lang="ts">
const props = defineProps<{
  version?: number | null
  diff?: string | null
}>()
</script>

<template>
  <div v-if="props.version != null || props.diff" class="version-diff">
    <span v-if="props.version != null" class="version">v{{ props.version }}</span>
    <p class="diff">{{ props.diff || '无差异说明' }}</p>
  </div>
</template>

<style scoped>
.version-diff {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border-left: 3px solid var(--color-warning);
  border-radius: var(--radius-sm);
  background: var(--color-warning-soft);
}

.version {
  font-weight: var(--font-weight-semibold);
  color: var(--color-warning);
}

.diff {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}
</style>

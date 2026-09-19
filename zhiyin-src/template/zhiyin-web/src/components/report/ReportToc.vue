<script setup lang="ts">
// 报告页 · 左侧目录导航（§4.4）。
//
// 目录项来自后端 ReportFullTextView.toc，不在前端硬编码章节名
// —— 15 维结构由后端与理论口径决定。
defineProps<{ items: Array<Record<string, unknown>>; activeId?: string }>()
const emit = defineEmits<{ select: [id: string] }>()
</script>

<template>
  <nav class="report-toc" aria-label="报告目录">
    <button
      v-for="item in items"
      :key="String(item.id)"
      type="button"
      class="toc-item"
      :class="{ active: String(item.id) === activeId }"
      @click="emit('select', String(item.id))"
    >
      {{ String(item.title) }}
    </button>
  </nav>
</template>

<style scoped>
.report-toc {
  position: sticky;
  top: calc(72px + var(--space-6));
  display: grid;
  gap: var(--space-1);
  align-self: start;
}

.toc-item {
  text-align: left;
  padding: var(--space-2) var(--space-3);
  border: 0;
  border-left: 2px solid transparent;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
}

.toc-item:hover {
  color: var(--color-brand-strong);
  background: var(--color-brand-soft);
}

.toc-item.active {
  border-left-color: var(--color-brand);
  background: var(--color-brand-soft);
  color: var(--color-brand-strong);
  font-weight: 700;
}
</style>

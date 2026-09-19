<script setup lang="ts">
// 报告页 · 全文区块（§4.4）。
//
// 只读资产视图：章节标题与正文全部来自 ReportFullTextView.sections，
// 前端不硬编码 15 维名称——维度口径由后端与理论卡决定。
//
// 长内容只在这里出现，**不进对话流**（全局约束①）。
const props = defineProps<{ section: Record<string, unknown> }>()
const paragraphs = () => (props.section.paragraphs as string[] | undefined) ?? []
</script>

<template>
  <section :id="String(props.section.id)" class="report-section">
    <h2>{{ String(props.section.title) }}</h2>
    <div v-if="paragraphs().length" class="rs-body">
      <p v-for="(p, index) in paragraphs()" :key="index">{{ p }}</p>
    </div>
    <p v-else-if="props.section.body" class="rs-body">{{ String(props.section.body) }}</p>
  </section>
</template>

<style scoped>
.report-section {
  padding: var(--space-6) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  scroll-margin-top: calc(72px + var(--space-4));
}

.report-section h2 {
  margin: 0 0 var(--space-4);
  font-size: var(--font-size-lg);
  font-weight: 800;
  letter-spacing: -0.01em;
}

.rs-body {
  max-width: 72ch;
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
}

.rs-body p {
  margin: 0 0 var(--space-3);
}

.rs-body p:last-child {
  margin-bottom: 0;
}
</style>

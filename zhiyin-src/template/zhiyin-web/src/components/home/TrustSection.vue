<script setup lang="ts">
import { computed } from 'vue'
import { useSessionStore } from '@/stores/session'
import MockBadge from '@/components/common/MockBadge.vue'
const session = useSessionStore()
const primary = computed(() => session.trustBlocks.find(x => x.code === 'primary_methodology') ?? session.trustBlocks[0])
const examples = computed(() => session.trustBlocks.filter(x => x !== primary.value))
</script>

<template>
  <section v-if="primary" class="trust-section" aria-labelledby="trust-title">
    <div class="trust-intro"><span class="trust-mark" aria-hidden="true">✳</span><p class="eyebrow">基于职业咨询方法论</p><h2 id="trust-title">{{ primary.title }}</h2><p>{{ primary.body }}</p></div>
    <div class="examples">
      <details v-for="item in examples" :key="item.code"><summary>{{ item.title }}<span aria-hidden="true">＋</span></summary><div class="example-body"><MockBadge v-if="session.preview" source="demo" /><p>{{ item.body }}</p><p v-if="item.expandable_ref && !session.trustBlocks.some(x => x.code === item.expandable_ref)" class="pending">完整示例内容暂未提供，当前仅展示方法说明。</p></div></details>
    </div>
  </section>
</template>

<style scoped>
.trust-section { display: grid; grid-template-columns: 1.1fr 1fr; gap: var(--space-12); padding: var(--space-10); margin-bottom: var(--space-12); border: 1px solid var(--color-success-border); border-radius: var(--radius-lg); background: var(--color-success-soft); }
.trust-mark { font-size: var(--font-size-2xl); color: var(--color-text-primary); }
.eyebrow { font-size: 10px; letter-spacing: 0.12em; color: var(--color-text-secondary); }
h2 { font-size: var(--font-size-xl); line-height: 1.5; }
.trust-intro > p:last-child { color: var(--color-text-secondary); }
.examples { align-self: center; }
details { border-bottom: 1px solid var(--color-success-border); }
summary { display: flex; justify-content: space-between; gap: var(--space-4); padding-block: var(--space-5); cursor: pointer; list-style: none; font-weight: var(--font-weight-semibold); }
summary::-webkit-details-marker { display: none; }
details[open] summary span { transform: rotate(45deg); }
.example-body { padding-bottom: var(--space-4); }
.pending { color: var(--color-text-secondary); font-size: var(--font-size-xs); }
@media (max-width: 900px) { .trust-section { grid-template-columns: 1fr; gap: var(--space-4); padding: var(--space-6); } }
</style>

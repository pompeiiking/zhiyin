<script setup lang="ts">
import { computed, ref } from 'vue'
import type { components } from '@/api/types'

type StagePanelView = components['schemas']['StagePanelView']

const props = defineProps<{
  title: string
  panel: StagePanelView | null
  index: number
}>()

type Mode = 'status' | 'theory' | 'diff'
const open = ref<Mode | null>(null)

function toggle(mode: Mode) {
  open.value = open.value === mode ? null : mode
}

function list(value?: Record<string, unknown>[] | null) {
  return value ?? []
}

function display(value: unknown) {
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function modelName(item: Record<string, unknown>) {
  return String(item.name ?? item.title ?? item.model ?? display(item))
}

const statusText = computed(() => props.panel?.evaluation || '待进入 · 尚未生成')
const hasDiff = computed(() => props.panel != null && (props.panel.diff || props.panel.version != null))
const updatedAt = computed(() => {
  const value = props.panel?.updated_at
  return value ? new Date(value).toLocaleString() : ''
})
</script>

<template>
  <section class="stage-panel">
    <header class="panel-head">
      <span class="number">{{ index + 1 }}</span>
      <div class="panel-title">
        <strong>{{ title }}</strong>
        <small v-if="updatedAt">更新于 {{ updatedAt }}</small>
      </div>
    </header>

    <p class="status">{{ statusText }}</p>

    <div class="modes">
      <button type="button" class="mode-head" :aria-expanded="open === 'status'" @click="toggle('status')">
        当前状态 <span aria-hidden="true">{{ open === 'status' ? '−' : '＋' }}</span>
      </button>
      <p v-if="open === 'status'" class="mode-body">{{ statusText }}</p>

      <button type="button" class="mode-head" :aria-expanded="open === 'theory'" @click="toggle('theory')">
        理论模型 <span aria-hidden="true">{{ open === 'theory' ? '−' : '＋' }}</span>
      </button>
      <ul v-if="open === 'theory'" class="theory-list">
        <li v-for="(item, itemIndex) in list(panel?.theory_models)" :key="itemIndex">{{ modelName(item) }}</li>
      </ul>

      <button
        v-if="hasDiff"
        type="button"
        class="mode-head"
        :aria-expanded="open === 'diff'"
        @click="toggle('diff')"
      >
        历史差异 <span aria-hidden="true">{{ open === 'diff' ? '−' : '＋' }}</span>
      </button>
      <p v-if="open === 'diff' && hasDiff" class="mode-body">
        <template v-if="panel?.version != null">v{{ panel.version }}：</template>{{ panel?.diff || '无差异说明' }}
      </p>
    </div>
  </section>
</template>

<style scoped>
/* 层次化属性规范（CONV-003）：L1 容器卡只有这里允许描边，分组/字段靠底色与间距区分 */
.stage-panel {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.panel-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-pill);
  background: var(--color-brand-soft);
  color: var(--color-brand);
  font-size: var(--font-size-sm);
}

.panel-title strong {
  display: block;
  font-size: var(--font-size-md);
}

.panel-title small {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.status {
  margin: var(--space-3) 0;
  color: var(--color-text-secondary);
}

.modes {
  display: grid;
  gap: var(--space-2);
}

.mode-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 0;
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  text-align: left;
}

.mode-head:hover {
  background: var(--color-brand-soft);
  color: var(--color-brand);
}

.mode-body {
  margin: 0;
  padding: var(--space-2) var(--space-3);
  color: var(--color-text-secondary);
}

.theory-list {
  margin: 0;
  padding: var(--space-1) var(--space-3) var(--space-1) var(--space-6);
  color: var(--color-text-secondary);
}
</style>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { PipelineCardView } from '@/api/schema'
import { useSessionStore } from '@/stores/session'
import TheoryTag from './TheoryTag.vue'

const props = defineProps<{ card: PipelineCardView; index: number; leadName?: string }>()

const router = useRouter()
const session = useSessionStore()

type Mode = 'output' | 'theory' | 'eval'
const open = ref<Mode | null>(null)

function toggle(mode: Mode) {
  open.value = open.value === mode ? null : mode
}

function entries(value?: Record<string, unknown> | null) {
  return Object.entries(value ?? {}).filter(([, item]) => item != null)
}

function display(value: unknown) {
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

const statusText = computed(() =>
  props.card.status === 'done' ? '已完成' : props.card.status === 'in_progress' ? '进行中' : '待开始',
)

const isEmpty = computed(
  () => !props.card.current_output && !props.card.theory_models?.length && !props.card.evaluation,
)

/**
 * 「待进入」说明取自动态文案包（AGENTS.md §8：文案不得硬编码在前端）。
 * 读不到就整条不渲染，而不是回落成前台自造的默认句。
 */
const pendingHint = computed(() => session.copyBundle[`stage.${props.card.stage}.pending_hint`] ?? '')

/**
 * 「查看明细 →」的去处：② 诊断的明细是报告全文，其余环节的明细在工作台分层资产里。
 * 两个页面都读真实资产；此前这个按钮没有 @click，点了没有任何反应。
 */
function openDetail() {
  void router.push({ name: props.card.stage === 'diagnose' ? 'report' : 'workspace' })
}
</script>

<template>
  <!-- L1 容器卡：仅此层允许描边 -->
  <article class="pipeline-card" :class="[card.status, { active: card.active }]" :aria-current="card.active ? 'step' : undefined">
    <header class="card-head">
      <span class="number">{{ index + 1 }}</span>
      <div class="card-title">
        <strong>{{ card.title }}</strong>
        <small>{{ statusText }}</small>
      </div>
    </header>

    <div class="lead-row">
      <span>当前主理</span>
      <strong>{{ leadName || '待分配' }}</strong>
    </div>

    <p v-if="isEmpty && pendingHint" class="empty-note">{{ pendingHint }}</p>

    <template v-else>
      <!-- L2 分组：无描边，靠底色区分；三态互斥展开 -->
      <div v-if="card.current_output" class="mode">
        <button type="button" class="mode-head" :aria-expanded="open === 'output'" @click="toggle('output')">
          当前产出 <span aria-hidden="true">{{ open === 'output' ? '−' : '＋' }}</span>
        </button>
        <dl v-if="open === 'output'">
          <template v-for="item in entries(card.current_output)" :key="item[0]">
            <dt>{{ item[0] }}</dt>
            <dd>{{ display(item[1]) }}</dd>
          </template>
        </dl>
        <button v-if="open === 'output'" type="button" class="detail-link" @click="openDetail">
          查看明细 →
        </button>
      </div>

      <div v-if="card.theory_models?.length" class="mode">
        <button type="button" class="mode-head" :aria-expanded="open === 'theory'" @click="toggle('theory')">
          理论模型 <span aria-hidden="true">{{ open === 'theory' ? '−' : '＋' }}</span>
        </button>
        <div v-if="open === 'theory'" class="theory-list">
          <TheoryTag v-for="(item, itemIndex) in card.theory_models" :key="itemIndex" :theory="item" />
        </div>
      </div>

      <div v-if="card.evaluation" class="mode">
        <button type="button" class="mode-head" :aria-expanded="open === 'eval'" @click="toggle('eval')">
          评价状态 <span aria-hidden="true">{{ open === 'eval' ? '−' : '＋' }}</span>
        </button>
        <dl v-if="open === 'eval'">
          <template v-for="item in entries(card.evaluation)" :key="item[0]">
            <dt>{{ item[0] }}</dt>
            <dd>{{ display(item[1]) }}</dd>
          </template>
        </dl>
      </div>
    </template>
  </article>
</template>

<style scoped>
/* 层次化属性规范（CONV-003）：L1 容器卡 / L2 分组 / L3 属性行，描边只允许出现在 L1 */
.pipeline-card {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.pipeline-card.active {
  border-color: var(--color-brand);
  box-shadow: inset 3px 0 var(--color-brand), var(--shadow-card);
  animation: active-breathe 3s ease-in-out infinite;
}

@keyframes active-breathe {
  50% { box-shadow: inset 3px 0 var(--color-brand), 0 0 0 3px var(--color-brand-soft); }
}

.pipeline-card.done .number {
  background: var(--color-success-soft);
  color: var(--color-success-strong);
}

.card-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.number {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--color-brand-soft);
  color: var(--color-link);
  flex-shrink: 0;
}

.card-title strong,
.card-title small {
  display: block;
}

.card-title small {
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

.lead-row {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

.lead-row strong { color: var(--color-role); }

@media (prefers-reduced-motion: reduce) {
  .pipeline-card.active { animation: none; }
}

.empty-note {
  margin: var(--space-3) 0 0;
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

/* L2 分组：无描边，靠浅底色与间距区分 */
.mode {
  margin-top: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.mode-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 40px;
  padding: var(--space-2) var(--space-3);
  border: 0;
  background: transparent;
  color: var(--color-link);
  font-size: var(--font-size-xs);
  cursor: pointer;
  text-align: left;
}

.mode-head:hover {
  color: var(--color-brand-strong);
}

.mode-head:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-focus);
  outline-offset: var(--focus-ring-offset);
}

/* L3 属性行：无边框无底色，行间用极浅分隔线 */
dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-1) var(--space-3);
  margin: 0;
  padding: 0 var(--space-3) var(--space-3);
  font-size: var(--font-size-xs);
}

dt {
  color: var(--color-text-secondary);
}

dd {
  margin: 0;
  overflow-wrap: break-word;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-1);
}

.theory-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0 var(--space-3) var(--space-3);
}

.detail-link {
  display: block;
  width: 100%;
  padding: var(--space-2) var(--space-3) var(--space-3);
  border: 0;
  background: transparent;
  color: var(--color-link);
  font-size: var(--font-size-xs);
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.detail-link:hover {
  color: var(--color-brand-strong);
}
</style>

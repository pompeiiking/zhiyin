<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'

import { useSessionStore } from '@/stores/session'
import { trackEvent } from '@/api/endpoints'

// 首页 · 任务/场景卡组（§4.1 / HOME-005）。
// 只负责渲染与向上抛选择事件；入口交接 / 游客拦截 / 埋点由 HomePage 的 selectTask 统一处理。
// 后端未接入时用演示场景卡兜底，标注「演示数据」（改版 §3.5 / OTH-006）。
defineProps<{ busy?: boolean; selected?: string }>()
const emit = defineEmits<{ (e: 'select', code: string): void }>()

const session = useSessionStore()
const { taskEntries, copyBundle } = storeToRefs(session)

const entries = computed(() =>
  taskEntries.value.slice().sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)),
)

// 演示场景数据：后端未接入时的内容化兜底
const demoScenes = [
  { code: 'campus', label: '校招求职', desc: '秋招 / 春招的岗位定位与投递策略', window: '秋招 9–11 月 · 春招 3–4 月', sample: '岗位匹配方案', open: true },
  { code: 'postgrad', label: '考研 / 保研 / 留学', desc: '升学方向选择与准备节奏', window: '考研 12 月 · 申请季 11–1 月', sample: '方向对比方案', open: true },
  { code: 'civil', label: '考公 / 考编', desc: '岗位选择与备考节奏', window: '国考 11 月 · 省考 3 月', sample: '备考计划', open: false },
  { code: 'earlycareer', label: '职场新人转型', desc: '初入职场的方向校准与跳槽规划', window: '随时可开始', sample: '转型路径方案', open: false },
] as const

const isDemo = computed(() => entries.value.length === 0)
const reserved = ref<string[]>([])

function onDemoClick(code: string, open: boolean) {
  if (open) {
    emit('select', code)
  } else if (!reserved.value.includes(code)) {
    reserved.value = [...reserved.value, code]
    void trackEvent('home_reserve_click', { code }).catch(() => {})
  }
}
</script>

<template>
  <section id="task-entries" class="task-card-group">
    <h2 class="group-title">{{ copyBundle['home.task_group_title'] || '从你当前的状态出发' }}</h2>

    <!-- 后端未接入：演示场景卡（内容化，标注演示数据） -->
    <div v-if="isDemo" class="cards">
      <button
        v-for="scene in demoScenes"
        :key="scene.code"
        type="button"
        class="task-card"
        :class="{ 'is-reserved': !scene.open && reserved.includes(scene.code) }"
        :disabled="busy"
        @click="onDemoClick(scene.code, scene.open)"
      >
        <span class="task-label">{{ scene.label }}</span>
        <span class="task-desc">{{ scene.desc }}</span>
        <span class="task-window">窗口：{{ scene.window }}</span>
        <span class="task-sample">产出示例：{{ scene.sample }}</span>
        <span class="task-state" :class="scene.open ? 'open' : 'closed'">
          {{ scene.open ? '已开放 · 直接进入' : (reserved.includes(scene.code) ? '已加入等待（演示）' : '未开放 · 可预约') }}
        </span>
      </button>
    </div>

    <!-- 后端接入：真实任务入口 -->
    <div v-else class="cards">
      <button
        v-for="entry in entries"
        :key="entry.code"
        type="button"
        class="task-card"
        :class="{ 'is-open': entry.target_stage == null, 'is-selected': selected === entry.code }"
        :disabled="busy"
        @click="emit('select', entry.code)"
      >
        <span class="task-label">{{ entry.label }}</span>
        <span v-if="entry.lead_agent_name" class="task-lead">{{ entry.lead_agent_name }}</span>
        <span class="task-state open">已开放 · 直接进入</span>
      </button>
    </div>

    <p v-if="isDemo" class="demo-tag">演示数据 · 连接服务后展示你的真实任务入口</p>
  </section>
</template>

<style scoped>
.task-card-group {
  margin-bottom: var(--space-12);
}

.group-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--space-6);
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-4);
}

.task-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  text-align: left;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}

.task-card:hover:not(:disabled) {
  border-color: var(--color-brand-border);
  box-shadow: var(--shadow-card);
}

.task-card:active:not(:disabled) {
  transform: scale(0.99);
}

.task-card.is-open {
  border-color: var(--color-brand);
  background: var(--color-brand-soft);
}

.task-card.is-selected {
  border-color: var(--color-brand);
  box-shadow: 0 0 0 1px var(--color-brand);
}

.task-card.is-reserved {
  opacity: 0.75;
}

.task-card:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.task-label {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.task-desc,
.task-window,
.task-sample {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.task-lead {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.task-state {
  margin-top: var(--space-2);
  padding: 2px var(--space-3);
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
}

.task-state.open {
  background: var(--color-success-soft);
  color: var(--color-success-strong);
}

.task-state.closed {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

.demo-tag {
  margin: var(--space-3) 0 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}
</style>

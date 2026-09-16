<script setup lang="ts">
import { computed } from 'vue'
import { useConversationStore } from '@/stores/conversation'
import AgentBadge from './AgentBadge.vue'

const conversation = useConversationStore()
const currentTaskName = computed(() => {
  const item = conversation.sessions.find((session) => session.task_id === conversation.currentTaskId)
  return String(item?.task_name ?? '当前任务')
})

const stageLabels = ['采集', '诊断', '决策', '行动', '复盘']
const stageProgress = computed(() =>
  stageLabels.map((label, index) => {
    const card = conversation.pipeline[index] as Record<string, unknown> | undefined
    return {
      label,
      done: card?.status === 'done',
      active: Boolean(card?.active) || (!conversation.pipeline.length && index === 0),
    }
  }),
)
</script>

<template>
  <section class="chat-stream" aria-label="当前对话">
    <header>
      <div class="task-head">
        <div>
          <small>当前任务</small>
          <h1>{{ currentTaskName }}</h1>
        </div>
        <AgentBadge :badge="conversation.badge" />
      </div>
      <ol class="stage-progress" aria-label="五环节进度">
        <li v-for="stage in stageProgress" :key="stage.label" :class="{ done: stage.done, active: stage.active }">
          <span aria-hidden="true"></span>{{ stage.label }}
        </li>
      </ol>
    </header>
    <div class="messages">
      <div class="empty">
        <span aria-hidden="true">✳</span>
        <h2>从一个具体困惑开始</h2>
        <p>选择任务后，对话内容会显示在这里。</p>
      </div>
    </div>
    <footer class="behavior-slot" aria-label="行为引导区">
      <strong>下一步</strong>
      <span>选择一项任务，开始梳理当前问题。</span>
    </footer>
  </section>
</template>

<style scoped>
.chat-stream { min-width: 0; min-height: 0; display: grid; grid-template-rows: auto 1fr auto; background: var(--color-surface); }
.chat-stream > header { padding: var(--space-4) var(--space-6); border-bottom: 1px solid var(--color-border); }
.task-head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); }
.task-head small { color: var(--color-text-muted); }
.task-head h1 { margin: var(--space-1) 0 0; font-size: var(--font-size-lg); }
.stage-progress { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-2); margin: var(--space-4) 0 0; padding: 0; list-style: none; color: var(--color-text-muted); font-size: var(--font-size-xs); }
.stage-progress li { display: flex; align-items: center; gap: var(--space-1); }
.stage-progress span { width: 8px; height: 8px; border-radius: 50%; background: var(--color-border); }
.stage-progress li.done span { background: var(--color-success); }
.stage-progress li.active { color: var(--color-link); font-weight: var(--font-weight-semibold); }
.stage-progress li.active span { background: var(--color-brand); box-shadow: 0 0 0 3px var(--color-brand-soft); }
.messages { min-height: 0; overflow: auto; display: grid; place-items: center; padding: var(--space-6); }
.empty { text-align: center; color: var(--color-text-secondary); }
.empty > span { font-size: var(--font-size-2xl); color: var(--color-link); }
.empty h2 { color: var(--color-text-primary); }
.behavior-slot { display: flex; gap: var(--space-3); align-items: center; padding: var(--space-4) var(--space-6); border-top: 1px solid var(--color-border); background: var(--color-brand-soft); color: var(--color-text-secondary); }
.behavior-slot strong { color: var(--color-link); }
</style>

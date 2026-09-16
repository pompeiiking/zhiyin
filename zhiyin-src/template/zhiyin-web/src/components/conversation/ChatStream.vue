<script setup lang="ts">
import { computed, ref } from 'vue'
import { useConversationStore } from '@/stores/conversation'
import AgentBadge from './AgentBadge.vue'
import BehaviorGuide from './BehaviorGuide.vue'
import DisclosureRow from './DisclosureRow.vue'
import MessageBubble from './MessageBubble.vue'
import QuickActions from './QuickActions.vue'

const conversation = useConversationStore()
const input = ref('')
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
const messages = computed(() => conversation.turns
  .map((item) => ({ role: item.role === 'user' ? 'user' as const : 'agent' as const, content: String(item.content ?? item.text ?? ''), theory: item.theory as Record<string, unknown> | undefined }))
  .filter((item) => item.content))
const guide = computed(() => conversation.guide)
const disclosure = computed(() => conversation.disclosure)
function send() { input.value = '' }
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
    <DisclosureRow :disclosure="disclosure" />
    <div class="messages">
      <div class="message-list"><MessageBubble v-for="(item, index) in messages" :key="index" :role="item.role" :content="item.content" :theory="item.theory" /></div>
    </div>
    <QuickActions @choose="value => { input = value; send() }" />
    <BehaviorGuide :guide="guide" @choose="value => { input = value; send() }" />
    <form class="composer" @submit.prevent="send"><input v-model="input" aria-label="输入消息" placeholder="写下你现在最想解决的困惑…" /><button type="submit" :disabled="!input.trim()">发送</button></form>
  </section>
</template>

<style scoped>
.chat-stream { min-width: 0; min-height: 0; display: grid; grid-template-rows: auto auto 1fr auto auto auto; background: var(--color-surface); }
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
.messages { min-height: 0; overflow: auto; padding: var(--space-6); }
.message-list { display:grid; align-content:end; gap:var(--space-4); min-height:100%; }
.composer { display:flex; gap:var(--space-2); padding:var(--space-3) var(--space-6) var(--space-4); border-top:1px solid var(--color-border); background:var(--color-surface); }
.composer input { flex:1; min-width:0; height:44px; padding-inline:var(--space-3); border:1px solid var(--color-border); border-radius:var(--radius-md); }
.composer button { min-width:72px; border:0; border-radius:var(--radius-md); background:var(--color-action-bg); color:var(--color-text-inverse); cursor:pointer; }
.composer button:disabled { opacity:.5; cursor:not-allowed; }
</style>

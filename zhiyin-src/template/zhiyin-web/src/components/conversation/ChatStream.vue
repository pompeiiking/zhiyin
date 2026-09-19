<script setup lang="ts">
import { computed, ref } from 'vue'
import { useConversationStore } from '@/stores/conversation'
import AgentBadge from './AgentBadge.vue'
import AnalysisHandoff from './AnalysisHandoff.vue'
import BehaviorGuide from './BehaviorGuide.vue'
import DisclosureRow from './DisclosureRow.vue'
import MessageBubble from './MessageBubble.vue'

const conversation = useConversationStore()
const input = ref('')
const sending = ref(false)
const headTitle = computed(() => {
  const taskName = conversation.sessions.find((session) => session.task_id === conversation.currentTaskId)?.task_name
  // 徽章只由真实一轮对话写入；没有任务时显示中性文案，不假定某位主理在场。
  return String(taskName ?? conversation.badge?.name ?? '核心对话')
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
  .map((item) => {
    const rawRole = String(item.role ?? 'agent')
    const role = rawRole === 'user' ? 'user' as const : rawRole === 'coach' ? 'coach' as const : 'agent' as const
    return {
      role,
      content: String(item.content ?? item.text ?? ''),
      theory: item.theory as Record<string, unknown> | undefined,
      action: item.action as string | undefined,
      long: Boolean(item.long),
    }
  })
  .filter((item) => item.content))
const guide = computed(() => conversation.guide)
const disclosure = computed(() => conversation.disclosure)
function send() {
  const text = input.value.trim()
  if (!text || sending.value) return
  conversation.turns.push({ role: 'user', content: text })
  input.value = ''
  sending.value = true
  // 真实一轮对话由 conversation.send 走 POST /app/conversation/message。
  // 这里不再合成任何"已收到"之类的假回复：接口失败就如实报错。
  conversation
    .send(text)
    .catch((err: unknown) => {
      conversation.turns.push({
        role: 'coach',
        content: `这轮消息没有发送成功：${err instanceof Error ? err.message : '未知错误'}。请稍后重试。`,
      })
    })
    .finally(() => {
      sending.value = false
    })
}
</script>

<template>
  <section class="chat-stream" aria-label="当前对话">
    <header class="chat-head">
      <div class="chat-head-l">
        <span class="dot-live" aria-hidden="true"></span>
        <h1>{{ headTitle }}</h1>
      </div>
      <AgentBadge :badge="conversation.badge" />
      <!-- 闭环进度：页头底部的细分段条；每一步的细节在右栏管线卡 -->
      <ol class="stagebar" aria-label="五环节进度">
        <li
          v-for="(stage, index) in stageProgress"
          :key="stage.label"
          :class="{ done: stage.done, on: stage.active }"
          :title="`${index + 1} ${stage.label}`"
          :aria-label="stage.label"
          :aria-current="stage.active ? 'step' : undefined"
        ></li>
      </ol>
    </header>

    <DisclosureRow :disclosure="disclosure" />

    <!-- 建档完成 → ②诊断交接条（最短状态 + 下一步入口；全文在完整报告页，见 §2.3、§4.7） -->
    <AnalysisHandoff />

    <div class="chat-scroll">
      <div v-if="messages.length" class="message-list"><MessageBubble v-for="(item, index) in messages" :key="index" :role="item.role" :content="item.content" :theory="item.theory" :action="item.action" :long="item.long" /></div>
      <div v-else class="empty-chat">
        <p>在下方写下你现在最想解决的困惑，开始和 AI 聊职业。</p>
      </div>
    </div>

    <BehaviorGuide :guide="guide" @choose="value => { input = value; send() }" />

    <form class="chat-input-bar" @submit.prevent="send">
      <button class="ci-attach" type="button" aria-label="添加附件" title="添加附件">＋</button>
      <div class="chat-input-fake"><span class="ci-dot" aria-hidden="true"></span><input v-model="input" aria-label="输入消息" placeholder="写下你现在最想解决的困惑…" /></div>
      <button class="ci-send" type="submit" :disabled="!input.trim() || sending"><span v-if="sending" class="ci-spinner" aria-hidden="true"></span>{{ sending ? '发送中' : '发送' }}</button>
    </form>
  </section>
</template>

<style scoped>
.chat-stream {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto auto 1fr auto auto;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r);
  box-shadow: var(--shadow);
  overflow: hidden;
}

/* 中栏是固定宽度的对话主区：子项允许收缩到容器宽度内，长文案走省略号而不是撑破列 */
.chat-stream > * { min-width: 0; }

.chat-head {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px var(--space-5) 12px;
  border-bottom: 1px solid var(--line);
}

.chat-head-l {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
}

.chat-head-l .dot-live {
  flex: none;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 0 4px var(--greenSoft);
  animation: blink 1.4s infinite;
}

@keyframes blink {
  0%, 80%, 100% { opacity: 0.25; }
  40% { opacity: 1; }
}

.chat-head-l h1 {
  margin: 0;
  min-width: 0;
  overflow: hidden;
  font-size: var(--font-size-lg);
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stagebar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  gap: 3px;
  margin: 0;
  padding: 0 var(--space-5);
  list-style: none;
}

.stagebar li {
  flex: 1;
  height: 3px;
  border-radius: 2px;
  background: var(--line);
}

.stagebar li.done { background: var(--green); }
.stagebar li.on { background: var(--blue); }

.chat-scroll {
  min-height: 0;
  overflow: auto;
  padding: 18px var(--space-5);
  background: linear-gradient(180deg, #FBFAF7, #F7F5F0);
}

.message-list {
  display: grid;
  align-content: end;
  gap: 18px;
  min-height: 100%;
}

.empty-chat {
  height: 100%;
  display: grid;
  place-items: center;
}

.empty-chat p {
  max-width: 320px;
  margin: 0;
  color: var(--muted);
  font-size: var(--font-size-sm);
  line-height: 1.7;
  text-align: center;
}

.chat-input-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px var(--space-5);
  border-top: 1px solid var(--line);
  background: var(--card);
}

.chat-input-fake {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: var(--pill);
  padding: 8px 16px;
  background: var(--paper);
}

.ci-dot {
  flex: none;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--muted);
  animation: blink 1.4s infinite;
}

.chat-input-fake input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  outline: none;
  color: var(--ink);
  font-size: var(--font-size-base);
}

.chat-input-fake input::placeholder { color: var(--muted); }

.ci-send {
  flex: none;
  min-width: 72px;
  border: 0;
  border-radius: var(--pill);
  background: var(--blue);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  padding: 10px 18px;
  cursor: pointer;
}

.ci-send:disabled { background: var(--line); opacity: 0.7; cursor: not-allowed; }

.ci-attach {
  flex: none;
  width: 40px;
  height: 40px;
  border: 1px solid var(--line);
  border-radius: 50%;
  background: var(--card);
  color: var(--muted);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}

.ci-attach:hover { border-color: var(--blue); color: var(--blueD); }

.ci-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  margin-right: 6px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  vertical-align: -2px;
}

@keyframes spin { to { transform: rotate(360deg); } }

@media (prefers-reduced-motion: reduce) {
  .chat-head-l .dot-live, .ci-dot { animation: none; }
  .ci-spinner { animation: none; }
}
</style>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useConversationStore } from '@/stores/conversation'
import AgentBadge from './AgentBadge.vue'
import AnalysisHandoff from './AnalysisHandoff.vue'
import BehaviorGuide from './BehaviorGuide.vue'
import DisclosureRow from './DisclosureRow.vue'
import MessageBubble from './MessageBubble.vue'

const conversation = useConversationStore()
const input = ref('')
const inputEl = ref<HTMLInputElement | null>(null)
const sending = ref(false)
const headTitle = computed(() => {
  const taskName = conversation.sessions.find((session) => session.task_id === conversation.currentTaskId)?.task_name
  // 徽章只由真实一轮对话写入；没有任务时显示中性文案，不假定某位主理在场。
  return String(taskName ?? conversation.badge?.name ?? '核心对话')
})

const stageLabels = ['采集', '诊断', '决策', '行动', '复盘']
// 高亮只认后端 pipeline_cards 里的 active；没有管线数据时五段全部中性，
// 不把"第一段"伪造成"当前正在采集"。
const stageProgress = computed(() =>
  stageLabels.map((label, index) => {
    const card = conversation.pipeline[index] as Record<string, unknown> | undefined
    return {
      label,
      done: card?.status === 'done',
      active: Boolean(card?.active),
    }
  }),
)
const messages = computed(() => conversation.turns
  .map((item) => {
    const rawRole = String(item.role ?? 'agent')
    // 取值与冻结契约 ConversationMessageView.role 严格一致（agent / user / system）。
    const role = rawRole === 'user' ? 'user' as const : rawRole === 'system' ? 'system' as const : 'agent' as const
    return {
      role,
      content: String(item.content ?? item.text ?? ''),
      // 主理名来自后端（实时轮次与历史查询同一口径）；缺失时留空，由气泡回落中性称呼。
      author: item.author as string | undefined,
      theory: item.theory as Record<string, unknown> | undefined,
    }
  })
  .filter((item) => item.content))
const guide = computed(() => conversation.guide)
const disclosure = computed(() => conversation.disclosure)
const scrollEl = ref<HTMLElement | null>(null)

/**
 * 把消息流滚到最新一条。
 *
 * 此前 .chat-scroll 永远停在 scrollTop=0：进入会话或发完一轮后，用户看到的
 * 仍是最早的历史，刚收到的 AI 回复在可视区之外，必须手动往下滚——这是主对话
 * 最影响可用性的问题。切换会话、进页面、新增消息三种时机都要贴到底。
 */
async function scrollToLatest() {
  await nextTick()
  const el = scrollEl.value
  if (el) el.scrollTop = el.scrollHeight
}

// 会话标识或消息条数变化都会触发：切换会话后要贴到底，新消息到达后也要。
watch(
  () => `${conversation.currentTaskId ?? ''}#${messages.value.length}`,
  () => { void scrollToLatest() },
)
onMounted(() => { void scrollToLatest() })

/**
 * 行为引导选项点击：只接受字符串。
 *
 * 曾经这里直接把 BehaviorGuide 抛上来的对象塞进 input，input 变成对象后
 * `input.trim()` 抛 TypeError，整个中栏渲染崩溃。选项必须传 label 字符串。
 */
function onChoose(value: string) {
  if (typeof value !== 'string' || !value.trim() || sending.value) return
  input.value = value
  void send()
}

function focusInput() {
  inputEl.value?.focus()
}

function send() {
  const text = input.value.trim()
  if (!text || sending.value) return
  input.value = ''
  sending.value = true
  // 用户气泡由 conversation.send 统一写入（它在 await 之前同步 push），这里不再二次 push：
  // 曾经两处都 push，真实任务下每条消息都会出现两个用户气泡。
  // 真实一轮对话由 conversation.send 走 POST /app/conversation/message。
  // 这里不合成任何"已收到"之类的假回复：接口失败就如实报错。
  conversation
    .send(text)
    .catch((err: unknown) => {
      conversation.turns.push({
        role: 'system',
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

    <div ref="scrollEl" class="chat-scroll">
      <div v-if="messages.length" class="message-list"><MessageBubble v-for="(item, index) in messages" :key="index" :role="item.role" :content="item.content" :author="item.author" :theory="item.theory" /></div>
      <div v-else class="empty-chat">
        <p>在下方写下你现在最想解决的困惑，开始和 AI 聊职业。</p>
      </div>
    </div>

    <BehaviorGuide :guide="guide" @choose="onChoose" @focus-input="focusInput" />

    <form class="chat-input-bar" @submit.prevent="send">
      <div class="chat-input-fake"><span class="ci-dot" aria-hidden="true"></span><input ref="inputEl" v-model="input" aria-label="输入消息" placeholder="写下你现在最想解决的困惑…" /></div>
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

/* 标题优先于徽章：徽章的 role_summary 很长，曾经把 .chat-head-l 挤到 41px，
   会话名被截成「直.」——连当前在哪个任务里都看不出来。给标题留最小宽度，由徽章省略。 */
.chat-head-l {
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 7em;
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

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import MockBadge from '@/components/common/MockBadge.vue'
import { agentCatalog, useAgentsStore } from '@/stores/agents'

// 首页「五个智能体，各管一段」（HOME-008 前的智能体区）。
//
// 点卡片 = 卡片网格切换成一个小对话框，直接与该智能体对话（演示数据），
// 不跳转核心对话页。数据源与智能体小队同一份（stores/agents.ts）。
const router = useRouter()
const agents = useAgentsStore()

// ⚠️ 演示阶段：开场白与回复为本地演示数据，后端会话引擎接入后替换。
const greetings: Record<string, string> = {
  profile_analyst: '我是建档分析师，负责把零散信息沉淀成结构化画像。先聊聊你的学校、专业、年级？',
  career_advisor: '我是职业顾问，帮你把画像和目标岗位对齐。你目前最想去的方向是什么？',
  path_planner: '我是路径规划师，帮你把方向拆成今天就能勾掉的小任务。定了方向吗？',
  companion_coach: '我是陪伴教练，盯执行、给反馈。最近进展卡在哪了？',
  info_scout: '我是信息侦查员，按需供给外部事实。想查哪类岗位、院校或行业信息？',
}

const replies: Record<string, string> = {
  profile_analyst: '收到，已记下。再补充一下你上手能用的工具或软件？',
  career_advisor: '明白。基于这个方向，你最看重薪资、稳定还是兴趣？',
  path_planner: '好，我们把它拆小一点：这周能先完成的一件事是什么？',
  companion_coach: '收到。有具体卡点吗？还是需要我陪你定个小目标？',
  info_scout: '好，我帮你查一下这个方向最近的岗位与时间窗口（演示数据）。',
}

// 每位智能体的快捷提问，点击直接发送，让对话框不那么空。
const suggestions: Record<string, string[]> = {
  profile_analyst: ['我的专业该怎么描述？', '哪些经历算有效证据？', '兴趣和价值观怎么聊？'],
  career_advisor: ['结构设计适合我吗？', '我的差距主要在哪？', '还有哪些备选方向？'],
  path_planner: ['这周该先做什么？', '怎么把方向拆成小任务？', '关键时间节点怎么排？'],
  companion_coach: ['最近总拖延怎么办？', '怎么保持行动动力？', '复盘该从哪开始？'],
  info_scout: ['查一下结构设计岗要求', '最近有什么招聘窗口？', '这个方向的薪资行情如何？'],
}

const activeAgentId = ref<string | null>(null)
const messages = ref<Array<{ role: 'agent' | 'user'; content: string }>>([])
const draft = ref('')
const busy = ref(false)

const activeAgent = computed(() => (activeAgentId.value ? agents.agentById(activeAgentId.value) : null))
const quickPrompts = computed(() => (activeAgentId.value ? suggestions[activeAgentId.value] ?? [] : []))

function openChat(id: string) {
  const agent = agents.agentById(id)
  if (!agent) return
  activeAgentId.value = id
  busy.value = false
  messages.value = [{ role: 'agent', content: greetings[id] ?? `我是${agent.name}，${agent.role}。想聊点什么？` }]
  draft.value = ''
}

function closeChat() {
  activeAgentId.value = null
  messages.value = []
  draft.value = ''
  busy.value = false
}

function send(preset?: string) {
  const id = activeAgentId.value
  const text = (preset ?? draft.value).trim()
  if (!text || busy.value || !id) return
  messages.value.push({ role: 'user', content: text })
  draft.value = ''
  busy.value = true
  window.setTimeout(() => {
    busy.value = false
    if (activeAgentId.value === id) {
      messages.value.push({ role: 'agent', content: replies[id] ?? '（演示）收到。' })
    }
  }, 600)
}

function openTeam() {
  void router.push({ name: 'agents' })
}
</script>

<template>
  <section id="agents" class="agents">
    <div class="container">
      <div class="head">
        <div>
          <h2>五个智能体，各管一段</h2>
          <p>采集、诊断、决策、行动、复盘各有主理，共用同一份画像与结论。</p>
        </div>
        <button class="head-cta" type="button" @click="openTeam">查看智能体小队 →</button>
      </div>

      <ul v-if="!activeAgent" class="agent-grid">
        <li v-for="agent in agentCatalog" :key="agent.id" :class="agent.theme">
          <button class="agent-card" type="button" @click="openChat(agent.id)">
            <span class="swatch" aria-hidden="true"></span>
            <span class="card-top">
              <span class="no" aria-hidden="true">{{ agent.no }}</span>
              <span class="stage">{{ agent.stages }}</span>
            </span>
            <span class="name">{{ agent.name }}</span>
            <span class="role">{{ agent.role }}</span>
            <span class="boundary">不做：{{ agent.boundary }}</span>
            <span class="go">和他对话 →</span>
          </button>
        </li>
      </ul>

      <!-- 点卡片后：卡片网格切换成一个大对话框，返回按钮回到卡片列表 -->
      <div v-else class="chat-panel" :class="activeAgent.theme">
        <header class="chat-head">
          <button class="chat-back" type="button" @click="closeChat">← 返回</button>
          <span class="chat-ico">{{ activeAgent.shortName }}</span>
          <div class="chat-meta"><b>{{ activeAgent.name }}</b></div>
          <span class="chat-stage">{{ activeAgent.stages }}</span>
        </header>
        <div class="chat-body">
          <div v-for="(m, i) in messages" :key="i" class="chat-row" :class="m.role">
            <span v-if="m.role === 'agent'" class="chat-avatar">{{ activeAgent.shortName }}</span>
            <div class="chat-msg"><p>{{ m.content }}</p></div>
          </div>
          <div v-if="busy" class="chat-row agent">
            <span class="chat-avatar">{{ activeAgent.shortName }}</span>
            <div class="chat-msg"><p>…</p></div>
          </div>
        </div>
        <div v-if="quickPrompts.length" class="chat-prompts">
          <button v-for="p in quickPrompts" :key="p" type="button" class="prompt-chip" @click="send(p)">{{ p }}</button>
        </div>
        <form class="chat-input" @submit.prevent="send()">
          <input v-model="draft" type="text" :placeholder="`和「${activeAgent.name}」聊两句…`" />
          <button type="submit" :disabled="!draft.trim() || busy">发送</button>
        </form>
        <p class="chat-note"><MockBadge source="demo" /> 内嵌演示对话 · 完整对话与结论产出仍在核心对话页</p>
      </div>

      <p v-if="!activeAgent" class="agents-note"><MockBadge source="demo" /> 能力池与状态为演示数据 · 点击卡片即可与对应智能体对话</p>
    </div>
  </section>
</template>

<style scoped>
.agents {
  padding: 64px 0;
  background: var(--color-bg);
  border-top: 1px solid var(--color-border);
}

.container { max-width: var(--content-max-width); margin: 0 auto; padding: 0 var(--page-gutter); }

.head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.head h2 { margin: 0 0 6px; font-size: 26px; font-weight: 800; color: var(--color-text-primary); }
.head p { margin: 0; color: var(--color-text-secondary); font-size: 14px; line-height: 1.6; }

.head-cta {
  flex: none;
  padding: 9px 18px;
  border: 1px solid var(--blueLine);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--blueD);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.head-cta:hover { background: var(--blueSoft); }

.agent-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  height: 100%;
  padding: 18px;
  overflow: hidden;
  text-align: left;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: transform var(--duration-base) var(--ease-standard), box-shadow var(--duration-base), border-color var(--duration-base);
}

.agent-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-card); border-color: var(--c); }

.swatch {
  position: absolute;
  top: -30px;
  right: -30px;
  width: 92px;
  height: 92px;
  border-radius: 50%;
  background: var(--cSoft);
  opacity: 0.6;
}

.card-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.no { color: var(--c); font-size: 12px; font-weight: 800; letter-spacing: 0.08em; }

.stage {
  padding: 2px 9px;
  border-radius: var(--radius-pill);
  background: var(--cSoft);
  color: var(--c);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.name { font-size: 17px; font-weight: 800; color: var(--color-text-primary); }

.role {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.boundary { color: var(--color-text-muted); font-size: 12.5px; }

.go { margin-top: auto; padding-top: 10px; color: var(--c); font-size: 13px; font-weight: 700; }

.agents-note { margin: 20px 0 0; text-align: center; color: var(--color-text-muted); font-size: 12.5px; }

/* 首页内嵌大对话框（点击卡片后原地切换） */
.chat-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  min-height: 400px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.chat-head {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--cSoft);
}

.chat-ico {
  display: grid;
  width: 34px;
  height: 34px;
  flex: none;
  place-items: center;
  border-radius: var(--radius-sm);
  background: var(--c);
  color: #fff;
  font-weight: 800;
}

.chat-meta { display: grid; gap: 1px; }
.chat-meta b { font-size: 14px; }
.chat-meta span { font-size: 12px; color: var(--color-text-secondary); }

.chat-stage {
  margin-left: auto;
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--c);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.chat-back {
  flex: none;
  padding: 5px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.chat-back:hover { color: var(--c); border-color: var(--c); }

.chat-body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  padding: 16px;
}

.chat-row { display: flex; align-items: flex-start; gap: 8px; }
.chat-row.user { justify-content: flex-end; }

.chat-avatar {
  flex: none;
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 50%;
  background: var(--c);
  color: #fff;
  font-size: 12px;
  font-weight: 800;
}

.chat-msg { max-width: 78%; }
.chat-msg p {
  margin: 0;
  padding: 9px 13px;
  border-radius: 14px;
  font-size: 13px;
  line-height: 1.6;
}

.chat-msg.agent p { background: var(--cSoft); border: 1px solid var(--color-border); border-top-left-radius: 4px; }
.chat-msg.user p { background: var(--c); color: #fff; border-top-right-radius: 4px; }

.chat-input {
  flex: none;
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--color-border);
}

.chat-input input {
  flex: 1;
  min-width: 0;
  padding: 9px 12px;
  border: 1px solid var(--c);
  border-radius: var(--radius-pill);
  background: #fff;
  font-size: 13px;
}

.chat-input button {
  padding: 9px 18px;
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--c);
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
}

.chat-input button:disabled { opacity: 0.5; cursor: default; }

.chat-prompts {
  flex: none;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 16px 12px;
}

.prompt-chip {
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--c);
  font-size: 12.5px;
  cursor: pointer;
}

.prompt-chip:hover { border-color: var(--c); background: var(--cSoft); }

.chat-note { flex: none; margin: 0; padding: 0 16px 12px; font-size: 12px; color: var(--color-text-muted); }

/* 每个智能体一个主题色（与智能体小队、对话页主理徽章同一套令牌） */
.a-blue { --c: var(--blue); --cSoft: var(--blueSoft); }
.a-green { --c: var(--greenD); --cSoft: var(--greenSoft); }
.a-amber { --c: var(--amber); --cSoft: var(--amberSoft); }
.a-violet { --c: var(--violet); --cSoft: var(--purpleSoft); }
.a-slate { --c: var(--color-text-secondary); --cSoft: var(--color-bg); }

@media (max-width: 1180px) {
  .agent-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

@media (max-width: 760px) {
  .head { align-items: flex-start; flex-direction: column; gap: 14px; }
  .agent-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 460px) {
  .agent-grid { grid-template-columns: minmax(0, 1fr); }
}
</style>

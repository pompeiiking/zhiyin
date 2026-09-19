<script setup lang="ts">
import { useRouter } from 'vue-router'

import { agentCatalog } from '@/stores/agents'

// 首页「五个智能体，各管一段」。
//
// ⚠️ 这里曾经内嵌一个"演示对话框"：开场白、回复、快捷提问全是本地写死的假内容，
//    点卡片就在首页演一段并不存在的对话。真实交互只在核心对话页发生，已全部删除；
//    现在点卡片直接进入该智能体的能力边界页。
const router = useRouter()

function openAgent(id: string) {
  void router.push({ name: 'agentDetail', params: { agentId: id } })
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

      <ul class="agent-grid">
        <li v-for="agent in agentCatalog" :key="agent.id" :class="agent.theme">
          <button class="agent-card" type="button" @click="openAgent(agent.id)">
            <span class="swatch" aria-hidden="true"></span>
            <span class="card-top">
              <span class="no" aria-hidden="true">{{ agent.no }}</span>
              <span class="stage">{{ agent.stages }}</span>
            </span>
            <span class="name">{{ agent.name }}</span>
            <span class="role">{{ agent.role }}</span>
            <span class="boundary">不做：{{ agent.boundary }}</span>
            <span class="go">看它管哪一段 →</span>
          </button>
        </li>
      </ul>

      <p class="agents-note">能力池来自动态资源；对话与结论产出只在核心对话页发生。</p>
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

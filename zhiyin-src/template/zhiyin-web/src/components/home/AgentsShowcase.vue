<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAgentCatalog } from '@/stores/agents'

// 首页「五个智能体，各管一段」。
//
// ⚠️ 这里曾经内嵌一个"演示对话框"：开场白、回复、快捷提问全是本地写死的假内容，
//    点卡片就在首页演一段并不存在的对话。真实交互只在核心对话页发生，已全部删除；
//    现在点卡片直接进入该智能体的能力边界页。
//
// 能力池定义来自 `GET /app/bootstrap` 的 agents（D9），前端不再硬编码五位智能体。
const router = useRouter()
const catalog = useAgentCatalog()

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
        <li v-for="agent in catalog" :key="agent.id" :class="agent.theme">
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

      <p class="agents-note">
        能力池当前由前端静态配置，与 <code>data/registry/agents.json</code> 同值；
        bootstrap 尚未下发该能力池，改由后端下发前两处需手工保持同步。
        对话与结论产出只在核心对话页发生。
      </p>
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

.chat-head {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--cSoft);
}
.chat-row.user { justify-content: flex-end; }

.chat-msg.agent p { background: var(--cSoft); border: 1px solid var(--color-border); border-top-left-radius: 4px; }
.chat-msg.user p { background: var(--c); color: #fff; border-top-right-radius: 4px; }

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

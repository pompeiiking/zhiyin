<script setup lang="ts">
import { useRouter } from 'vue-router'
import { agentCatalog } from '@/stores/agents'

// 智能体小队卡片组：轴 C 能力池的列表视图。
// 每张卡只回答「谁 / 管哪一段 / 什么状态」，点击进入该智能体的单智能体页看职责与边界；
// 本页与下级页都不做实时对话（§2.1、§4.8）。数据来源见 stores/agents.ts 的文件头说明。
const router = useRouter()

function openDetail(id: string) {
  void router.push({ name: 'agentDetail', params: { agentId: id } })
}
</script>

<template>
  <ul class="agent-grid">
    <li v-for="agent in agentCatalog" :key="agent.id" :class="agent.theme">
      <button class="agent-card" type="button" @click="openDetail(agent.id)">
        <span class="swatch" aria-hidden="true"></span>
        <span class="card-top">
          <span class="no" aria-hidden="true">{{ agent.no }}</span>
        </span>
        <span class="name">{{ agent.name }}</span>
        <span class="stage">{{ agent.stages }}</span>
        <span class="meta">
          <span class="boundary">{{ agent.boundary }}</span>
          <span class="tag-open">查看职责 →</span>
        </span>
      </button>
    </li>
  </ul>
</template>

<style scoped>
.agent-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-4);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-grid > li {
  display: flex;
}

.agent-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  width: 100%;
  min-height: 280px;
  flex: 1;
  padding: var(--space-6);
  overflow: hidden;
  text-align: left;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: transform var(--duration-base) var(--ease-standard), box-shadow var(--duration-base), border-color var(--duration-base);
}

.agent-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-card);
  border-color: var(--c);
}

.agent-card:active { transform: translateY(-1px); }

.swatch {
  position: absolute;
  top: -56px;
  right: -56px;
  width: 170px;
  height: 170px;
  border-radius: 50%;
  background: var(--cSoft);
  opacity: 0.55;
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.no { color: var(--c); font-size: var(--font-size-sm); font-weight: 800; letter-spacing: 0.08em; }

.name { font-size: var(--font-size-lg); font-weight: 800; line-height: 1.3; }

.stage {
  align-self: flex-start;
  padding: 4px 12px;
  border-radius: var(--radius-pill);
  background: var(--cSoft);
  color: var(--c);
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-top: auto;
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.tag-open { color: var(--c); font-weight: 700; white-space: nowrap; }

@media (max-width: 1180px) {
  .agent-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

@media (max-width: 760px) {
  .agent-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 460px) {
  .agent-grid { grid-template-columns: minmax(0, 1fr); }
  .agent-card { min-height: 0; }
}

/* 每个智能体一个主题色（与首页智能体区、对话页主理徽章同一套令牌） */
.a-blue { --c: var(--blue); --cSoft: var(--blueSoft); }
.a-green { --c: var(--greenD); --cSoft: var(--greenSoft); }
.a-amber { --c: var(--amber); --cSoft: var(--amberSoft); }
.a-violet { --c: var(--violet); --cSoft: var(--purpleSoft); }
.a-slate { --c: var(--color-text-secondary); --cSoft: var(--color-bg); }
</style>
<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AgentContextRail from '@/components/agents/AgentContextRail.vue'
import AgentScopePanel from '@/components/agents/AgentScopePanel.vue'
import { useAgentById } from '@/stores/agents'

// 单智能体页 #screen-subagent（功能块，挂在智能体小队主页下）
//
// 承载的轴：《职引-前端页面设计》§2.1——轴 C「能力与编排」的单点视图。
// 使命：看清这一位管哪一段、依据什么、当前产出什么，并在需要时请它接手。
// 明确不为它做：**不做实时对话**（实时交互只在核心对话页）、不产生平行资产、不另起一套结论。
const route = useRoute()
const router = useRouter()
const agentById = useAgentById()

const agentId = computed(() => String(route.params.agentId ?? ''))

function ensureKnownAgent() {
  if (!agentById(agentId.value)) void router.replace({ name: 'agents' })
}

onMounted(ensureKnownAgent)
watch(agentId, ensureKnownAgent)

function backToHub() {
  void router.push({ name: 'agents' })
}

function toConversation() {
  void router.push({ name: 'conversation' })
}
</script>

<template>
  <main data-anchor="screen-subagent" class="agent-page">
    <div class="container">
      <nav class="crumb" aria-label="面包屑">
        <button class="back" type="button" @click="backToHub">← 智能体小队</button>
        <span class="crumb-name">能力与边界</span>
        <button class="link" type="button" @click="toConversation">回到核心对话页</button>
      </nav>

      <div class="layout">
        <AgentScopePanel :key="agentId" :agent-id="agentId" />
        <AgentContextRail :key="agentId" :agent-id="agentId" />
      </div>
    </div>
  </main>
</template>

<style scoped>
.agent-page { padding: var(--space-6) 0 var(--space-10); background: var(--color-bg); }

.crumb { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-5); }

.back {
  padding: 7px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.back:hover { border-color: var(--blue); color: var(--blueD); }
.crumb-name { font-size: var(--font-size-sm); font-weight: 700; }
.link { margin-left: auto; border: 0; background: none; color: var(--color-link); font-size: var(--font-size-xs); font-weight: 700; text-decoration: underline; }

.layout { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: var(--space-6); align-items: start; }

@media (max-width: 1000px) {
  .layout { grid-template-columns: minmax(0, 1fr); }
}
</style>
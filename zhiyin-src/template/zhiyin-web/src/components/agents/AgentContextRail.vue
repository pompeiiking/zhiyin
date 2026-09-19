<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentById, useAgentCatalog } from '@/stores/agents'

// 单智能体页右栏：把这一位的「依据什么、不做什么、队友是谁」摆在主栏旁边。
// 口径来自 bootstrap 下发的 agents（能力池，源头是 data/registry/agents.json），
// 本组件不新增能力描述、也不硬编码任何智能体定义。
const props = defineProps<{ agentId: string }>()

const catalog = useAgentCatalog()
const agentById = useAgentById()
const router = useRouter()

const agent = computed(() => agentById(props.agentId))
const peers = computed(() => catalog.value.filter((item) => item.id !== props.agentId))

function switchTo(id: string) {
  void router.push({ name: 'agentDetail', params: { agentId: id } })
}
</script>

<template>
  <aside v-if="agent" class="context-rail" aria-label="这位智能体的职责与边界">
    <section class="card">
      <header><b>依据什么</b></header>
      <div class="block">
        <span class="label">理论包</span>
        <ul v-if="agent.theories.length" class="tags">
          <li v-for="theory in agent.theories" :key="theory">{{ theory }}</li>
        </ul>
        <p v-else class="muted">无理论包，只按需供给外部事实。</p>
      </div>
      <div class="block">
        <span class="label">工具</span>
        <p>{{ agent.tools.join(' · ') }}</p>
      </div>
    </section>

    <section class="card">
      <header><b>同一小队的其他成员</b></header>
      <ul class="peers">
        <li v-for="peer in peers" :key="peer.id">
          <button type="button" @click="switchTo(peer.id)">
            <span :class="`dot ${peer.theme}`" aria-hidden="true">{{ peer.shortName }}</span>
            <span class="peer-copy">
              <b>{{ peer.name }}</b>
              <small>{{ peer.stages }}</small>
            </span>
          </button>
        </li>
      </ul>
    </section>
  </aside>
</template>

<style scoped>
.context-rail { display: grid; gap: var(--space-4); align-content: start; }

.card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.card header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg);
}

.card header b { font-size: var(--font-size-sm); font-weight: 800; }

.block { padding: var(--space-3) var(--space-4); }

.block + .block { border-top: 1px solid var(--color-border); }

.label { display: block; margin-bottom: 5px; color: var(--blueD); font-size: var(--font-size-xs); font-weight: 800; letter-spacing: 0.06em; }

.block p { margin: 0; color: var(--color-text-secondary); font-size: var(--font-size-xs); line-height: 1.7; }
.block p.muted { color: var(--color-text-muted); }

.tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 0; padding: 0; list-style: none; }

.tags li {
  padding: 3px 9px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

.peers { display: grid; gap: 0; margin: 0; padding: 0 var(--space-2) var(--space-3); list-style: none; }

.peers button {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-3);
  border: 0;
  border-radius: var(--radius-sm);
  background: none;
  text-align: left;
}

.peers button:hover { background: var(--color-bg); }

.peers .dot {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: none;
  border-radius: var(--radius-sm);
  background: var(--c);
  color: #fff;
  font-size: var(--font-size-xs);
  font-weight: 800;
}

.peer-copy { display: grid; gap: 2px; min-width: 0; }
.peer-copy b { font-size: var(--font-size-sm); font-weight: 700; color: var(--color-text-primary); }
.peer-copy small { color: var(--color-text-muted); font-size: var(--font-size-xs); }

.a-blue { --c: var(--blue); }
.a-green { --c: var(--greenD); }
.a-amber { --c: var(--amber); }
.a-violet { --c: var(--violet); }
.a-slate { --c: var(--color-text-secondary); }
</style>

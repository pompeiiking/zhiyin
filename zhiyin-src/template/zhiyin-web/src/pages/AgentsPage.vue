<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AgentTeamGrid from '@/components/agents/AgentTeamGrid.vue'
import type { ProfilePanelView } from '@/api/schema'
import { useWorkspaceStore } from '@/stores/workspace'

// 智能体小队主页 #screen-agents（功能块，不占主线导航）
//
// 承载的轴：《职引-前端页面设计》§2.1——轴 C「能力与编排」的可见投影。
// 使命：让用户看清「当前是谁在帮我、各管哪一段」。
// 明确不为它做：不做能力陈列墙、不堆模型与能力数字；**不做实时对话**——对话与结论产出只在
// 核心对话页发生（§2.1），本页与单智能体页只做能力与边界的可见化。
//
// 画像数字直接读 `GET /app/workspace` 的真实面板；不再在这里合成"15 维解析"状态。
const router = useRouter()
const store = useWorkspaceStore()

const profile = computed(() => store.profilePanel as unknown as ProfilePanelView | null)
const coverageText = computed(() =>
  profile.value ? `${Math.round((profile.value.coverage ?? 0) * 100)}%` : '—',
)
const confidenceText = computed(() =>
  profile.value ? (profile.value.overall_confidence ?? 0).toFixed(2) : '—',
)

function toConversation() {
  void router.push({ name: 'conversation' })
}

function toReport() {
  void router.push({ name: 'report' })
}

onMounted(() => {
  void store.load()
})
</script>

<template>
  <main data-anchor="screen-agents" class="hub">
    <div class="container">
      <section class="hub-head">
        <div>
          <h1>你的画像已就绪，五个智能体各管一段</h1>
          <p>采集、诊断、决策、行动、复盘各有主理，共用同一份画像与结论。点开卡片看它管哪一段、边界在哪。</p>
        </div>
        <aside>
          <div class="aside-row"><small>画像覆盖</small><b>{{ coverageText }}</b></div>
          <div class="aside-row"><small>整体置信度</small><b>{{ confidenceText }}</b></div>
          <button class="aside-link" type="button" @click="toConversation">回到核心对话页 →</button>
        </aside>
      </section>

      <p v-if="store.error" class="summary empty" role="alert">画像加载失败：{{ store.error }}</p>

      <section v-else class="summary" aria-label="环节产出">
        <div class="summary-main">
          <h2>各环节产出以真实资产为准</h2>
          <p>诊断、决策、行动三段的产出都在核心对话页完成，并写回同一份资产；这里不预置任何结论。</p>
        </div>
        <button class="act ghost" type="button" @click="toReport">查看完整报告 →</button>
      </section>

      <AgentTeamGrid />

      <footer class="hub-foot">
        <p>能力池由前端静态配置（与 <code>data/registry/agents.json</code> 同值，尚未由 bootstrap 下发）· 对话与结论产出只在核心对话页发生 · 五位共用同一份画像与资产，换主理不换结论。</p>
      </footer>
    </div>
  </main>
</template>

<style scoped>
.hub { padding: var(--space-8) 0 var(--space-12); background: var(--color-bg); }

.hub-head { display: grid; grid-template-columns: minmax(0, 1fr) 236px; gap: var(--space-8); align-items: end; padding-bottom: var(--space-6); }
.hub-head h1 { max-width: 720px; margin: var(--space-3) 0; font-size: clamp(1.75rem, 3.2vw, 2.5rem); line-height: 1.22; letter-spacing: -0.02em; }
.hub-head p { max-width: 640px; margin: 0; color: var(--color-text-secondary); font-size: var(--font-size-sm); line-height: 1.75; }

.hub-head aside { padding: var(--space-4); border: 1px solid var(--blueLine); border-radius: var(--radius-lg); background: linear-gradient(135deg, var(--blueSoft), var(--card)); }
.aside-row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); font-size: var(--font-size-xs); }
.aside-row + .aside-row { margin-top: var(--space-2); }
.aside-row small { color: var(--color-text-muted); }
.aside-row b { color: var(--blueD); font-size: var(--font-size-sm); }
.aside-row b.ok { color: var(--greenD); }
.aside-link { width: 100%; margin-top: var(--space-3); padding-top: var(--space-3); border: 0; border-top: 1px solid var(--blueLine); background: none; color: var(--blueD); font-size: var(--font-size-xs); font-weight: 700; text-align: left; }

.summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  margin-bottom: var(--space-6);
  padding: var(--space-5);
  border: 1px solid var(--color-success-border);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--greenSoft), var(--card));
}

.summary.empty { border-color: var(--blueLine); background: linear-gradient(135deg, var(--blueSoft), var(--card)); }
.summary-main h2 { margin: var(--space-2) 0 0; font-size: var(--font-size-md); }
.summary-main p { margin: var(--space-2) 0 0; color: var(--color-text-secondary); font-size: var(--font-size-xs); }

.act {
  flex: none;
  padding: 11px 20px;
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--blueD);
  color: #fff;
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.act.ghost { background: var(--card); border: 1px solid var(--color-success-border); color: var(--greenD); }
.act:hover { filter: brightness(1.05); }

.hub-foot { margin-top: var(--space-8); border-top: 1px solid var(--color-border); padding-top: var(--space-5); }
.hub-foot p { margin: 0; color: var(--color-text-muted); font-size: var(--font-size-xs); line-height: 1.7; }

@media (max-width: 900px) {
  .hub-head { grid-template-columns: minmax(0, 1fr); gap: var(--space-5); }
  .summary { align-items: stretch; flex-direction: column; }
}
</style>
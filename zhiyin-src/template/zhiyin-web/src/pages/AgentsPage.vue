<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import AgentTeamGrid from '@/components/agents/AgentTeamGrid.vue'
import MockBadge from '@/components/common/MockBadge.vue'
import { useProfileCoverage } from '@/composables'
import { useAgentsStore } from '@/stores/agents'

// 智能体小队主页 #screen-agents（功能块，不占主线导航）
//
// 承载的轴：《职引-前端页面设计》§2.1——轴 C「能力与编排」的可见投影。
// 使命：让用户看清「当前是谁在帮我、各管哪一段」，并在需要时召唤某一位继续微循环。
// 明确不为它做：不做能力陈列墙、不堆模型与能力数字；**不做实时对话**——对话与结论产出只在
// 核心对话页发生（§2.1），本页与单智能体页只做能力与边界的可见化。
const router = useRouter()
const agents = useAgentsStore()
const { coverageText, confidenceText } = useProfileCoverage()
const analysisDone = computed(() => agents.analysisStatus === 'done')
const groups = computed(() => agents.analysisGroups)

const summary = computed(() => [
  { label: '强项', value: groups.value.strong.length },
  { label: '机会', value: groups.value.option.length },
  { label: '待补', value: groups.value.gap.length },
  { label: '风险', value: groups.value.risk.length },
])

function toConversation() {
  void router.push({ name: 'conversation' })
}

function toReport() {
  void router.push({ name: 'report' })
}
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
          <div class="aside-row"><small>15 维解析</small><b :class="{ ok: analysisDone }">{{ analysisDone ? '已完成' : '未生成' }}</b></div>
          <button class="aside-link" type="button" @click="toConversation">回到核心对话页 →</button>
        </aside>
      </section>

      <section v-if="analysisDone" class="summary" aria-label="解析结论摘要">
        <div class="summary-main">
          <h2>解析已完成，可按环节找人接手</h2>
          <ul class="chips">
            <li v-for="item in summary" :key="item.label"><b>{{ item.value }}</b>{{ item.label }}</li>
          </ul>
        </div>
        <button class="act ghost" type="button" @click="toReport">查看完整解析 →</button>
      </section>

      <section v-else class="summary empty" aria-label="解析状态">
        <div class="summary-main">
          <h2>解析还没生成</h2>
          <p>回对话页完成建档即可生成（当前覆盖 {{ coverageText }} · 置信度 {{ confidenceText }}）。</p>
        </div>
        <button class="act" type="button" @click="toConversation">回对话页生成解析 →</button>
      </section>

      <AgentTeamGrid />

      <footer class="hub-foot">
        <p><MockBadge source="demo" /> 能力池与状态为演示数据 · 对话与结论产出只在核心对话页发生 · 五位共用同一份画像与资产，换主理不换结论。</p>
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

.chips { display: flex; flex-wrap: wrap; gap: var(--space-2); margin: var(--space-3) 0 0; padding: 0; list-style: none; }
.chips li { display: inline-flex; align-items: baseline; gap: 5px; padding: 4px 11px; border: 1px solid var(--color-border); border-radius: var(--radius-pill); background: var(--card); font-size: var(--font-size-xs); color: var(--color-text-secondary); }
.chips li b { color: var(--color-text-primary); font-size: var(--font-size-sm); }

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
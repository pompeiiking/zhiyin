<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { useAgentsStore } from '@/stores/agents'
import { useConversationStore } from '@/stores/conversation'
import { useWorkspaceStore } from '@/stores/workspace'

// 单智能体页主栏（#screen-subagent）：把这一位「是谁 / 管哪一段 / 产出什么 / 如何接手」摊开。
// 本页不做实时对话——实时交互只发生在核心对话页；stores/agents.ts::summon 只写换主理告知，不产生平行资产。
const props = defineProps<{ agentId: string }>()

const router = useRouter()
const agents = useAgentsStore()
const conversation = useConversationStore()
const workspace = useWorkspaceStore()

const agent = computed(() => agents.agentById(props.agentId))

/** 全环节按需调用（如信息侦查员）：不在某一段主理。 */
const onDemand = computed(() => (agent.value?.stageCodes ?? []).length === 0)

const STATUS_LABEL: Record<string, string> = {
  done: '已完成',
  in_progress: '进行中',
  empty: '未开始',
}

/** 该智能体负责的环节（阶段名 + 状态 + 该环节产出，状态与产出直接读管线卡）。 */
const stages = computed(() => {
  const codes = agent.value?.stageCodes ?? []
  const pipeline = conversation.pipeline as Array<Record<string, unknown>>
  return pipeline
    .filter((card) => codes.includes(String(card.stage)))
    .map((card) => ({
      stage: String(card.stage),
      title: String(card.title ?? ''),
      status: String(card.status ?? 'empty'),
      statusLabel: STATUS_LABEL[String(card.status ?? 'empty')] ?? '未开始',
      output: Object.entries((card.current_output ?? {}) as Record<string, string>),
    }))
})

const stageProgress = computed(() => ({
  done: stages.value.filter((s) => s.status === 'done').length,
  total: stages.value.length,
}))

/** 该智能体负责环节对应的资产产出：产出的是「结果」——一份画像 / 报告 / 方案 / 计划 / 复盘 */
const producedAssets = computed(() => {
  const codes = agent.value?.stageCodes ?? []
  const assets: Array<{ key: string; label: string; version: string; summary: string; detail: string | null }> = []

  if (codes.includes('collect')) {
    const p = workspace.profilePanel as Record<string, unknown> | null
    assets.push({
      key: 'profile',
      label: '个人画像',
      version: `覆盖 ${Math.round(Number(p?.coverage ?? 0) * 100)}% · 置信 ${Math.round(Number(p?.overall_confidence ?? 0) * 100)}%`,
      summary: '学业、技能维度已沉淀；兴趣、价值观待补全',
      detail: null,
    })
  }
  if (codes.includes('diagnose')) {
    const r = workspace.reportPanel as Record<string, unknown> | null
    assets.push({
      key: 'report',
      label: '诊断报告',
      version: `v${r?.version ?? 1} · ${String(r?.updated_at ?? '')}`,
      summary: String(r?.evaluation ?? ''),
      detail: r?.diff ? String(r.diff) : null,
    })
  }
  if (codes.includes('decide')) {
    const d = workspace.planPanel as Record<string, unknown> | null
    assets.push({
      key: 'plan',
      label: '方向方案',
      version: `v${d?.version ?? 1} · ${String(d?.updated_at ?? '')}`,
      summary: String(d?.evaluation ?? ''),
      detail: null,
    })
  }
  if (codes.includes('act')) {
    const a = workspace.actionPanel as Record<string, unknown> | null
    assets.push({
      key: 'action',
      label: '行动计划',
      version: `v${a?.version ?? 1} · ${String(a?.updated_at ?? '')}`,
      summary: String(a?.evaluation ?? ''),
      detail: null,
    })
  }
  if (codes.includes('review')) {
    const rv = workspace.reviewPanel as Record<string, unknown> | null
    assets.push({
      key: 'review',
      label: '行为日志 · 复盘',
      version: `v${rv?.version ?? 1} · ${String(rv?.updated_at ?? '')}`,
      summary: String(rv?.evaluation ?? ''),
      detail: null,
    })
  }
  return assets
})

function summon() {
  // 只做跳转：真正的换主理由编排器在下一轮对话里判定并下发 Disclosure。
  // 曾经这里会在前端直接改写徽章与告知行，等于伪造一次并未发生的交接。
  void router.push({ name: 'conversation' })
}
</script>

<template>
  <section v-if="agent" class="scope" :class="agent.theme">
    <header class="hero">
      <span class="hero-mark" aria-hidden="true">{{ agent.shortName }}</span>
      <div class="hero-copy">
        <div class="hero-line">
          <h1>{{ agent.name }}</h1>
          <span class="status" :class="`is-${agent.statusTone}`">{{ agent.stages }}</span>
        </div>
        <p class="hero-role">{{ agent.role }}</p>
        <div class="hero-foot">
          <div v-if="onDemand" class="hero-stages">
            <span class="stage-pill is-ondemand">按需调用 · 不主理某一段</span>
          </div>
          <template v-else>
            <div class="hero-stages">
              <span v-for="s in stages" :key="s.title" class="stage-pill" :class="`is-${s.status}`">{{ s.title }}</span>
            </div>
            <span class="hero-progress">已完成 {{ stageProgress.done }}/{{ stageProgress.total }}</span>
          </template>
        </div>
      </div>
    </header>

    <section class="block" aria-label="它负责的环节">
      <h2 class="block-title">它负责的环节</h2>
      <p v-if="onDemand" class="muted">不在某一段主理：任一环节需要外部事实时按需调用。</p>
      <ul v-else class="stage-cards">
        <li v-for="item in stages" :key="item.stage" class="stage-card" :class="`is-${item.status}`">
          <div class="stage-top">
            <span class="stage-dot" :class="`is-${item.status}`" aria-hidden="true"></span>
            <b>{{ item.title }}</b>
            <span class="stage-status" :class="`is-${item.status}`">{{ item.statusLabel }}</span>
          </div>
          <ul v-if="item.output.length" class="kv">
            <li v-for="[key, value] in item.output" :key="key"><small>{{ key }}</small><b>{{ value }}</b></li>
          </ul>
          <p v-else class="muted">这一环还没有产出。</p>
        </li>
      </ul>
    </section>

    <section class="block" aria-label="当前产出">
      <h2 class="block-title">当前产出</h2>
      <div v-if="producedAssets.length" class="produced">
        <div v-for="asset in producedAssets" :key="asset.key" class="produced-card">
          <div class="produced-head">
            <b class="produced-label">{{ asset.label }}</b>
            <span class="produced-version">{{ asset.version }}</span>
          </div>
          <p class="produced-summary">{{ asset.summary }}</p>
          <p v-if="asset.detail" class="produced-diff">{{ asset.detail }}</p>
        </div>
      </div>
      <p v-else class="muted">这一环还没有产出，回核心对话页走完当前环节后写回这里。</p>
    </section>

    <section class="summon">
      <div>
        <h2>要它接手，回核心对话页</h2>
        <p class="muted">是否交接由编排器按环节判定，并在一轮对话里显式告知；前端不自行改写主理徽章。</p>
      </div>
      <button class="act" type="button" @click="summon">去核心对话页继续 →</button>
    </section>

    <footer class="scope-foot">
      <p>能力池来自动态资源；环节状态与产出取当前账号的真实资产，未产出即显示为空。</p>
    </footer>
  </section>
  <p v-else class="fallback">没有找到这个智能体，正在返回智能体小队…</p>
</template>

<style scoped>
.scope { display: grid; gap: var(--space-5); align-content: start; }

/* 身份卡 */
.hero {
  position: relative;
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: var(--space-5);
  align-items: center;
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--cSoft), var(--color-surface) 58%);
  overflow: hidden;
}

.hero::after {
  content: '';
  position: absolute;
  top: -60px;
  right: -60px;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: var(--cSoft);
  opacity: 0.5;
}

.hero-mark {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 72px;
  height: 72px;
  border-radius: var(--radius-md);
  background: var(--c);
  color: #fff;
  font-size: var(--font-size-xl);
  font-weight: 800;
  box-shadow: 0 12px 26px rgba(0, 0, 0, 0.16);
}

.hero-copy { position: relative; z-index: 1; min-width: 0; }

.hero-line { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.hero-line h1 { margin: 0; font-size: var(--font-size-xl); line-height: 1.2; letter-spacing: -0.01em; }

.hero-role { margin: 8px 0 0; color: var(--color-text-secondary); font-size: var(--font-size-sm); line-height: 1.7; }

.hero-foot { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-3); }

.hero-stages { display: flex; flex-wrap: wrap; gap: 6px; }

.stage-pill {
  padding: 4px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.stage-pill.is-done { border-color: var(--greenD); color: var(--greenD); background: var(--greenSoft); }
.stage-pill.is-in_progress { border-color: var(--amber); color: var(--amber); background: var(--amberSoft); }
.stage-pill.is-empty { color: var(--color-text-muted); }
.stage-pill.is-ondemand { border-color: var(--c); color: var(--c); background: var(--cSoft); }

.hero-progress { font-size: var(--font-size-xs); font-weight: 600; color: var(--color-text-muted); }

.status { padding: 4px 11px; border-radius: var(--radius-pill); font-size: var(--font-size-xs); font-weight: 700; white-space: nowrap; }
.status.is-done { color: var(--greenD); background: var(--greenSoft); }
.status.is-active { color: var(--amber); background: var(--amberSoft); }
.status.is-sync { color: var(--color-text-secondary); background: var(--color-bg); }
.status.is-ondemand { color: var(--blueD); background: var(--blueSoft); }

/* 产出 */
.block {
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.block-title { margin: 0 0 var(--space-4); font-size: var(--font-size-md); }
.muted { color: var(--color-text-muted); }

.stage-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: var(--space-3); margin: 0; padding: 0; list-style: none; }

.stage-card {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.stage-top { display: flex; align-items: center; gap: var(--space-2); }

.stage-dot { width: 8px; height: 8px; flex: none; border-radius: 50%; background: var(--color-text-muted); }
.stage-dot.is-done { background: var(--greenD); }
.stage-dot.is-in_progress { background: var(--amber); }
.stage-dot.is-empty { background: var(--color-text-muted); }

.stage-top b { font-size: var(--font-size-sm); }

.stage-status { margin-left: auto; font-size: var(--font-size-xs); font-weight: 700; }
.stage-status.is-done { color: var(--greenD); }
.stage-status.is-in_progress { color: var(--amber); }
.stage-status.is-empty { color: var(--color-text-muted); }

.kv { display: flex; flex-wrap: wrap; gap: var(--space-2); margin: var(--space-3) 0 0; padding: 0; list-style: none; }

.kv li {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  font-size: var(--font-size-xs);
}

.kv small { color: var(--color-text-muted); }
.kv b { color: var(--color-text-primary); font-size: var(--font-size-xs); }

.produced { display: grid; gap: var(--space-3); }

.produced-card {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.produced-head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); margin-bottom: 6px; }
.produced-label { color: var(--c); font-size: var(--font-size-xs); font-weight: 800; letter-spacing: 0.05em; }
.produced-version { color: var(--color-text-muted); font-size: var(--font-size-xs); white-space: nowrap; }
.produced-summary { margin: 0; color: var(--color-text-primary); font-size: var(--font-size-sm); font-weight: 600; line-height: 1.7; }
.produced-diff { margin: 10px 0 0; padding: 8px 12px; border-left: 3px solid var(--c); border-radius: var(--radius-sm); background: var(--cSoft); color: var(--color-text-secondary); font-size: var(--font-size-xs); line-height: 1.7; }

/* 召唤 */
.summon {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--cSoft), var(--color-surface) 70%);
}

.summon h2 { margin: 0 0 6px; font-size: var(--font-size-md); }
.summon p { margin: 0; font-size: var(--font-size-xs); line-height: 1.7; }

.act {
  flex: none;
  padding: 12px 22px;
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--c);
  color: #fff;
  font-size: var(--font-size-sm);
  font-weight: 700;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.12);
}

.act:hover { filter: brightness(1.06); }

.scope-foot { border-top: 1px solid var(--color-border); padding-top: var(--space-4); }
.scope-foot p { margin: 0; color: var(--color-text-muted); font-size: var(--font-size-xs); line-height: 1.7; }

.fallback { color: var(--color-text-muted); font-size: var(--font-size-sm); }

@media (max-width: 640px) {
  .hero { grid-template-columns: 48px minmax(0, 1fr); gap: var(--space-4); }
  .hero-mark { width: 48px; height: 48px; font-size: var(--font-size-lg); }
  .summon { flex-direction: column; align-items: stretch; }
  .act { width: 100%; }
}

/* 每个智能体一个主题色（与首页智能体区、对话页主理徽章同一套令牌） */
.a-blue { --c: var(--blue); --cSoft: var(--blueSoft); }
.a-green { --c: var(--greenD); --cSoft: var(--greenSoft); }
.a-amber { --c: var(--amber); --cSoft: var(--amberSoft); }
.a-violet { --c: var(--violet); --cSoft: var(--purpleSoft); }
.a-slate { --c: var(--color-text-secondary); --cSoft: var(--color-bg); }
</style>

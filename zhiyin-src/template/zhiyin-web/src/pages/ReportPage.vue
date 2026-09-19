<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { ReportFullTextView } from '@/api/schema'
import { exportAsset, getReportFullText, trackEvent } from '@/api/endpoints'
import { useSessionStore } from '@/stores/session'
import ReportToc from '@/components/report/ReportToc.vue'

// 完整报告页 #screen-report（P0，挂在工作台资产上）
//
// 口径（前端设计文档 §4.4）：左侧目录导航 + 全文区块 + 导出操作。
// 报告内容来自 `GET /app/report/full-text`（只读资产版本，不重新生成）。
//
// ⚠️ 本页曾内联了一整份演示报告（含编造的方向方案、行动计划、画像条目、报告编号与
//    本地导出实现），以及一份前端合成的 15 维分数。这些都不是后端产出，已全部删除：
//    拿不到就显示空态，不再用近似内容顶替。
const session = useSessionStore()

const report = ref<ReportFullTextView | null>(null)
const loading = ref(true)
const error = ref('')
const activeId = ref('')
const exportNotice = ref('')
const exporting = ref(false)

// 导出入口的可见性由动态资源的功能开关决定（`feature_flags.export`），
// 与「前端按开关决定功能块可见性」的口径一致。开关关闭时**不给按钮**，
// 但明确说明原因，而不是让用户点了才发现不可用。
const canExport = computed(() => session.featureFlags.export === true)

const toc = computed(() => (report.value?.toc ?? []) as Array<Record<string, unknown>>)
const sections = computed(() => (report.value?.sections ?? []) as Array<Record<string, unknown>>)

function sectionById(id: string): Record<string, unknown> | null {
  return sections.value.find((item) => String(item.id) === id) ?? null
}

const verdict = computed(() => {
  const section = sectionById('verdict')
  const content = (section?.content ?? {}) as Record<string, unknown>
  return {
    title: String(content.title ?? section?.title ?? ''),
    summary: String(content.summary ?? ''),
  }
})

const swot = computed(() => {
  const content = (sectionById('swot')?.content ?? {}) as Record<string, unknown>
  const pick = (key: string) =>
    Array.isArray(content[key]) ? (content[key] as unknown[]).map((item) => String(item)) : []
  return {
    strength: pick('strength'),
    weakness: pick('weakness'),
    opportunity: pick('opportunity'),
    risk: pick('risk'),
  }
})
const swotEmpty = computed(
  () =>
    !swot.value.strength.length &&
    !swot.value.weakness.length &&
    !swot.value.opportunity.length &&
    !swot.value.risk.length,
)

interface DimensionItem {
  name: string
  tag: string
  conclusion: string
  evidence: string
}
interface DimensionGroup {
  id: string
  group: string
  method: string
  items: DimensionItem[]
}

const dimensionGroups = computed<DimensionGroup[]>(() =>
  sections.value
    .filter((item) => String(item.id).startsWith('dimension-'))
    .map((item) => {
      const content = (item.content ?? {}) as Record<string, unknown>
      const rawItems = Array.isArray(content.items) ? (content.items as Array<Record<string, unknown>>) : []
      return {
        id: String(item.id),
        group: String(content.group ?? item.title ?? ''),
        method: String(content.group_method ?? ''),
        items: rawItems.map((entry) => ({
          name: String(entry.name ?? ''),
          tag: String(entry.tag ?? ''),
          conclusion: String(entry.conclusion ?? ''),
          evidence: String(entry.evidence ?? ''),
        })),
      }
    })
    .filter((group) => group.items.length > 0),
)

interface PlanGap {
  requirement: string
  current_state: string
  suggestion: string
}
interface DirectionPlan {
  id: string
  role: string
  name: string
  target_desc: string
  match_score: number
  gaps: PlanGap[]
  fit_reason: string
  main_risk: string
  selected: boolean
}

const ROLE_LABELS: Record<string, string> = {
  main: '主攻',
  parallel: '平行',
  fallback: '保底',
}

/** ③ 方向方案：与画像/报告同属活资产，由 `report/full-text` 一并下发。 */
const directions = computed<DirectionPlan[]>(() => {
  const content = (sectionById('directions')?.content ?? {}) as Record<string, unknown>
  const raw = Array.isArray(content.plans) ? (content.plans as Array<Record<string, unknown>>) : []
  return raw.map((plan) => ({
    id: String(plan.id ?? ''),
    role: String(plan.role ?? ''),
    name: String(plan.name ?? ''),
    target_desc: String(plan.target_desc ?? ''),
    match_score: Number(plan.match_score ?? 0),
    gaps: (Array.isArray(plan.gaps) ? (plan.gaps as Array<Record<string, unknown>>) : []).map(
      (gap) => ({
        requirement: String(gap.requirement ?? ''),
        current_state: String(gap.current_state ?? ''),
        suggestion: String(gap.suggestion ?? ''),
      }),
    ),
    fit_reason: String(plan.fit_reason ?? ''),
    main_risk: String(plan.main_risk ?? ''),
    selected: Boolean(plan.selected),
  }))
})

interface ActionTask {
  text: string
  due_date: string | null
  done: boolean
}
interface ActionPhase {
  name: string
  date_range: string
  tag: string
  tasks: ActionTask[]
}

/** ④ 行动计划：同样属于活资产。 */
const actionPhases = computed<ActionPhase[]>(() => {
  const content = (sectionById('action')?.content ?? {}) as Record<string, unknown>
  const raw = Array.isArray(content.phases) ? (content.phases as Array<Record<string, unknown>>) : []
  return raw.map((phase) => ({
    name: String(phase.name ?? ''),
    date_range: String(phase.date_range ?? ''),
    tag: String(phase.tag ?? ''),
    tasks: (Array.isArray(phase.tasks) ? (phase.tasks as Array<Record<string, unknown>>) : []).map(
      (task) => ({
        text: String(task.text ?? ''),
        due_date: task.due_date ? String(task.due_date) : null,
        done: Boolean(task.done),
      }),
    ),
  }))
})

function roleLabel(role: string): string {
  return ROLE_LABELS[role] ?? role
}

function matchPercent(score: number): string {
  return `${Math.round(score * 100)}%`
}

/** 已单独渲染的章节，其余章节走通用列表渲染。 */
const RENDERED_IDS = new Set(['verdict', 'swot', 'directions', 'action'])
const otherSections = computed(() =>
  sections.value.filter(
    (item) => !RENDERED_IDS.has(String(item.id)) && !String(item.id).startsWith('dimension-'),
  ),
)

async function load() {
  loading.value = true
  try {
    const data = await getReportFullText()
    report.value = data?.report_id ? data : null
    error.value = ''
    if (report.value && toc.value.length) activeId.value = String(toc.value[0].id ?? '')
  } catch (err) {
    report.value = null
    // 404「尚未生成诊断报告」是正常状态，不是故障；如实显示空态。
    error.value = err instanceof Error ? err.message : '报告加载失败'
  } finally {
    loading.value = false
  }
}

function selectSection(id: string) {
  activeId.value = id
}

function scrollTo(id: string) {
  activeId.value = id
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function onExport(format: 'pdf' | 'docx') {
  if (exporting.value) return
  exporting.value = true
  exportNotice.value = ''
  try {
    const result = await exportAsset('report', format)
    exportNotice.value = result?.available
      ? `导出已生成：${String(result.object_key ?? '')}`
      : String(result?.message ?? '后端暂未提供导出文件')
  } catch (err) {
    exportNotice.value = `导出失败：${err instanceof Error ? err.message : '未知错误'}`
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  void load()
  void trackEvent('diagnosis_view', { source: 'report' }).catch(() => {})
})
</script>

<template>
  <main data-anchor="screen-report" class="report-page">
    <div class="rp-container">
      <header class="rp-head">
        <div>
          <h1>完整报告</h1>
          <p v-if="report">
            第 {{ report.version }} 版 · 生成于 {{ report.generated_at }} · 只读资产视图
          </p>
          <p v-else>只读资产视图 · 尚未生成报告</p>
        </div>
        <div class="rp-actions">
          <template v-if="canExport">
            <button class="export-btn export-btn--ghost" type="button" :disabled="exporting" @click="onExport('pdf')">
              导出 PDF
            </button>
            <button class="export-btn" type="button" :disabled="exporting" @click="onExport('docx')">
              导出 Word
            </button>
          </template>
          <span v-else class="rp-export-off">导出功能未开放</span>
        </div>
      </header>

      <p v-if="exportNotice" class="rp-notice" role="status">{{ exportNotice }}</p>

      <p v-if="loading" class="rp-empty">正在加载报告…</p>

      <p v-else-if="!report" class="rp-empty">
        尚未生成诊断报告。完成①采集并进入②诊断后，报告正文会显示在这里。
        <span v-if="error" class="rp-empty-detail">（{{ error }}）</span>
      </p>

      <div v-else class="rp-layout">
        <ReportToc :items="toc" :active-id="activeId" @select="selectSection" />
        <div class="rp-sections">
          <section id="verdict" class="rp-verdict">
            <div class="vd-top">
              <span class="vd-eyebrow">诊断结论</span>
              <b class="vd-score">第 {{ report.version }} 版</b>
            </div>
            <h2 class="vd-title">{{ verdict.title || '诊断结论' }}</h2>
            <p class="vd-summary">{{ verdict.summary || '报告未提供结论摘要。' }}</p>

            <div class="vd-swot">
              <div v-if="swotEmpty" class="rp-empty">报告未提供 SWOT 内容。</div>
              <template v-else>
                <div class="swot-cell strong">
                  <b>优势</b>
                  <p v-for="(item, index) in swot.strength" :key="`s${index}`">{{ item }}</p>
                </div>
                <div class="swot-cell gap">
                  <b>待补</b>
                  <p v-for="(item, index) in swot.weakness" :key="`w${index}`">{{ item }}</p>
                </div>
                <div class="swot-cell option">
                  <b>机会</b>
                  <p v-for="(item, index) in swot.opportunity" :key="`o${index}`">{{ item }}</p>
                </div>
                <div class="swot-cell risk">
                  <b>风险</b>
                  <p v-for="(item, index) in swot.risk" :key="`r${index}`">{{ item }}</p>
                </div>
              </template>
            </div>
          </section>

          <section
            v-for="group in dimensionGroups"
            :id="group.id"
            :key="group.id"
            class="rp-block"
          >
            <div class="rp-block-head">
              <h2 class="rp-block-title">{{ group.group }}</h2>
              <span v-if="group.method" class="rp-block-method">{{ group.method }}</span>
            </div>
            <ul class="rp-items">
              <li v-for="(item, index) in group.items" :key="index" class="rp-item">
                <div class="rp-item-head">
                  <b class="rp-item-name">{{ item.name }}</b>
                  <span v-if="item.tag" class="rp-item-tag">{{ item.tag }}</span>
                </div>
                <p class="rp-item-text">{{ item.conclusion }}</p>
                <p v-if="item.evidence" class="rp-item-evidence">依据：{{ item.evidence }}</p>
              </li>
            </ul>
          </section>

          <section v-if="directions.length" id="directions" class="rp-block">
            <h2 class="rp-block-title">方向方案</h2>
            <ul class="rp-items">
              <li v-for="plan in directions" :key="plan.id" class="rp-item">
                <div class="rp-item-head">
                  <span class="rp-item-tag">{{ roleLabel(plan.role) }}</span>
                  <b class="rp-item-name">{{ plan.name }}</b>
                  <span class="rp-item-score">{{ matchPercent(plan.match_score) }} 匹配</span>
                  <span v-if="plan.selected" class="rp-item-chosen">已选定</span>
                </div>
                <p class="rp-item-text">{{ plan.target_desc }}</p>
                <p class="rp-item-evidence">契合依据：{{ plan.fit_reason }}</p>
                <p class="rp-item-risk">主要风险：{{ plan.main_risk }}</p>
                <ul v-if="plan.gaps.length" class="rp-gaps">
                  <li v-for="(gap, index) in plan.gaps" :key="index">
                    {{ gap.requirement }} → 现状：{{ gap.current_state }} → 建议：{{ gap.suggestion }}
                  </li>
                </ul>
              </li>
            </ul>
          </section>

          <section v-if="actionPhases.length" id="action" class="rp-block">
            <h2 class="rp-block-title">行动计划</h2>
            <ol class="rp-phases">
              <li v-for="(phase, index) in actionPhases" :key="index" class="rp-phase">
                <div class="rp-item-head">
                  <b class="rp-item-name">{{ phase.name }}</b>
                  <span class="rp-phase-range">{{ phase.date_range }}</span>
                  <span v-if="phase.tag" class="rp-item-tag">{{ phase.tag }}</span>
                </div>
                <ul class="rp-tasks">
                  <li v-for="(task, taskIndex) in phase.tasks" :key="taskIndex" :class="{ done: task.done }">
                    <span class="rp-task-mark">{{ task.done ? '✓' : '○' }}</span>
                    <span>{{ task.text }}</span>
                    <span v-if="task.due_date" class="rp-task-due">{{ task.due_date.slice(0, 10) }}</span>
                  </li>
                </ul>
              </li>
            </ol>
          </section>

          <section v-else-if="report" class="rp-block">
            <h2 class="rp-block-title">行动计划</h2>
            <p class="rp-empty">尚未生成行动计划。在③选定方向后，④行动会产出带时间点的任务。</p>
          </section>

          <section v-for="section in otherSections" :id="String(section.id)" :key="String(section.id)" class="rp-block">
            <h2 class="rp-block-title">{{ String(section.title ?? section.id) }}</h2>
            <pre class="rp-raw">{{ JSON.stringify(section.content ?? {}, null, 2) }}</pre>
          </section>
        </div>
      </div>

      <button class="rp-back" type="button" @click="scrollTo('verdict')">回到结论 ↑</button>
    </div>
  </main>
</template>

<style scoped>
.report-page {
  min-height: 100%;
  background: var(--paper);
}

.rp-container {
  max-width: var(--content-max-width);
  margin-inline: auto;
  padding: var(--space-8) var(--page-gutter) var(--space-16);
  display: grid;
  gap: var(--space-6);
}

.rp-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.rp-head h1 {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: 800;
  letter-spacing: -0.02em;
}

.rp-head p {
  margin: 6px 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.rp-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.export-btn {
  padding: 10px 20px;
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--color-action-bg);
  color: var(--color-text-inverse);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
}

.export-btn--ghost {
  background: transparent;
  color: var(--color-link);
  border: 1px solid var(--color-brand-border);
}

.rp-export-off { color: var(--color-text-muted); font-size: var(--font-size-xs); }

.rp-layout {
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  gap: var(--space-6);
  align-items: start;
}

.rp-sections {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}
.chip.strong { border-color: var(--greenLine); background: var(--greenSoft); color: var(--greenD); }
.chip.option { border-color: var(--blueLine); background: var(--blueSoft); color: var(--blueD); }
.chip.gap { border-color: var(--amberLine); background: var(--amberSoft); color: var(--amber); }
.chip.risk { border-color: var(--redLine); background: var(--redSoft); color: var(--red); }
.dim-track i.strong { background: linear-gradient(90deg, var(--green), var(--greenD)); }
.dim-track i.option { background: linear-gradient(90deg, var(--blue), var(--blueD)); }
.dim-track i.gap { background: linear-gradient(90deg, var(--amberLine), var(--amber)); }
.dim-track i.risk { background: linear-gradient(90deg, #e8a090, var(--red)); }
.dim-score.strong { color: var(--greenD); }
.dim-score.option { color: var(--blueD); }
.dim-score.gap { color: var(--amber); }
.dim-score.risk { color: var(--red); }
.heat-cell.strong { background: var(--greenSoft); border: 1px solid var(--greenLine); }
.heat-cell.strong .heat-score { color: var(--greenD); }
.heat-cell.option { background: var(--blueSoft); border: 1px solid var(--blueLine); }
.heat-cell.option .heat-score { color: var(--blueD); }
.heat-cell.gap { background: var(--amberSoft); border: 1px solid var(--amberLine); }
.heat-cell.gap .heat-score { color: var(--amber); }
.heat-cell.risk { background: var(--redSoft); border: 1px solid var(--redLine); }
.heat-cell.risk .heat-score { color: var(--red); }

/* 综合结论：深色 verdict 卡 + SWOT 四象限 */
.rp-verdict {
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, #1b2a3f, #243a55);
  color: #fff;
  box-shadow: var(--shadow-card);
  scroll-margin-top: calc(72px + var(--space-4));
}

.vd-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.vd-eyebrow { font-size: var(--font-size-xs); letter-spacing: 0.1em; opacity: 0.7; }
.vd-score { padding: 4px 12px; border-radius: var(--radius-pill); background: rgba(255, 255, 255, 0.14); font-size: var(--font-size-sm); }
.vd-title { margin: var(--space-4) 0 var(--space-3); font-size: var(--font-size-xl); line-height: 1.35; letter-spacing: -0.01em; }
.vd-summary { margin: 0 0 var(--space-5); color: rgba(255, 255, 255, 0.78); font-size: var(--font-size-sm); line-height: 1.7; }

.vd-swot {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.swot-cell {
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.swot-cell b { display: block; margin-bottom: var(--space-2); font-size: var(--font-size-xs); letter-spacing: 0.06em; }
.swot-cell ul { display: flex; flex-wrap: wrap; gap: 6px; margin: 0; padding: 0; list-style: none; }
.swot-cell li { padding: 2px 10px; border-radius: var(--radius-pill); background: rgba(255, 255, 255, 0.1); font-size: var(--font-size-xs); }
.dir-table td.recommended, .dir-table th.recommended { background: var(--greenSoft); }
.dir-table td.recommended strong { color: var(--greenD); }
.clover-items .track { height: 8px; border-radius: var(--radius-pill); background: var(--color-bg); overflow: hidden; }
.clover-items .track i { display: block; height: 100%; border-radius: inherit; }
.c-int .track i { background: var(--blue); }
.c-skill .track i { background: var(--green); }
.c-val .track i { background: var(--amber); }

.rp-empty {
  margin: 0;
  padding: var(--space-8);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  text-align: center;
}

.rp-notice {
  margin: 0;
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-warning-soft);
  color: var(--color-text-primary);
  font-size: var(--font-size-xs);
}

@media (max-width: 640px) {
  .rp-layout {
    grid-template-columns: 1fr;
  }

  .vd-swot {
    grid-template-columns: 1fr;
  }
}

@media print {
  .rp-actions,
  .rp-notice,
  .rp-layout > :first-child,
  .rp-strip {
    display: none !important;
  }

  .rp-layout {
    grid-template-columns: 1fr;
  }
}

/* 报告页：真实内容渲染所需的补充样式（原样式块保持不变） */
.rp-empty-detail { color: var(--muted); }
.rp-block { display: grid; gap: var(--space-4); margin-top: var(--space-8); }
.rp-block-head { display: flex; align-items: baseline; gap: var(--space-3); flex-wrap: wrap; }
.rp-block-title { margin: 0; font-size: var(--font-size-lg); font-weight: 800; }
.rp-block-method { color: var(--muted); font-size: var(--font-size-xs); }
.rp-items { display: grid; gap: var(--space-3); margin: 0; padding: 0; list-style: none; }
.rp-item { padding: var(--space-4); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--card); }
.rp-item-head { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.rp-item-name { font-size: var(--font-size-sm); }
.rp-item-tag { padding: 1px 8px; border-radius: var(--radius-pill); background: var(--blueSoft); color: var(--blueD); font-size: var(--font-size-xs); font-weight: 700; }
.rp-item-text { margin: 8px 0 0; font-size: var(--font-size-sm); line-height: 1.7; }
.rp-item-evidence { margin: 6px 0 0; color: var(--muted); font-size: var(--font-size-xs); line-height: 1.6; }
.rp-raw { margin: 0; padding: var(--space-4); border-radius: var(--radius-md); background: var(--card); font-size: var(--font-size-xs); white-space: pre-wrap; overflow-wrap: anywhere; }
.rp-back { justify-self: start; margin-top: var(--space-6); padding: 6px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-pill); background: var(--card); color: var(--color-text-secondary); font-size: var(--font-size-xs); cursor: pointer; }
.rp-item-score { color: var(--greenD); font-size: var(--font-size-xs); font-weight: 800; }
.rp-item-chosen { padding: 1px 8px; border-radius: var(--radius-pill); background: var(--greenSoft); color: var(--greenD); font-size: var(--font-size-xs); font-weight: 700; }
.rp-item-risk { margin: 6px 0 0; color: var(--red); font-size: var(--font-size-xs); line-height: 1.6; }
.rp-gaps { margin: 8px 0 0; padding-left: 18px; color: var(--color-text-secondary); font-size: var(--font-size-xs); line-height: 1.7; }
.rp-phases { display: grid; gap: var(--space-4); margin: 0; padding: 0; list-style: none; }
.rp-phase { padding: var(--space-4); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--card); }
.rp-phase-range { color: var(--muted); font-size: var(--font-size-xs); }
.rp-tasks { display: grid; gap: 6px; margin: 10px 0 0; padding: 0; list-style: none; }
.rp-tasks li { display: flex; align-items: baseline; gap: 8px; font-size: var(--font-size-xs); line-height: 1.6; }
.rp-tasks li.done { color: var(--muted); text-decoration: line-through; }
.rp-task-mark { flex: none; color: var(--greenD); font-weight: 800; }
.rp-task-due { margin-left: auto; color: var(--muted); white-space: nowrap; }
</style>

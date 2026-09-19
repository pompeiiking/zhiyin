<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { ReportFullTextView } from '@/api/schema'
import { exportAsset, getReportFullText, trackEvent } from '@/api/endpoints'
import ReportToc from '@/components/report/ReportToc.vue'

// 完整报告页 #screen-report（P0，挂在工作台资产上）
//
// 口径（前端设计文档 §4.4）：左侧目录导航 + 全文区块 + 导出操作。
// 报告内容来自 `GET /app/report/full-text`（只读资产版本，不重新生成）。
//
// ⚠️ 本页曾内联了一整份演示报告（含编造的方向方案、行动计划、画像条目、报告编号与
//    本地导出实现），以及一份前端合成的 15 维分数。这些都不是后端产出，已全部删除：
//    拿不到就显示空态，不再用近似内容顶替。方向方案目前后端没有正文接口，
//    因此这里如实显示空态而不是编三档方案。
const report = ref<ReportFullTextView | null>(null)
const loading = ref(true)
const error = ref('')
const activeId = ref('')
const exportNotice = ref('')
const exporting = ref(false)

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
          <button class="export-btn export-btn--ghost" type="button" :disabled="exporting" @click="onExport('pdf')">
            导出 PDF
          </button>
          <button class="export-btn" type="button" :disabled="exporting" @click="onExport('docx')">
            导出 Word
          </button>
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

/* 概览卡：品牌蓝渐变 hero，突出主攻方向与匹配度 */
.rp-overview {
  position: relative;
  overflow: hidden;
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--blueD), var(--blue) 60%, #57b0f0);
  color: #fff;
  box-shadow: var(--shadow-card);
  scroll-margin-top: calc(72px + var(--space-4));
}

.ov-glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}

.ov-glow-a { width: 180px; height: 180px; top: -80px; right: -40px; background: radial-gradient(circle, rgba(255, 255, 255, 0.35), transparent 70%); }
.ov-glow-b { width: 140px; height: 140px; bottom: -70px; left: -30px; background: radial-gradient(circle, rgba(255, 255, 255, 0.22), transparent 70%); }

.ov-eyebrow {
  position: relative;
  display: inline-block;
  font-size: var(--font-size-xs);
  letter-spacing: 0.1em;
  opacity: 0.85;
}

.ov-body {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-8);
  flex-wrap: wrap;
  margin-top: var(--space-5);
}

.ov-verdict { display: grid; gap: 6px; }
.ov-label { font-size: var(--font-size-xs); opacity: 0.85; }
.ov-direction { font-size: clamp(2rem, 5vw, 3rem); line-height: 1; letter-spacing: -0.02em; }

.ov-match {
  justify-self: start;
  padding: 4px 12px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.2);
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.ov-alts { display: grid; gap: var(--space-3); margin: 0; padding: 0; list-style: none; }
.ov-alts li { display: flex; align-items: baseline; gap: var(--space-2); font-size: var(--font-size-sm); }
.ov-alts span { opacity: 0.75; font-size: var(--font-size-xs); }
.ov-alts b { font-size: var(--font-size-md); }
.ov-alts em { font-style: normal; opacity: 0.85; }

/* 综合匹配度环：conic-gradient 分数环，右侧对齐 */
.ov-ring {
  position: relative;
  display: grid;
  width: 128px;
  height: 128px;
  flex: none;
  place-items: center;
  margin-left: auto;
  border-radius: 50%;
  background: conic-gradient(#fff var(--score), rgba(255, 255, 255, 0.25) 0);
}
.ov-ring::before {
  position: absolute;
  width: 102px;
  height: 102px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--blueD), var(--blue));
  content: '';
}
.ov-ring div {
  position: relative;
  z-index: 1;
  display: grid;
  text-align: center;
}
.ov-ring strong { font-size: 32px; line-height: 1; }
.ov-ring span { margin-top: 4px; font-size: var(--font-size-xs); opacity: 0.85; }

/* 概览统计条 */
.rp-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  margin: var(--space-2) 0 var(--space-4);
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}
.rp-strip > div { display: grid; gap: 3px; padding: var(--space-4) var(--space-3); text-align: center; }
.rp-strip > div:not(:last-child) { border-right: 1px solid var(--color-border); }
.rp-strip strong { font-size: var(--font-size-xl); font-weight: 800; }
.rp-strip span { color: var(--color-text-secondary); font-size: var(--font-size-xs); }
.strip-green strong { color: var(--greenD); }
.strip-amber strong { color: var(--amber); }
.strip-blue strong { color: var(--blueD); }
.strip-violet strong { color: var(--violet); }

/* 15 维全景解析：四组着色 + 逐项得分条 */
.rp-panorama {
  padding: var(--space-6) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  scroll-margin-top: calc(72px + var(--space-4));
}

.pan-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.pan-head h2 { margin: 0; font-size: var(--font-size-lg); font-weight: 800; letter-spacing: -0.01em; }

.pan-chips { display: flex; gap: var(--space-2); flex-wrap: wrap; }

.chip {
  display: inline-flex;
  align-items: baseline;
  gap: 5px;
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.chip b { font-size: var(--font-size-sm); }
.chip.strong { border-color: var(--greenLine); background: var(--greenSoft); color: var(--greenD); }
.chip.option { border-color: var(--blueLine); background: var(--blueSoft); color: var(--blueD); }
.chip.gap { border-color: var(--amberLine); background: var(--amberSoft); color: var(--amber); }
.chip.risk { border-color: var(--redLine); background: var(--redSoft); color: var(--red); }

.pan-summary { margin: var(--space-4) 0 var(--space-5); color: var(--color-text-secondary); font-size: var(--font-size-sm); }
.pan-match { color: var(--blueD); font-size: var(--font-size-md); }

/* 雷达图 + 目标岗位对比 */
.pan-visuals {
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}
.radar-card,
.fit-card {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}
.radar-card > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-4) 0;
}
.radar-card header span,
.fit-card header > span { color: var(--greenD); font-size: var(--font-size-xs); font-weight: 800; letter-spacing: 0.06em; }
.radar-card h3,
.fit-card h3 { margin: 4px 0 0; font-size: var(--font-size-md); }
.radar-card header small { display: flex; align-items: center; gap: 5px; color: var(--color-text-muted); font-size: var(--font-size-xs); }
.radar-card header i { width: 8px; height: 8px; border-radius: 50%; background: var(--blue); }
.radar-card header em { width: 8px; height: 8px; margin-left: 6px; border: 1px dashed var(--greenD); border-radius: 50%; background: var(--greenSoft); }
.radar-card svg { display: block; width: 100%; height: 240px; }
.radar-guide { fill: none; stroke: var(--color-border); stroke-width: 1; }
.radar-axis { stroke: var(--color-border); stroke-width: 1; }
.radar-target { fill: rgb(56 185 121 / 10%); stroke: var(--greenLine); stroke-width: 1.5; stroke-dasharray: 4 3; }
.radar-user { fill: rgb(55 138 221 / 18%); stroke: var(--blue); stroke-width: 2; }
.radar-dot { fill: var(--blue); stroke: #fff; stroke-width: 2; }
.radar-card text { fill: var(--color-text-secondary); font-size: 10px; font-weight: 600; }

.fit-card { display: flex; flex-direction: column; padding: var(--space-4); }
.fit-card header p { margin: 6px 0 0; color: var(--color-text-secondary); font-size: var(--font-size-xs); }
.fit-list { display: grid; gap: var(--space-5); margin: var(--space-6) 0 var(--space-5); }
.fit-row > div:first-child { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-2); }
.fit-row b { font-size: var(--font-size-sm); }
.fit-row span { color: var(--color-text-secondary); font-size: var(--font-size-xs); }
.fit-track { position: relative; overflow: visible; height: 8px; margin-top: var(--space-2); border-radius: var(--radius-pill); background: var(--color-bg); }
.fit-track i { display: block; height: 100%; border-radius: inherit; }
.fit-bar--blue { background: linear-gradient(90deg, #5eb0e9, var(--blue)); }
.fit-bar--green { background: linear-gradient(90deg, #6fd0a2, var(--green)); }
.fit-bar--amber { background: linear-gradient(90deg, #f0c36a, var(--amber)); }
.fit-track em { position: absolute; top: -4px; width: 2px; height: 16px; border-radius: 2px; background: var(--color-text-secondary); }
.fit-card footer { display: grid; gap: 3px; margin-top: auto; padding: var(--space-3); border-radius: var(--radius-md); background: var(--greenSoft); }
.fit-card footer span { color: var(--color-text-secondary); font-size: var(--font-size-xs); }
.fit-card footer b { color: var(--greenD); font-size: var(--font-size-sm); }

.pan-bars { display: grid; gap: var(--space-3); margin: 0; padding: 0; list-style: none; }
.pan-bars li { display: grid; grid-template-columns: 96px 1fr 34px; align-items: center; gap: var(--space-3); }

.dim-name { color: var(--color-text-secondary); font-size: var(--font-size-xs); text-align: right; }

.dim-track { height: 10px; border-radius: var(--radius-pill); background: var(--color-bg); overflow: hidden; }
.dim-track i { display: block; height: 100%; border-radius: inherit; }
.dim-track i.strong { background: linear-gradient(90deg, var(--green), var(--greenD)); }
.dim-track i.option { background: linear-gradient(90deg, var(--blue), var(--blueD)); }
.dim-track i.gap { background: linear-gradient(90deg, var(--amberLine), var(--amber)); }
.dim-track i.risk { background: linear-gradient(90deg, #e8a090, var(--red)); }

.dim-score { font-size: var(--font-size-sm); font-weight: 800; text-align: right; }
.dim-score.strong { color: var(--greenD); }
.dim-score.option { color: var(--blueD); }
.dim-score.gap { color: var(--amber); }
.dim-score.risk { color: var(--red); }

/* 15 维热力图：5 列网格，按四组着色 */
.pan-heatmap {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-2);
  margin-bottom: var(--space-5);
}

.heat-cell {
  display: grid;
  gap: 2px;
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  text-align: center;
}

.heat-name { font-size: var(--font-size-xs); color: var(--color-text-secondary); }
.heat-score { font-size: var(--font-size-sm); font-weight: 800; }
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
.s-strong b { color: #7fe3b8; }
.s-weak b { color: #f0a47b; }
.s-opp b { color: #8fbdf2; }
.s-risk b { color: #f5c9a6; }

/* 方向方案对比表 */
.rp-directions {
  padding: var(--space-6) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  scroll-margin-top: calc(72px + var(--space-4));
}

.dir-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  margin-bottom: var(--space-4);
}

.dir-head h2 { margin: 0; font-size: var(--font-size-lg); font-weight: 800; letter-spacing: -0.01em; }
.dir-sub { color: var(--color-text-secondary); font-size: var(--font-size-xs); }

.dir-table-wrap { overflow-x: auto; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }
.dir-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.dir-table th, .dir-table td { padding: var(--space-4); text-align: left; vertical-align: top; border-bottom: 1px solid var(--color-border); }
.dir-table thead th { color: var(--blueD); background: var(--blueSoft); font-size: var(--font-size-xs); }
.dir-table tbody th { width: 90px; color: var(--color-text-secondary); font-weight: 600; background: var(--color-bg); font-size: var(--font-size-xs); }
.dir-table tbody tr:last-child th, .dir-table tbody tr:last-child td { border-bottom: 0; }
.dir-table td b { font-size: var(--font-size-md); }
.dir-table td strong { color: var(--blueD); font-size: var(--font-size-lg); }
.dir-table td.recommended, .dir-table th.recommended { background: var(--greenSoft); }
.dir-table td.recommended strong { color: var(--greenD); }
.gap-tag { display: inline-block; margin: 2px 4px 2px 0; padding: 3px 8px; border-radius: var(--radius-pill); color: var(--amber); background: var(--amberSoft); font-size: var(--font-size-xs); }

/* 三叶草模型：韦恩图三环 + 逐环得分条 */
.rp-clover {
  padding: var(--space-6) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  scroll-margin-top: calc(72px + var(--space-4));
}

.clover-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.clover-head h2 { margin: 0; font-size: var(--font-size-lg); font-weight: 800; letter-spacing: -0.01em; }
.clover-sub { color: var(--color-text-secondary); font-size: var(--font-size-xs); }

.clover-body {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) 1fr;
  gap: var(--space-6);
  align-items: center;
  margin-top: var(--space-4);
}

.venn { width: 100%; max-width: 300px; height: auto; }
.venn circle { fill-opacity: 0.2; stroke-width: 1.5; }
.venn-int { fill: var(--blue); stroke: var(--blueD); }
.venn-skill { fill: var(--green); stroke: var(--greenD); }
.venn-val { fill: var(--amber); stroke: var(--amber); }
.venn-label { font-size: 13px; font-weight: 700; fill: var(--color-text-primary); text-anchor: middle; }
.venn-score { font-size: 18px; font-weight: 800; fill: var(--color-text-primary); text-anchor: middle; }
.venn-core { font-size: 22px; fill: var(--amber); text-anchor: middle; }

.clover-items { display: grid; gap: var(--space-4); margin: 0; padding: 0; list-style: none; }
.clover-items li { display: grid; grid-template-columns: 40px 1fr 32px; align-items: center; gap: var(--space-3); }
.clover-items span { font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text-primary); }
.clover-items .track { height: 8px; border-radius: var(--radius-pill); background: var(--color-bg); overflow: hidden; }
.clover-items .track i { display: block; height: 100%; border-radius: inherit; }
.c-int .track i { background: var(--blue); }
.c-skill .track i { background: var(--green); }
.c-val .track i { background: var(--amber); }
.clover-items b { font-size: var(--font-size-sm); font-weight: 800; text-align: right; }
.clover-items p { grid-column: 2 / -1; margin: 0; color: var(--color-text-secondary); font-size: var(--font-size-xs); }

/* 个人画像：三张带图标与状态的彩色信息卡 */
.rp-profile {
  padding: var(--space-6) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  scroll-margin-top: calc(72px + var(--space-4));
}

.prof-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  margin-bottom: var(--space-4);
}

.prof-head h2 { margin: 0; font-size: var(--font-size-lg); font-weight: 800; letter-spacing: -0.01em; }
.prof-sub { color: var(--color-text-secondary); font-size: var(--font-size-xs); }

.prof-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-3); }
.prof-grid article {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}
.prof-blue { border-color: var(--blueLine); background: var(--blueSoft); }
.prof-green { border-color: var(--greenLine); background: var(--greenSoft); }
.prof-amber { border-color: var(--amberLine); background: var(--amberSoft); }

.prof-icon {
  display: grid;
  width: 40px;
  height: 40px;
  flex: none;
  place-items: center;
  border-radius: var(--radius-sm);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 800;
}
.prof-blue .prof-icon { background: var(--blue); }
.prof-green .prof-icon { background: var(--green); }
.prof-amber .prof-icon { background: var(--amber); }

.prof-body { display: grid; gap: 6px; min-width: 0; }
.prof-title { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
.prof-title b { font-size: var(--font-size-sm); font-weight: 700; }
.prof-title em { padding: 2px 8px; border-radius: var(--radius-pill); font-size: var(--font-size-xs); font-style: normal; }
.prof-status--blue { color: var(--blueD); background: #fff; }
.prof-status--green { color: var(--greenD); background: #fff; }
.prof-status--amber { color: var(--amber); background: #fff; }
.prof-body p { margin: 0; color: var(--color-text-primary); font-size: var(--font-size-sm); line-height: 1.6; }

/* 行动计划：三段时间轴 */
.rp-action {
  padding: var(--space-6) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  scroll-margin-top: calc(72px + var(--space-4));
}

.act-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  margin-bottom: var(--space-5);
}

.act-head h2 { margin: 0; font-size: var(--font-size-lg); font-weight: 800; letter-spacing: -0.01em; }
.act-sub { color: var(--color-text-secondary); font-size: var(--font-size-xs); }

.act-timeline { display: grid; gap: var(--space-3); margin: 0; padding: 0; list-style: none; }
.act-timeline li { display: flex; gap: var(--space-3); position: relative; }
.act-timeline li:not(:last-child)::before {
  position: absolute;
  top: 26px;
  bottom: -14px;
  left: 13px;
  width: 2px;
  background: var(--color-border);
  content: '';
}

.act-node {
  display: grid;
  width: 28px;
  height: 28px;
  flex: none;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  font-size: var(--font-size-xs);
  font-weight: 800;
}
.act-blue .act-node { background: var(--blue); }
.act-green .act-node { background: var(--green); }
.act-violet .act-node { background: var(--violet); }

.act-body { display: grid; gap: 4px; min-width: 0; padding-bottom: var(--space-1); }
.act-top { display: flex; align-items: baseline; gap: var(--space-3); flex-wrap: wrap; }
.act-month { font-size: var(--font-size-sm); font-weight: 800; }
.act-top em { font-size: var(--font-size-sm); font-style: normal; color: var(--color-text-secondary); }
.act-blue .act-month { color: var(--blueD); }
.act-green .act-month { color: var(--greenD); }
.act-violet .act-month { color: var(--violet); }
.act-body p { margin: 0; color: var(--color-text-secondary); font-size: var(--font-size-xs); line-height: 1.6; }

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

  .ov-body {
    gap: var(--space-4);
  }

  .ov-ring {
    margin-left: 0;
  }

  .rp-strip {
    grid-template-columns: repeat(2, 1fr);
  }

  .rp-strip > div:nth-child(2) {
    border-right: 0;
  }

  .pan-visuals {
    grid-template-columns: 1fr;
  }

  .pan-bars li {
    grid-template-columns: 76px 1fr 30px;
    gap: var(--space-2);
  }

  .pan-heatmap {
    grid-template-columns: repeat(3, 1fr);
  }

  .vd-swot {
    grid-template-columns: 1fr;
  }

  .clover-body {
    grid-template-columns: 1fr;
  }

  .venn {
    max-width: 260px;
    margin-inline: auto;
  }

  .prof-grid {
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

  .rp-overview {
    border: 1px solid var(--color-border);
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

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { ReportFullTextView } from '@/api/schema'
import {
  claimGap,
  exportAsset,
  getReportFullText,
  getWorkspace,
  markTaskDone,
  selectDirectionPlan,
  trackEvent,
  writeCalendarNode,
} from '@/api/endpoints'
import { useSessionStore } from '@/stores/session'
import ReportToc from '@/components/report/ReportToc.vue'

// 完整报告页 #screen-report（P0，挂在工作台资产上）
//
// 口径（前端设计文档 §4.4）：左侧目录导航 + 全文区块 + 导出操作。
// 报告内容来自 `GET /app/report/full-text`（只读资产版本，不重新生成）。
//
// 本页不只是"读"：报告之后产品要继续往前走，用户必须能在这里完成四个动作——
// 认领差距（FR-DIAG-004）、选定方向（FR-DECIDE-003）、勾掉任务（FR-ACT-004）、
// 把节点放进日历（FR-BLOCK-002）。四者各调一个独立写端点，成功后由后端写行为
// 日志，成就与工作台时间线随之变化。只把报告渲染出来、按钮点了没反应，不算实现。
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

// 写操作的即时反馈与乐观状态。
//
// 为什么不在这四个动作后重新拉一次报告：`load()` 会把整页切成"正在加载报告…"，
// 用户刚点一下就看到整页闪一次。这里按各端点返回的**真实结果**就地更新（认领全量
// 清单、选中的方案 id、命中任务的完成数），后端仍是唯一事实来源，刷新后一致。
const actionNotice = ref('')
const claimingGapId = ref('')
const claimedGapIds = ref<string[]>([])
const selectingPlanId = ref('')
const chosenPlanId = ref('')
const busyTaskKey = ref('')
const doneTaskKeys = ref<string[]>([])
const calendaredTaskKeys = ref<string[]>([])
// 已写进日历的任务文本。日历节点的 `related_task_text` 就是任务原文，用它在刷新后
// 还原「已入日历」标记——只靠本地 key 的话，刷新即丢，用户会以为没加过而重复写入。
const calendaredTaskTexts = ref<string[]>([])

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

// 15 维的 `tag` 是内核冻结枚举 `DimensionEvidenceLevel`（英文值），
// 这里按既有 `ROLE_LABELS` 的做法映射为中文显示名。枚举本身是契约的一部分，
// 显示名与枚举同步冻结，所以放在代码里而不是动态资源——放注册表反而会让
// 文案与契约漂移（改了契约不改注册表，界面就会显示不存在的等级）。
const LEVEL_LABELS: Record<string, string> = {
  confirmed: '已确认',
  partial: '部分支撑',
  pending: '待验证',
  missing: '无依据',
}

// 分组码同样是内核 `ReportDimensionGroup.group` 的冻结字面量。
// 此前报告页把 `SELF-PORTRAIT` 直接当标题显示给用户，这里一并修正。
const GROUP_LABELS: Record<string, string> = {
  'SELF-PORTRAIT': '自我画像',
  'JOB-MARKET': '职业环境',
  'DECISION-RISK': '决策与风险',
}

function levelLabel(tag: string): string {
  return LEVEL_LABELS[tag] ?? tag
}

function groupLabel(group: string): string {
  return GROUP_LABELS[group] ?? group
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

/**
 * 15 维证据覆盖热力图的数据。
 *
 * 为什么是"证据覆盖"而不是"能力高低"：PRD `FR-DIAG-001` 只要求每维有结论与证据引用，
 * 没有任何评分口径。此前用前端硬编码的 0-100 分画雷达图，那是编造数据；
 * 现在按内核枚举 `DimensionEvidenceLevel` 上色，展示的是报告真的能自证的东西——
 * 每一维有多少依据。没有依据的维度会被显眼标出，正好引导用户回①补采（FR-DIAG-006）。
 */
const heatCells = computed(() =>
  dimensionGroups.value.flatMap((group) =>
    group.items.map((item) => ({
      key: `${group.id}-${item.name}`,
      group: groupLabel(group.group),
      name: item.name,
      tag: item.tag,
      level: levelLabel(item.tag),
      detail: item.conclusion,
      evidence: item.evidence,
    })),
  ),
)

/** 证据覆盖统计：让"这份诊断有多少是靠得住的"变成可核对的数字。 */
const heatSummary = computed(() => {
  const total = heatCells.value.length
  const count = (level: string) => heatCells.value.filter((cell) => cell.tag === level).length
  return {
    total,
    confirmed: count('confirmed'),
    partial: count('partial'),
    pending: count('pending'),
    missing: count('missing'),
  }
})

interface PlanGap {
  requirement: string
  current_state: string
  suggestion: string
}
interface ReportGapItem {
  gap_id: string
  requirement: string
  current_state: string
  suggestion: string
  theory_refs: string[]
  claimed: boolean
}

/**
 * ② 诊断产出的差距清单（FR-DIAG-003）。
 *
 * `claimed` 是后端把 `report.gap_claims` 折叠出来的布尔值，前端据此决定这一条显示
 * 「认领」按钮还是「已认领」——认领是针对某一版报告里的某一条差距做的动作，
 * 前端不做任何本地推断。旧报告没有 `gaps` 区块 → 这里为空 → 不渲染该章节。
 */
const reportGaps = computed<ReportGapItem[]>(() => {
  const content = (sectionById('gaps')?.content ?? {}) as Record<string, unknown>
  const raw = Array.isArray(content.items) ? (content.items as Array<Record<string, unknown>>) : []
  return raw.map((gap) => ({
    gap_id: String(gap.gap_id ?? ''),
    requirement: String(gap.requirement ?? ''),
    current_state: String(gap.current_state ?? ''),
    suggestion: String(gap.suggestion ?? ''),
    theory_refs: Array.isArray(gap.theory_refs) ? (gap.theory_refs as unknown[]).map(String) : [],
    claimed: Boolean(gap.claimed),
  }))
})

/** 本次会话内刚认领的差距，与报告里的 `claimed` 合并，避免重复认领时按钮状态回退。 */
function isGapClaimed(gap: ReportGapItem): boolean {
  return gap.claimed || claimedGapIds.value.includes(gap.gap_id)
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

/** 当前选中的方向方案。刚选定的优先，其次才是报告里的选中标记。 */
const activePlanId = computed(
  () => chosenPlanId.value || directions.value.find((plan) => plan.selected)?.id || '',
)

/**
 * 行动任务的复合标识 `阶段名:任务文本`。
 *
 * 这个口径由后端冻结：`InMemory` / `SqlAlchemy` 两个仓储与 DTO Mapper 三处必须一致
 * （见 `zhiyin_business` 的任务标识约定）。前端只做同样的拼接，不做模糊匹配，
 * 否则勾选会写错任务。
 */
function taskKey(phase: ActionPhase, task: ActionTask): string {
  return `${phase.name}:${task.text}`
}

function isTaskDone(phase: ActionPhase, task: ActionTask): boolean {
  return task.done || doneTaskKeys.value.includes(taskKey(phase, task))
}

function isTaskInCalendar(phase: ActionPhase, task: ActionTask): boolean {
  return (
    calendaredTaskKeys.value.includes(taskKey(phase, task)) ||
    calendaredTaskTexts.value.includes(task.text)
  )
}

/** 认领一条差距（FR-DIAG-004）。幂等：重复点同一条不会重复写行为日志。 */
async function onClaimGap(gap: ReportGapItem) {
  if (claimingGapId.value) return
  claimingGapId.value = gap.gap_id
  actionNotice.value = ''
  try {
    const result = await claimGap(gap.gap_id)
    claimedGapIds.value = result.claimed_gap_ids ?? [gap.gap_id]
    actionNotice.value = `已认领差距：${gap.requirement}`
  } catch (err) {
    actionNotice.value = `认领失败：${err instanceof Error ? err.message : '未知错误'}`
  } finally {
    claimingGapId.value = ''
  }
}

/** 选定方向方案（FR-DECIDE-003）。再选另一套走同一端点，后端自动取消旧方案。 */
async function onSelectPlan(plan: DirectionPlan) {
  if (selectingPlanId.value) return
  selectingPlanId.value = plan.id
  actionNotice.value = ''
  try {
    const result = await selectDirectionPlan(plan.id)
    chosenPlanId.value = result.plan_id
    actionNotice.value = `已选定方向：${result.name}`
  } catch (err) {
    actionNotice.value = `选定失败：${err instanceof Error ? err.message : '未知错误'}`
  } finally {
    selectingPlanId.value = ''
  }
}

/** 勾掉一条行动任务（FR-ACT-004）。成功后该任务的完成数会体现在工作台进度上。 */
async function onMarkTaskDone(phase: ActionPhase, task: ActionTask) {
  const key = taskKey(phase, task)
  if (busyTaskKey.value) return
  busyTaskKey.value = key
  actionNotice.value = ''
  try {
    const result = await markTaskDone(key)
    if (result.done) doneTaskKeys.value = [...new Set([...doneTaskKeys.value, key])]
    actionNotice.value = `已完成任务：${result.text}（${result.done_total}/${result.task_total}）`
  } catch (err) {
    actionNotice.value = `勾选失败：${err instanceof Error ? err.message : '未知错误'}`
  } finally {
    busyTaskKey.value = ''
  }
}

/** 把任务节点写进日历（FR-BLOCK-002）。规划师写入，教练在⑤复盘中读取。 */
async function onAddToCalendar(phase: ActionPhase, task: ActionTask) {
  const key = taskKey(phase, task)
  if (busyTaskKey.value) return
  busyTaskKey.value = key
  actionNotice.value = ''
  try {
    const node = await writeCalendarNode({
      title: task.text,
      due_at: task.due_date,
      source: 'planner',
      related_task_text: task.text,
    })
    calendaredTaskKeys.value = [...new Set([...calendaredTaskKeys.value, key])]
    calendaredTaskTexts.value = [...new Set([...calendaredTaskTexts.value, task.text])]
    actionNotice.value = `已加入日历：${node.title}`
  } catch (err) {
    actionNotice.value = `加入日历失败：${err instanceof Error ? err.message : '未知错误'}`
  } finally {
    busyTaskKey.value = ''
  }
}

interface ProfileFieldItem {
  key: string
  value: unknown
  confidence: number
  source: string
  evidence: string[]
}

/**
 * ⑤（末章）个人画像：**本版本生成时的快照**，不是当前活画像。
 *
 * 报告是版本化只读资产（《前端页面设计》§4.4：「报告全文页读取资产版本」），
 * 画像是活状态。后端在②诊断生成报告时把当次画像冻结进
 * `Report.profile_snapshot` 并随正文下发，所以这里显示的就是这一版的依据，
 * 不会因为用户后来又补了信息而变成"v1 报告里显示今天的画像"。
 * 旧报告没有快照 → 后端不生成该章节 → 这里自然不渲染。
 */
const profileSnapshot = computed<ProfileFieldItem[]>(() => {
  const content = (sectionById('profile')?.content ?? {}) as Record<string, unknown>
  const raw = Array.isArray(content.fields) ? (content.fields as Array<Record<string, unknown>>) : []
  return raw.map((field) => ({
    key: String(field.key ?? ''),
    value: field.value,
    confidence: Number(field.confidence ?? 0),
    source: String(field.source ?? ''),
    evidence: Array.isArray(field.evidence) ? (field.evidence as unknown[]).map(String) : [],
  }))
})

/** 快照生成时间：让"这是哪一版的依据"可核对。 */
const profileSnapshotAt = computed(() => {
  const content = (sectionById('profile')?.content ?? {}) as Record<string, unknown>
  return String(content.snapshot_of ?? '')
})

/** 字段中文名取文案包，与对话页/工作台同一口径。 */
function profileFieldName(key: string): string {
  return session.copyBundle[`profile.field.${key}`] ?? key
}

/** 值可能是字符串、数组或对象；空值如实显示"待采集"，与 `ProfileFields` 一致。 */
function profileFieldValue(field: ProfileFieldItem): string {
  const value = field.value
  if (value === null || value === undefined) return '待采集'
  if (Array.isArray(value)) return value.map((item) => String(item)).join(' / ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function confidencePercent(field: ProfileFieldItem): string {
  return `${Math.round((field.confidence ?? 0) * 100)}%`
}

/** 已单独渲染的章节，其余章节走通用列表渲染。 */
const RENDERED_IDS = new Set(['verdict', 'swot', 'gaps', 'directions', 'action', 'profile'])
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
    // 重新取到报告后，以报告为准清掉本地乐观状态：那是上一份数据的即时反馈，
    // 留着会让"另一版报告"显示成本版已认领/已勾选。
    claimedGapIds.value = []
    chosenPlanId.value = ''
    doneTaskKeys.value = []
    calendaredTaskKeys.value = []
    calendaredTaskTexts.value = []
    actionNotice.value = ''
    if (report.value && toc.value.length) activeId.value = String(toc.value[0].id ?? '')
    await restoreCalendarMarkers()
  } catch (err) {
    report.value = null
    // 404「尚未生成诊断报告」是正常状态，不是故障；如实显示空态。
    error.value = err instanceof Error ? err.message : '报告加载失败'
  } finally {
    loading.value = false
  }
}

/**
 * 从工作台视图回填「已入日历」标记（FR-BLOCK-002）。
 *
 * 日历节点是后端资产：写入后刷新页面，按钮不该复活成「加入日历」，否则用户会
 * 重复写入同一个节点。工作台视图已提供 `calendar_nodes` 读路径，这里按
 * `related_task_text` 与任务原文对齐；读不到就退回空标记，不影响报告渲染。
 */
async function restoreCalendarMarkers() {
  try {
    const workspace = await getWorkspace()
    const nodes = (workspace?.calendar_nodes ?? []) as Array<Record<string, unknown>>
    calendaredTaskTexts.value = [
      ...new Set(
        nodes
          .map((node) => String(node.related_task_text ?? ''))
          .filter((text) => text.length > 0),
      ),
    ]
  } catch {
    calendaredTaskTexts.value = []
  }
}

// 目录项既是"当前章节"指示，也要真的把正文滚到该章节。
// 此前目录绑的是只改 activeId 的旧函数，点击后除高亮外没有任何位移，
// 目录因此失去导航意义；这里统一走 scrollTo。
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
      <p v-if="actionNotice" class="rp-notice" role="status">{{ actionNotice }}</p>

      <p v-if="loading" class="rp-empty">正在加载报告…</p>

      <p v-else-if="!report" class="rp-empty">
        尚未生成诊断报告。完成①采集并进入②诊断后，报告正文会显示在这里。
        <span v-if="error" class="rp-empty-detail">（{{ error }}）</span>
      </p>

      <div v-else class="rp-layout">
        <ReportToc :items="toc" :active-id="activeId" @select="scrollTo" />
        <div class="rp-sections">
          <section id="verdict" class="rp-verdict">
            <div class="vd-top">
              <span class="vd-eyebrow">诊断结论</span>
              <b class="vd-score">第 {{ report.version }} 版</b>
            </div>
            <h2 class="vd-title">{{ verdict.title || '诊断结论' }}</h2>
            <p class="vd-summary">{{ verdict.summary || '报告未提供结论摘要。' }}</p>

            <div id="swot" class="vd-swot">
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

          <!-- 15 维证据覆盖热力图（§4.4 数据可视化）。
               上色依据是内核枚举 DimensionEvidenceLevel「证据充分度」，不是能力分数：
               PRD FR-DIAG-001 只要求每维有结论与证据引用，没有任何评分口径。
               悬停任一格显示该维的结论与证据；明细列表保留在下方。 -->
          <section v-if="heatCells.length" id="heatmap" class="rp-block rp-heat">
            <div class="rp-block-head">
              <h2 class="rp-block-title">15 维证据覆盖</h2>
              <span class="rp-block-method">
                共 {{ heatSummary.total }} 维 · 已确认 {{ heatSummary.confirmed }} ·
                部分支撑 {{ heatSummary.partial }} · 待验证 {{ heatSummary.pending }} ·
                无依据 {{ heatSummary.missing }}
              </span>
            </div>

            <ul class="heat-grid">
              <li
                v-for="cell in heatCells"
                :key="cell.key"
                class="heat-cell"
                :class="`is-${cell.tag}`"
                :title="`${cell.name}（${cell.level}）\n${cell.detail}\n依据：${cell.evidence}`"
              >
                <span class="heat-name">{{ cell.name }}</span>
                <span class="heat-level">{{ cell.level }}</span>
              </li>
            </ul>

            <p class="heat-note">
              「无依据」表示这一维还没有任何画像字段或检索证据支撑，结论只作待验证假设。
              补上对应信息后重跑诊断，该维等级会随之变化。
            </p>
          </section>

          <section
            v-for="group in dimensionGroups"
            :id="group.id"
            :key="group.id"
            class="rp-block"
          >
            <div class="rp-block-head">
              <h2 class="rp-block-title">{{ groupLabel(group.group) }}</h2>
              <span v-if="group.method" class="rp-block-method">{{ group.method }}</span>
            </div>
            <ul class="rp-items">
              <li v-for="(item, index) in group.items" :key="index" class="rp-item">
                <div class="rp-item-head">
                  <b class="rp-item-name">{{ item.name }}</b>
                  <span v-if="item.tag" class="rp-item-tag">{{ levelLabel(item.tag) }}</span>
                </div>
                <p class="rp-item-text">{{ item.conclusion }}</p>
                <p v-if="item.evidence" class="rp-item-evidence">依据：{{ item.evidence }}</p>
              </li>
            </ul>
          </section>

          <!-- 差距清单（FR-DIAG-003/004）：诊断 → 决策的衔接点。
               每条差距都能被"认领"，认领记录写进报告资产，并触发行为日志 → 成就
               `first_gap_claimed` 与工作台时间线。没有认领入口，报告就只是一张图。 -->
          <section v-if="reportGaps.length" id="gaps" class="rp-block">
            <div class="rp-block-head">
              <h2 class="rp-block-title">差距清单</h2>
              <span class="rp-block-method">
                共 {{ reportGaps.length }} 条 · 已认领
                {{ reportGaps.filter((gap) => isGapClaimed(gap)).length }} 条
              </span>
            </div>
            <ul class="rp-items">
              <li v-for="gap in reportGaps" :key="gap.gap_id" class="rp-item">
                <div class="rp-item-head">
                  <b class="rp-item-name">{{ gap.requirement }}</b>
                  <span v-if="isGapClaimed(gap)" class="rp-item-chosen">已认领</span>
                  <button
                    v-else
                    class="rp-act"
                    type="button"
                    :disabled="claimingGapId === gap.gap_id"
                    @click="onClaimGap(gap)"
                  >
                    {{ claimingGapId === gap.gap_id ? '认领中…' : '认领这条差距' }}
                  </button>
                </div>
                <p class="rp-item-text">现状：{{ gap.current_state || '报告未提供现状描述' }}</p>
                <p class="rp-item-evidence">建议：{{ gap.suggestion }}</p>
                <p v-if="gap.theory_refs.length" class="rp-item-evidence">
                  方法论：{{ gap.theory_refs.join(' / ') }}
                </p>
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
                  <span v-if="activePlanId === plan.id" class="rp-item-chosen">已选定</span>
                  <button
                    v-else
                    class="rp-act"
                    type="button"
                    :disabled="selectingPlanId === plan.id"
                    @click="onSelectPlan(plan)"
                  >
                    {{ selectingPlanId === plan.id ? '选定中…' : '选定这个方向' }}
                  </button>
                </div>
                <p class="rp-item-text">{{ plan.target_desc }}</p>
                <p class="rp-item-evidence">契合依据：{{ plan.fit_reason }}</p>
                <p class="rp-item-risk">主要风险：{{ plan.main_risk }}</p>
                <ul v-if="plan.gaps.length" class="rp-gaps">
                  <li v-for="(gap, index) in plan.gaps" :key="index">
                    {{ gap.requirement }}
                    <!--
                      现状/建议来自后端 PlanGap。当前契约层只下发了 requirement，
                      current_state / suggestion 恒为空串；此处按内容渲染，避免出现
                      「→ 现状： → 建议：」这种空标签。后端补齐字段后自动生效。
                    -->
                    <template v-if="gap.current_state"> → 现状：{{ gap.current_state }}</template>
                    <template v-if="gap.suggestion"> → 建议：{{ gap.suggestion }}</template>
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
                  <li
                    v-for="(task, taskIndex) in phase.tasks"
                    :key="taskIndex"
                    :class="{ done: isTaskDone(phase, task) }"
                  >
                    <button
                      class="rp-task-mark"
                      type="button"
                      :disabled="busyTaskKey === taskKey(phase, task)"
                      :title="isTaskDone(phase, task) ? '已完成' : '标记为已完成'"
                      @click="onMarkTaskDone(phase, task)"
                    >
                      {{ isTaskDone(phase, task) ? '✓' : '○' }}
                    </button>
                    <span>{{ task.text }}</span>
                    <span v-if="task.due_date" class="rp-task-due">{{ task.due_date.slice(0, 10) }}</span>
                    <button
                      v-if="!isTaskDone(phase, task) && !isTaskInCalendar(phase, task)"
                      class="rp-act rp-act--mini"
                      type="button"
                      :disabled="busyTaskKey === taskKey(phase, task)"
                      @click="onAddToCalendar(phase, task)"
                    >
                      加入日历
                    </button>
                    <span v-else-if="isTaskInCalendar(phase, task)" class="rp-item-chosen">
                      已入日历
                    </span>
                  </li>
                </ul>
              </li>
            </ol>
          </section>

          <section v-else-if="report" class="rp-block">
            <h2 class="rp-block-title">行动计划</h2>
            <p class="rp-empty">尚未生成行动计划。在③选定方向后，④行动会产出带时间点的任务。</p>
          </section>

          <!-- 个人画像：本版本生成时的**快照**（§4.4 要求报告含个人画像）。
               刻意写明"快照"，避免用户把它当成当前画像而与工作台对不上。 -->
          <section v-if="profileSnapshot.length" id="profile" class="rp-block">
            <div class="rp-block-head">
              <h2 class="rp-block-title">个人画像</h2>
              <span class="rp-block-method">
                本版本生成时的画像快照{{ profileSnapshotAt ? ` · ${profileSnapshotAt.slice(0, 10)}` : '' }}
              </span>
            </div>
            <ul class="rp-items">
              <li v-for="field in profileSnapshot" :key="field.key" class="rp-item">
                <div class="rp-item-head">
                  <b class="rp-item-name">{{ profileFieldName(field.key) }}</b>
                  <span class="rp-item-score">置信度 {{ confidencePercent(field) }}</span>
                  <span v-if="field.source" class="rp-item-tag">{{ field.source }}</span>
                </div>
                <p class="rp-item-text">{{ profileFieldValue(field) }}</p>
                <p v-if="field.evidence.length" class="rp-item-evidence">
                  依据：{{ field.evidence.join(' / ') }}
                </p>
              </li>
            </ul>
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
.chip.risk { border-color: var(--redLine); background: var(--redSoft); color: var(--red); }
.dim-score.risk { color: var(--red); }
.heat-cell.strong { background: var(--greenSoft); border: 1px solid var(--greenLine); }
.heat-cell.option { background: var(--blueSoft); border: 1px solid var(--blueLine); }
.heat-cell.gap { background: var(--amberSoft); border: 1px solid var(--amberLine); }
.heat-cell.risk { background: var(--redSoft); border: 1px solid var(--redLine); }

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
  /* 目录里的「SWOT」指向本块：它嵌在综合结论卡里，需要自己的 scroll-margin
     才能在跳转后不被顶栏压住。 */
  scroll-margin-top: calc(72px + var(--space-4));
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
  .rp-layout > :first-child {
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
.rp-task-mark {
  flex: none;
  padding: 0;
  border: 0;
  background: none;
  color: var(--greenD);
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}
.rp-task-mark:disabled { cursor: progress; opacity: 0.5; }
.rp-task-due { margin-left: auto; color: var(--muted); white-space: nowrap; }

/* 写操作按钮：认领差距 / 选定方向 / 加入日历。统一样式，避免各处各写一套。 */
.rp-act {
  margin-left: auto;
  padding: 4px 12px;
  border: 1px solid var(--color-brand-border);
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--color-link);
  font-size: var(--font-size-xs);
  font-weight: 700;
  cursor: pointer;
}
.rp-act:disabled { cursor: progress; opacity: 0.5; }
.rp-act--mini { margin-left: 0; flex: none; }

/* 15 维证据覆盖热力图。色阶按内核枚举 DimensionEvidenceLevel 的四档，
   从"证据充分"到"无依据"逐级变浅/转红，不表达能力好坏。 */
.heat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.heat-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-left-width: 4px;
  border-radius: var(--radius-sm);
  background: var(--card);
  cursor: help;
}
.heat-name { font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-primary); }
.heat-level { font-size: var(--font-size-xs); font-weight: 700; }
.heat-cell.is-confirmed { border-left-color: var(--greenD); background: var(--greenSoft); }
.heat-cell.is-confirmed .heat-level { color: var(--greenD); }
.heat-cell.is-partial { border-left-color: var(--blueD); background: var(--blueSoft); }
.heat-cell.is-partial .heat-level { color: var(--blueD); }
.heat-cell.is-pending { border-left-color: var(--amber); background: var(--amberSoft); }
.heat-cell.is-pending .heat-level { color: var(--amber); }
.heat-cell.is-missing { border-left-color: var(--red); background: var(--redSoft); }
.heat-cell.is-missing .heat-level { color: var(--red); }
.heat-note { margin: var(--space-3) 0 0; color: var(--color-text-muted); font-size: var(--font-size-xs); line-height: 1.7; }
</style>

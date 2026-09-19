<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { ReportFullTextView } from '@/api/schema'
import { getReportFullText, trackEvent } from '@/api/endpoints'
import { useSessionStore } from '@/stores/session'
import { useAgentsStore } from '@/stores/agents'
import MockBadge from '@/components/common/MockBadge.vue'
import GrowthShareCard from '@/components/report/GrowthShareCard.vue'
import ReportSection from '@/components/report/ReportSection.vue'
import ReportToc from '@/components/report/ReportToc.vue'

// 完整报告页 #screen-report（P0，挂在工作台资产上）
//
// 口径（前端设计文档 §4.4）：左侧目录导航 + 全文区块 + 导出操作。
// 报告内容来自 GET /app/report/full-text（只读资产版本，不重新生成）。
const session = useSessionStore()

// ⚠️ 临时演示数据：后端报告全文未接入时保留可读正文，非真实数据
const demoReport = {
  report_id: 'demo-report',
  version: 2,
  generated_at: '今天 11:02',
  toc: [
    { id: 'overview', title: '报告概览' },
    { id: 'verdict', title: '综合结论' },
    { id: 'panorama', title: '15 维全景解析' },
    { id: 'directions', title: '方向方案对比' },
    { id: 'clover', title: '三叶草模型' },
    { id: 'profile', title: '个人画像' },
    { id: 'action', title: '行动计划' },
  ],
  sections: [
    {
      id: 'overview',
      title: '报告概览',
      paragraphs: [
        '本报告基于你的对话与行为日志，按职业咨询成熟方法逐步生成，当前为第 2 版。',
        '主攻方向建议为「结构设计」，备选「施工管理」；结论与依据见下文各章节。',
      ],
    },
    {
      id: 'panorama',
      title: '15 维全景解析',
      paragraphs: [
        '优势维度：技能匹配、学业基础、工具熟练度均高于结构设计岗常见要求。',
        '差距维度：职业兴趣尚未明确，价值排序待采集；建议下一步补齐兴趣编码。',
        '风险维度：秋招窗口临近，需在 9 月前完成方向确认与网申准备。',
      ],
    },
  ],
} as unknown as ReportFullTextView

// 个人画像与行动计划：演示阶段结构化呈现，后端接入后由 report.sections 下发
const profileItems = [
  { key: 'education', label: '学业', value: '沈阳建筑大学 · 土木工程 · 大四 · GPA 3.2（前 30%）', status: '已采集', tone: 'blue' },
  { key: 'skill', label: '技能', value: '熟练使用 AutoCAD、PKPM、YJK，完成 2 个课程设计', status: '已采集', tone: 'green' },
  { key: 'interest', label: '兴趣与价值', value: '职业兴趣与价值排序待采集，补齐后可提升诊断置信度', status: '待补充', tone: 'amber' },
] as const

const actionPhases = [
  { month: '9 月', title: '锁定目标与投递', detail: '完成目标公司清单，投递网申（结构设计岗优先）。', tone: 'blue' },
  { month: '10 月', title: '准备面试作品集', detail: '重点展示 2 个课程设计与结构计算。', tone: 'green' },
  { month: '11 月', title: '校准方向', detail: '按面试反馈校准方向，必要时重生成方案。', tone: 'violet' },
] as const

const report = ref<ReportFullTextView>(demoReport)
const activeId = ref('overview')
const exportNotice = ref('')

const toc = computed(() => (report.value.toc ?? []) as Array<Record<string, unknown>>)
const sections = computed(() => (report.value.sections ?? []) as Array<Record<string, unknown>>)
// 后端资产导出未接入时（演示 / preview），前端本地生成 Word / 打印 PDF 也能完整导出。
const canExport = computed(() => session.featureFlags.export === true || session.preview === true)

// 报告身份与编号：演示阶段由本地生成，后端接入后由 report 下发。
const reportOwner = computed(() => session.identity.nickname || '体验用户')
const reportNo = computed(() => {
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  return `ZY-${date}-${String(report.value.version ?? 1).padStart(3, '0')}`
})

// 15 维全景解析：结论与分组口径统一取用 agents store（与对话页 / 智能体页同源），
// 报告页不另写一套维度名、分数或分组阈值。
const agents = useAgentsStore()
const dimensions = computed(() => agents.analysis?.dimensions ?? [])
const matchScore = computed(() => agents.analysis?.matchScore ?? 0)
const groups = computed(() => agents.analysisGroups)
const groupMeta = [
  { key: 'strong', label: '强项' },
  { key: 'option', label: '机会' },
  { key: 'gap', label: '待补' },
  { key: 'risk', label: '风险' },
] as const

type DimensionTone = (typeof groupMeta)[number]['key']
const toneOf = (score: number): DimensionTone =>
  score >= 80 ? 'strong' : score >= 70 ? 'option' : score >= 60 ? 'gap' : 'risk'

// 综合结论 SWOT：四象限直接由 agents 的四组口径派生，报告页不另设阈值或重排
const swot = computed(() => ({
  strengths: groups.value.strong,
  weaknesses: [...groups.value.gap, ...groups.value.risk],
  opportunities: groups.value.option,
  risks: groups.value.risk,
}))

// 三叶草（兴趣 × 能力 × 价值）：三环分别映射到 15 维中的对应维度，中央交集即理想职业
const clover = computed(() => {
  const score = (name: string) => dimensions.value.find((d) => d.name === name)?.score ?? 0
  return {
    interest: score('兴趣倾向'),
    ability: score('通用能力'),
    value: score('职业价值观'),
  }
})

const cloverNotes = {
  interest: '兴趣编码待明确，补齐后可提升诊断置信度',
  ability: '结构软件与技术积累扎实',
  value: '价值排序待采集',
} as const

// 方向方案：主攻 / 平行 / 保底三档（与对话页方向口径一致的演示值）
const directions = [
  { strategy: 'primary', label: 'A · 主攻', title: '结构设计', matchScore: 82, rationale: '土木专业与 PKPM/YJK 结构软件优势最匹配设计院结构岗', gaps: ['补齐作品集', '强化结构计算表达'] },
  { strategy: 'parallel', label: 'B · 平行', title: '施工管理', matchScore: 74, rationale: '工程现场与项目管理方向，专业能力可迁移', gaps: ['补现场实习', '施工组织认知'] },
  { strategy: 'fallback', label: 'C · 保底', title: 'BIM 建模', matchScore: 69, rationale: '数字化建模与协同方向，软件上手快', gaps: ['补 Revit 建模', '协同流程'] },
] as const

// 概览 / 综合结论 / 15 维 / 方向方案 / 三叶草各自单独渲染，其余章节走通用 ReportSection
const otherSections = computed(() => sections.value.filter((s) => !['overview', 'verdict', 'panorama', 'directions', 'clover'].includes(String(s.id))))

// 概览统计条：优势维度 / 重点提升 / 方向方案 / 关键窗口
const summaryStrip = computed(() => [
  { label: '优势维度', value: groups.value.strong.length, tone: 'green' },
  { label: '重点提升', value: groups.value.gap.length, tone: 'amber' },
  { label: '方向方案', value: directions.length, tone: 'blue' },
  { label: '关键窗口', value: '8周', tone: 'violet' },
])

// 15 维雷达图：取 6 个代表性维度与岗位基线对照（其余维度走热力图与得分条）
const radarItems = computed(() => {
  const labels = ['专业基础', '技能匹配', '通用能力', '岗位认知', '目标清晰度', '路径可达性']
  const score = (name: string) => dimensions.value.find((d) => d.name === name)?.score ?? 0
  return labels.map((label) => ({ label, score: score(label) }))
})
const radarTarget = [82, 82, 78, 80, 75, 76]
function radarPoint(index: number, score: number, radius = 82) {
  const angle = (Math.PI * 2 * index) / 6 - Math.PI / 2
  return `${150 + (Math.cos(angle) * radius * score) / 100},${118 + (Math.sin(angle) * radius * score) / 100}`
}
const radarUserPoints = computed(() => radarItems.value.map((item, index) => radarPoint(index, item.score)).join(' '))
const radarTargetPoints = computed(() => radarTarget.map((score, index) => radarPoint(index, score)).join(' '))
const radarGuidePoints = (score: number) => Array.from({ length: 6 }, (_, index) => radarPoint(index, score)).join(' ')
const radarLabelPoints = Array.from({ length: 6 }, (_, index) => {
  const angle = (Math.PI * 2 * index) / 6 - Math.PI / 2
  return { x: 150 + Math.cos(angle) * 105, y: 118 + Math.sin(angle) * 105 + 4 }
})

// 目标岗位对比条：当前得分 vs 岗位基线
const jobFitBars = computed(() => {
  const score = (name: string) => dimensions.value.find((d) => d.name === name)?.score ?? 0
  return [
    { label: '技能匹配', value: score('技能匹配'), target: 82, tone: 'blue' },
    { label: '经历证据', value: score('经历证据'), target: 78, tone: 'amber' },
    { label: '工程化准备', value: score('通用能力'), target: 75, tone: 'green' },
  ]
})

function selectSection(id: string) {
  activeId.value = id
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// 目录高亮跟随滚动：滚动文章时，左侧目录自动高亮当前所在章节。
const TOP_OFFSET = 96
let scrollRaf = 0

function updateActiveSection() {
  const ids = toc.value.map((item) => String(item.id))
  if (!ids.length) return
  let current = ids[0]
  for (const id of ids) {
    const el = document.getElementById(id)
    if (el && el.getBoundingClientRect().top <= TOP_OFFSET) current = id
  }
  // 滚到底部时兜底高亮最后一章
  const scrolledToBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4
  if (scrolledToBottom) current = ids[ids.length - 1]
  activeId.value = current
}

function onScroll() {
  if (scrollRaf) return
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = 0
    updateActiveSection()
  })
}

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  if (scrollRaf) cancelAnimationFrame(scrollRaf)
})

// ---- 导出：演示阶段前端直接生成 Word（.doc）/ 打印为 PDF，后端资产导出接入后再走 POST /app/assets/export ----
function escapeHtml(value: string | number) {
  return String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[character] ?? character))
}

function exportWord() {
  const dimensionRows = dimensions.value
    .map((item) => `<tr><td>${groupMeta.find((g) => g.key === toneOf(item.score))?.label ?? ''}</td><td>${escapeHtml(item.name)}</td><td class="score">${item.score}</td></tr>`)
    .join('')
  const directionRows = directions
    .map((d) => `<tr><td>${escapeHtml(d.label)}</td><td>${escapeHtml(d.title)}</td><td class="score">${d.matchScore}%</td><td>${escapeHtml(d.rationale)}</td><td>${d.gaps.map(escapeHtml).join('；')}</td></tr>`)
    .join('')
  const css = `@page WordSection1{size:595.3pt 841.9pt;margin:51pt 45pt 51pt 45pt}div.WordSection1{page:WordSection1}body{font-family:'Microsoft YaHei','SimSun',sans-serif;color:#202824;font-size:10.5pt;line-height:1.7;margin:0}h1,h2,h3,p{margin:0}h1{font-size:27pt;line-height:1.28}h2{font-size:17pt;color:#18241e}h3{font-size:12.5pt}p{margin:7pt 0}.cover{min-height:690pt;box-sizing:border-box;padding:37pt 22pt 0;text-align:center}.brand{color:#0c956b;font-size:16pt;font-weight:700;text-align:left}.document-no{text-align:right;font-size:9pt;margin-top:-23pt;color:#4b5750}.cover-title{margin-top:94pt}.cover-title b{color:#0c956b}.subtitle{margin-top:8pt;font-size:12pt}.seal{width:105pt;height:105pt;margin:62pt auto 45pt;border-radius:50%;background:#e9f7f0;color:#079667;display:flex;align-items:center;justify-content:center;font-size:15pt;font-weight:700;border:6pt solid #c6eedb}.cover-line{border:0;border-top:1pt solid #6fc49e;margin:0 0 31pt}.cover-meta{font-size:10pt;color:#536159;line-height:2}.page-break{page-break-before:always}.section-title{position:relative;text-align:center;margin:0 0 23pt;padding-top:8pt;border-top:1pt solid #8fcfb1}.section-title span{display:inline-block;margin-top:-14pt;padding:6pt 18pt;border-radius:14pt;color:white;background:#09936b;font-weight:700}.insight{padding:12pt 14pt;border-left:4pt solid #0c956b;background:#f4faf7;font-size:11pt}.swot{width:100%;border-collapse:separate;border-spacing:6pt}.swot td{width:25%;vertical-align:top;padding:9pt;border:1pt solid #dde7e1}.swot b{color:#0c956b;font-size:15pt}.swot p{font-size:9.5pt}.data-table{width:100%;border-collapse:collapse;margin-top:11pt}.data-table th,.data-table td{border:1pt solid #d9dfdb;padding:7pt 8pt;vertical-align:top}.data-table th{background:#eaf6ef;font-size:9pt;color:#1d382a}.data-table td{font-size:9pt}.score{color:#078c64;font-weight:700;text-align:center;white-space:nowrap}.footer{margin-top:37pt;padding-top:4pt;border-top:1pt solid #a5d5ba;text-align:center;color:#76837b;font-size:8.5pt}`
  const primary = directions.find((d) => d.strategy === 'primary')
  const documentHtml = `<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(reportOwner.value)}职业深度解析报告</title><style>${css}</style></head><body><div class="WordSection1"><section class="cover"><div class="brand">职引</div><div class="document-no">职业深度解析报告 · ${escapeHtml(reportNo.value)}</div><div class="cover-title"><h1><b>AI</b> 职业深度解析报告</h1><p class="subtitle">${escapeHtml(reportOwner.value)}的职业画像、方向判断与行动建议</p></div><div class="seal">15 维<br>解析</div><hr class="cover-line"><div class="cover-meta">综合匹配度：<b>${matchScore.value}%</b><br>报告编号：${escapeHtml(reportNo.value)}<br>生成时间：${escapeHtml(report.value.generated_at ?? '—')}</div></section><section class="page-break"><div class="section-title"><span>核心结论</span></div><div class="insight"><b>核心结论：</b>综合 15 维解析（${groups.value.strong.length} 强项 / ${groups.value.option.length} 机会 / ${groups.value.gap.length} 待补 / ${groups.value.risk.length} 风险），建议以设计院「结构设计」为主攻，施工管理平行备选，BIM 建模保底。<br><b>主攻建议：</b>${escapeHtml(primary?.title ?? '待选择方向')}（匹配度 ${primary?.matchScore ?? matchScore.value}%）</div><div class="section-title"><span>15 维职业诊断</span></div><table class="data-table"><thead><tr><th>分组</th><th>维度</th><th>得分</th></tr></thead><tbody>${dimensionRows}</tbody></table></section><section class="page-break"><div class="section-title"><span>SWOT 判断</span></div><table class="swot"><tr><td><b>S</b><h3>优势</h3>${swot.value.strengths.map((item) => `<p>${escapeHtml(item)}</p>`).join('')}</td><td><b>W</b><h3>待补</h3>${swot.value.weaknesses.map((item) => `<p>${escapeHtml(item)}</p>`).join('')}</td><td><b>O</b><h3>机会</h3>${swot.value.opportunities.map((item) => `<p>${escapeHtml(item)}</p>`).join('')}</td><td><b>T</b><h3>风险</h3>${swot.value.risks.map((item) => `<p>${escapeHtml(item)}</p>`).join('')}</td></tr></table><div class="section-title"><span>方向方案</span></div><table class="data-table"><thead><tr><th>策略</th><th>目标方向</th><th>匹配度</th><th>定位依据</th><th>关键差距</th></tr></thead><tbody>${directionRows}</tbody></table><footer class="footer">职引 · 职业深度解析报告 ｜报告不是终点，而是下一次行动的起点</footer></section></div></body></html>`
  const blob = new Blob(['\ufeff', documentHtml], { type: 'application/msword;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `${reportOwner.value}_职业深度解析报告_${reportNo.value}.doc`
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(link.href), 1000)
  exportNotice.value = 'Word 报告已生成并开始下载。'
}

function exportPdf() {
  exportNotice.value = ''
  window.print()
}

function onExport(format: 'pdf' | 'docx') {
  void trackEvent('asset_export', { asset_type: 'report', format }).catch(() => {})
  if (format === 'docx') exportWord()
  else exportPdf()
}

onMounted(async () => {
  void trackEvent('diagnosis_view', { source: 'report' }).catch(() => {})
  agents.ensureDemoAnalysis()
  window.addEventListener('scroll', onScroll, { passive: true })
  updateActiveSection()
  try {
    const data = await getReportFullText()
    if (data?.report_id) report.value = data
  } catch {
    // 后端未接入时保留演示正文，页面仍可评审
  }
})
</script>

<template>
  <main data-anchor="screen-report" class="report-page">
    <div class="rp-container">
      <header class="rp-head">
        <div>
          <h1>完整报告</h1>
          <p>第 {{ report.version }} 版 · 生成于 {{ report.generated_at }} · 只读资产视图</p>
        </div>
        <div class="rp-actions">
          <MockBadge source="demo" />
          <template v-if="canExport">
            <button type="button" class="export-btn export-btn--ghost" @click="onExport('pdf')">导出 PDF</button>
            <button type="button" class="export-btn" @click="onExport('docx')">导出 Word</button>
          </template>
        </div>
      </header>

      <div class="rp-layout">
        <ReportToc :items="toc" :active-id="activeId" @select="selectSection" />
        <div class="rp-sections">
          <section id="overview" class="rp-overview">
            <span class="ov-glow ov-glow-a" aria-hidden="true"></span>
            <span class="ov-glow ov-glow-b" aria-hidden="true"></span>
            <span class="ov-eyebrow">报告概览 · 第 {{ report.version }} 版 · {{ reportNo }}</span>
            <div class="ov-body">
              <div class="ov-verdict">
                <span class="ov-label">{{ reportOwner }} 的主攻方向</span>
                <b class="ov-direction">{{ directions[0].title }}</b>
                <span class="ov-match">{{ directions[0].matchScore }}% 匹配度</span>
              </div>
              <ul class="ov-alts">
                <li v-for="d in directions.slice(1)" :key="d.title">
                  <span>{{ d.strategy === 'parallel' ? '备选' : '保底' }}</span>
                  <b>{{ d.title }}</b>
                  <em>{{ d.matchScore }}%</em>
                </li>
              </ul>
              <div class="ov-ring" :style="{ '--score': `${matchScore * 3.6}deg` }">
                <div><strong>{{ matchScore }}</strong><span>综合匹配度</span></div>
              </div>
            </div>
          </section>

          <section class="rp-strip" aria-label="报告统计">
            <div v-for="item in summaryStrip" :key="item.label" :class="`strip-${item.tone}`">
              <strong>{{ item.value }}</strong>
              <span>{{ item.label }}</span>
            </div>
          </section>

          <section id="verdict" class="rp-verdict">
            <div class="vd-top">
              <span class="vd-eyebrow">15 维综合结论</span>
              <b class="vd-score">{{ matchScore }}% 匹配</b>
            </div>
            <h2 class="vd-title">「技术功底扎实 + 目标明确」— 主攻条件基本具备</h2>
            <p class="vd-summary">
              综合 15 维解析（{{ groups.strong.length }} 强项 / {{ groups.option.length }} 机会 /
              {{ groups.gap.length }} 待补 / {{ groups.risk.length }} 风险）：建议以设计院「结构设计」为主攻，
              施工管理平行备选，BIM 建模保底。
            </p>
            <div class="vd-swot">
              <div class="swot-cell s-strong">
                <b>优势 STRENGTH</b>
                <ul><li v-for="n in swot.strengths" :key="n">{{ n }}</li></ul>
              </div>
              <div class="swot-cell s-weak">
                <b>短板 WEAKNESS</b>
                <ul><li v-for="n in swot.weaknesses" :key="n">{{ n }}</li></ul>
              </div>
              <div class="swot-cell s-opp">
                <b>机会 OPPORTUNITY</b>
                <ul><li v-for="n in swot.opportunities" :key="n">{{ n }}</li></ul>
              </div>
              <div class="swot-cell s-risk">
                <b>风险 RISK</b>
                <ul><li v-for="n in swot.risks" :key="n">{{ n }}</li></ul>
              </div>
            </div>
          </section>

          <section id="panorama" class="rp-panorama">
            <header class="pan-head">
              <h2>15 维全景解析</h2>
              <div class="pan-chips">
                <span v-for="g in groupMeta" :key="g.key" class="chip" :class="g.key">
                  <b>{{ groups[g.key].length }}</b>{{ g.label }}
                </span>
              </div>
            </header>
            <p class="pan-summary">综合匹配度 <b class="pan-match">{{ matchScore }}%</b> · 优势、机会、待补与风险四组一目了然</p>
            <div class="pan-visuals">
              <article class="radar-card">
                <header>
                  <div><span>能力结构图</span><h3>个人画像与岗位基线</h3></div>
                  <small><i /> 当前画像　<em /> 岗位基线</small>
                </header>
                <svg viewBox="0 0 300 242" role="img" aria-label="个人能力与岗位基线雷达图">
                  <polygon v-for="guide in [100, 66, 33]" :key="guide" :points="radarGuidePoints(guide)" class="radar-guide" />
                  <line v-for="(_, index) in radarItems" :key="index" x1="150" y1="118" :x2="radarPoint(index, 100).split(',')[0]" :y2="radarPoint(index, 100).split(',')[1]" class="radar-axis" />
                  <polygon :points="radarTargetPoints" class="radar-target" />
                  <polygon :points="radarUserPoints" class="radar-user" />
                  <circle v-for="(item, index) in radarItems" :key="item.label" :cx="radarPoint(index, item.score).split(',')[0]" :cy="radarPoint(index, item.score).split(',')[1]" r="4" class="radar-dot" />
                  <text v-for="(item, index) in radarItems" :key="`${item.label}-label`" :x="radarLabelPoints[index].x" :y="radarLabelPoints[index].y" text-anchor="middle">{{ item.label }}</text>
                </svg>
              </article>
              <article class="fit-card">
                <header><span>目标岗位对比</span><h3>结构设计岗要求</h3><p>当前能力与目标岗位基线的距离</p></header>
                <div class="fit-list">
                  <div v-for="item in jobFitBars" :key="item.label" class="fit-row">
                    <div><b>{{ item.label }}</b><span>当前 {{ item.value }} / 目标 {{ item.target }}</span></div>
                    <div class="fit-track"><i :class="`fit-bar--${item.tone}`" :style="{ width: `${item.value}%` }" /><em :style="{ left: `${item.target}%` }" /></div>
                  </div>
                </div>
                <footer><span>优先补齐</span><b>可访问作品集与工程化项目证据</b></footer>
              </article>
            </div>
            <div class="pan-heatmap">
              <div v-for="d in dimensions" :key="d.name" class="heat-cell" :class="toneOf(d.score)">
                <span class="heat-name">{{ d.name }}</span>
                <b class="heat-score">{{ d.score }}</b>
              </div>
            </div>
            <ul class="pan-bars">
              <li v-for="d in dimensions" :key="d.name">
                <span class="dim-name">{{ d.name }}</span>
                <div class="dim-track"><i :class="toneOf(d.score)" :style="{ width: `${d.score}%` }"></i></div>
                <b class="dim-score" :class="toneOf(d.score)">{{ d.score }}</b>
              </li>
            </ul>
          </section>

          <section id="directions" class="rp-directions">
            <header class="dir-head">
              <h2>方向方案对比</h2>
              <span class="dir-sub">主攻 / 平行 / 保底三档，匹配度与关键差距一目了然</span>
            </header>
            <div class="dir-table-wrap">
              <table class="dir-table">
                <thead>
                  <tr><th>对比维度</th><th v-for="d in directions" :key="d.title" :class="{ recommended: d.strategy === 'primary' }">{{ d.label }}</th></tr>
                </thead>
                <tbody>
                  <tr><th>方向名称</th><td v-for="d in directions" :key="d.title" :class="{ recommended: d.strategy === 'primary' }"><b>{{ d.title }}</b></td></tr>
                  <tr><th>匹配度</th><td v-for="d in directions" :key="d.title" :class="{ recommended: d.strategy === 'primary' }"><strong>{{ d.matchScore }}%</strong></td></tr>
                  <tr><th>定位依据</th><td v-for="d in directions" :key="d.title" :class="{ recommended: d.strategy === 'primary' }">{{ d.rationale }}</td></tr>
                  <tr><th>关键差距</th><td v-for="d in directions" :key="d.title" :class="{ recommended: d.strategy === 'primary' }"><span v-for="g in d.gaps" :key="g" class="gap-tag">{{ g }}</span></td></tr>
                </tbody>
              </table>
            </div>
          </section>

          <section id="clover" class="rp-clover">
            <header class="clover-head">
              <h2>三叶草模型</h2>
              <span class="clover-sub">兴趣 × 能力 × 价值，交集即理想职业</span>
            </header>
            <div class="clover-body">
              <svg class="venn" viewBox="0 0 300 250" role="img" aria-label="三叶草模型韦恩图">
                <circle cx="150" cy="80" r="66" class="venn-int" />
                <circle cx="95" cy="168" r="66" class="venn-skill" />
                <circle cx="205" cy="168" r="66" class="venn-val" />
                <text x="150" y="70" class="venn-label">兴趣</text>
                <text x="150" y="90" class="venn-score">{{ clover.interest }}</text>
                <text x="95" y="158" class="venn-label">能力</text>
                <text x="95" y="178" class="venn-score">{{ clover.ability }}</text>
                <text x="205" y="158" class="venn-label">价值</text>
                <text x="205" y="178" class="venn-score">{{ clover.value }}</text>
                <text x="150" y="152" class="venn-core">✦</text>
              </svg>
              <ul class="clover-items">
                <li class="c-int">
                  <span>兴趣</span>
                  <div class="track"><i :style="{ width: `${clover.interest}%` }"></i></div>
                  <b>{{ clover.interest }}</b>
                  <p>{{ cloverNotes.interest }}</p>
                </li>
                <li class="c-skill">
                  <span>能力</span>
                  <div class="track"><i :style="{ width: `${clover.ability}%` }"></i></div>
                  <b>{{ clover.ability }}</b>
                  <p>{{ cloverNotes.ability }}</p>
                </li>
                <li class="c-val">
                  <span>价值</span>
                  <div class="track"><i :style="{ width: `${clover.value}%` }"></i></div>
                  <b>{{ clover.value }}</b>
                  <p>{{ cloverNotes.value }}</p>
                </li>
              </ul>
            </div>
          </section>

          <section id="profile" class="rp-profile">
            <header class="prof-head">
              <h2>个人画像</h2>
              <span class="prof-sub">对话中沉淀的学业、技能与兴趣价值</span>
            </header>
            <div class="prof-grid">
              <article v-for="item in profileItems" :key="item.key" :class="`prof-${item.tone}`">
                <div class="prof-icon">{{ item.label.slice(0, 1) }}</div>
                <div class="prof-body">
                  <div class="prof-title"><b>{{ item.label }}</b><em :class="`prof-status--${item.tone}`">{{ item.status }}</em></div>
                  <p>{{ item.value }}</p>
                </div>
              </article>
            </div>
          </section>

          <section id="action" class="rp-action">
            <header class="act-head">
              <h2>行动计划</h2>
              <span class="act-sub">按时间窗口拆成今天就能勾掉的小任务</span>
            </header>
            <ol class="act-timeline">
              <li v-for="(phase, index) in actionPhases" :key="phase.month" :class="`act-${phase.tone}`">
                <span class="act-node">{{ index + 1 }}</span>
                <div class="act-body">
                  <div class="act-top"><b class="act-month">{{ phase.month }}</b><em>{{ phase.title }}</em></div>
                  <p>{{ phase.detail }}</p>
                </div>
              </li>
            </ol>
          </section>

          <ReportSection v-for="section in otherSections" :key="String(section.id)" :section="section" />
          <p v-if="!sections.length" class="rp-empty">暂无报告正文。完成诊断后，这里会呈现完整报告。</p>
        </div>
      </div>

      <p v-if="exportNotice" class="rp-notice" role="status">{{ exportNotice }}</p>

      <GrowthShareCard />
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
</style>

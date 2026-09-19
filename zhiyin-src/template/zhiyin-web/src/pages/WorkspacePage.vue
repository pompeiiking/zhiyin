<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { ProfilePanelView, StagePanelView } from '@/api/schema'
import { trackEvent } from '@/api/endpoints'
import { useWorkspaceStore } from '@/stores/workspace'
import { agentCatalog, useAgentsStore } from '@/stores/agents'
import { useSessionStore } from '@/stores/session'
import TheoryTag from '@/components/conversation/TheoryTag.vue'
import MockBadge from '@/components/common/MockBadge.vue'
import CoachMessageStream from '@/components/workspace/CoachMessageStream.vue'

// 智能工作台 #screen-wb（P0，登录用户）。
// 「职业成长主页」形态：hero（含五环节闭环）→ 智能体矩阵 → 双列（左：诊断+时间线，右：画像·日历·成就）。
const store = useWorkspaceStore()
const agents = useAgentsStore()
const session = useSessionStore()
const router = useRouter()

const owner = computed(() => session.identity.nickname || '演示用户')

const profile = computed(() => store.profilePanel as unknown as ProfilePanelView | null)
const reportPanel = computed(() => store.reportPanel as unknown as StagePanelView | null)
const planPanel = computed(() => store.planPanel as unknown as StagePanelView | null)
const actionPanel = computed(() => store.actionPanel as unknown as StagePanelView | null)
const reviewPanel = computed(() => store.reviewPanel as unknown as StagePanelView | null)

const coverage = computed(() => Math.round((profile.value?.coverage ?? 0) * 100))
const confidence = computed(() => Math.round((profile.value?.overall_confidence ?? 0) * 100))
const profileFields = computed(() => (profile.value?.fields ?? []) as Array<Record<string, unknown>>)
const profileGaps = computed(() => (profile.value?.gaps ?? []) as Array<Record<string, unknown>>)

// 15 维结论复用 agents store（与报告页 / 对话页同源），不另写一套维度与阈值。
const matchScore = computed(() => agents.analysis?.matchScore ?? 0)
const groups = computed(() => agents.analysisGroups)
const swot = computed(() => [
  { key: 'strong', label: '优势', tone: 'green', items: groups.value.strong },
  { key: 'option', label: '机会', tone: 'blue', items: groups.value.option },
  { key: 'gap', label: '待补', tone: 'amber', items: groups.value.gap },
  { key: 'risk', label: '风险', tone: 'red', items: groups.value.risk },
])

// 轴 B · 五环节闭环（含再入环）。
const loopStages = [
  { stage: 'collect', label: '采集建模', status: 'done' },
  { stage: 'diagnose', label: '诊断匹配', status: 'done' },
  { stage: 'decide', label: '决策', status: 'done' },
  { stage: 'act', label: '行动', status: 'current' },
  { stage: 'review', label: '复盘校准', status: 'next' },
]

// 轴 A 纠正入口（WB-009）
const correcting = ref(false)
const correction = ref('')
const correctionDone = ref(false)
function submitCorrection() {
  correctionDone.value = true
  void trackEvent('wb_axis_correct', { text: correction.value }).catch(() => {})
}

// 长期跟踪时间线：五环节资产链（画像 → 诊断 → 方案 → 计划 → 复盘）。
interface TimelineNode {
  no: number
  title: string
  detail: string
  status: 'done' | 'current' | 'next'
  time: string
  theories: Array<Record<string, unknown>>
  diff: string | null
}
const timeline = computed<TimelineNode[]>(() => [
  { no: 1, title: '完成对话建档', detail: `画像覆盖度 ${coverage.value}% · 置信度 ${confidence.value}%`, status: 'done', time: String(profile.value?.updated_at ?? '今天 10:24'), theories: [], diff: null },
  { no: 2, title: '完成 15 维深度解析', detail: String(reportPanel.value?.evaluation ?? '生成诊断报告'), status: 'done', time: String(reportPanel.value?.updated_at ?? '今天 11:02'), theories: (reportPanel.value?.theory_models ?? []) as Array<Record<string, unknown>>, diff: reportPanel.value?.diff ?? null },
  { no: 3, title: '选定主攻方向', detail: String(planPanel.value?.evaluation ?? '方向方案'), status: 'done', time: String(planPanel.value?.updated_at ?? '今天 11:20'), theories: (planPanel.value?.theory_models ?? []) as Array<Record<string, unknown>>, diff: planPanel.value?.diff ?? null },
  { no: 4, title: '生成行动计划', detail: String(actionPanel.value?.evaluation ?? '行动计划'), status: 'current', time: String(actionPanel.value?.updated_at ?? '今天 11:40'), theories: (actionPanel.value?.theory_models ?? []) as Array<Record<string, unknown>>, diff: actionPanel.value?.diff ?? null },
  { no: 5, title: '节点提醒 · 网申', detail: String(reviewPanel.value?.evaluation ?? '持续校准'), status: 'next', time: String(reviewPanel.value?.updated_at ?? '昨天 20:15'), theories: (reviewPanel.value?.theory_models ?? []) as Array<Record<string, unknown>>, diff: reviewPanel.value?.diff ?? null },
])

const openNode = ref<number | null>(2)
function toggleNode(no: number) {
  openNode.value = openNode.value === no ? null : no
}

// 关键节点日历（演示）。
const calendar = [
  { date: '09.12', title: '简历重写 + 投递 5 家设计院', countdown: '6 天后', urgent: true },
  { date: '09.30', title: 'PKPM / YJK 突击计划截止', countdown: '24 天后', urgent: false },
  { date: '10.15', title: '校园宣讲会 + 内推盘点', countdown: '39 天后', urgent: false },
  { date: '10.31', title: '笔试面试模拟 ×3', countdown: '55 天后', urgent: false },
]

// 成长与成就（演示）。
const badges = [
  { char: '像', label: '画像建立者', on: true },
  { char: '报', label: '首份分析报告', on: true },
  { char: '向', label: '已选定方向', on: true },
  { char: '连', label: '连续在线 7 天', on: false },
  { char: '行', label: '行动派 · 完成 10 项任务', on: false },
  { char: '职', label: '首个 Offer', on: false },
]

// 智能体最近动态（演示，对应 agentCatalog）。
const agentActivity: Record<string, string> = {
  profile_analyst: '最近更新 · 今天 10:24',
  career_advisor: '最近分析 · 今天 11:02',
  path_planner: '当前 · 行动进行中',
  companion_coach: '刚刚 · 已发出 2 条提醒',
  info_scout: '最近同步 · 今天 06:00',
}

function goAgent(id: string) {
  void trackEvent('wb_agent_open', { agent_id: id }).catch(() => {})
  router.push({ name: 'agentDetail', params: { agentId: id } })
}

function goReport() {
  void trackEvent('diagnosis_view', { source: 'workspace' }).catch(() => {})
  router.push({ name: 'report' })
}

onMounted(() => {
  void store.load()
  agents.ensureDemoAnalysis()
  void trackEvent('wb_enter', {}).catch(() => {})
})
</script>

<template>
  <main data-anchor="screen-wb" class="wb-page">
    <div class="wb-container">
      <!-- hero：标题 + 覆盖度环 + 五环节闭环（内嵌，不单独成卡） -->
      <header class="wb-hero">
        <span class="hero-glow hero-glow-a" aria-hidden="true"></span>
        <span class="hero-glow hero-glow-b" aria-hidden="true"></span>
        <MockBadge class="hero-badge" source="demo" />

        <div class="hero-main">
          <span class="hero-tag">数据闭环 · 持续校准</span>
          <h1>{{ owner }} 的智能工作台</h1>
          <p class="hero-sub">五个智能体围绕同一份画像持续协作，报告、方案与计划随你成长不断更新。</p>
          <div class="hero-meta">
            <span class="hero-stage">当前阶段 · {{ store.axisAStage }}</span>
            <button type="button" class="hero-correct" :aria-expanded="correcting" @click="correcting = !correcting">
              {{ correcting ? '收起' : '不是这样，纠正' }}
            </button>
          </div>
          <div v-if="correcting" class="correct-panel">
            <textarea v-model="correction" rows="2" placeholder="说说你现在的真实状态…"></textarea>
            <button type="button" @click="submitCorrection">提交纠正</button>
            <p v-if="correctionDone" class="correct-done">已记录（演示），正式实现会反馈到阶段推断。</p>
          </div>
        </div>

        <div class="hero-side">
          <div class="hero-ring" :style="{ '--score': `${coverage * 3.6}deg` }">
            <div><strong>{{ coverage }}%</strong><span>画像覆盖</span></div>
          </div>
          <p class="hero-since">陪伴第 <b>18</b> 天 · 累计 <b>7</b> 次对话</p>
        </div>

        <ol class="wb-loop" aria-label="五环节闭环">
          <li v-for="(s, i) in loopStages" :key="s.stage" :class="s.status">
            <i>{{ i + 1 }}</i><span>{{ s.label }}</span>
          </li>
        </ol>
      </header>

      <!-- 智能体协作矩阵 -->
      <section class="wb-agents" aria-label="智能体协作矩阵">
        <header class="sec-head">
          <div><h2>五个智能体协作</h2></div>
          <p>围绕同一份画像持续协作，谁负责哪一环节一目了然。</p>
        </header>
        <div class="agent-grid">
          <button v-for="agent in agentCatalog" :key="agent.id" type="button" class="agent-card" :class="agent.theme" @click="goAgent(agent.id)">
            <span class="ac-ico">{{ agent.shortName }}</span>
            <span class="ac-body">
              <span class="ac-top"><b>{{ agent.name }}</b><em :class="agent.statusTone">{{ agent.status }}</em></span>
              <span class="ac-role">{{ agent.role }}</span>
              <span class="ac-time">{{ agentActivity[agent.id] ?? '—' }}</span>
            </span>
          </button>
        </div>
      </section>

      <!-- 双列：左（诊断结论 + 时间线）/ 右（画像 · 日历 · 成就） -->
      <div class="wb-grid">
        <div class="col-main">
          <section class="wb-diag" aria-label="最新诊断结论">
            <header class="sec-head">
              <div><h2>诊断结论</h2></div>
              <button type="button" class="link-btn" @click="goReport">查看完整报告 →</button>
            </header>
            <div class="diag-top">
              <div class="diag-score">
                <strong>{{ matchScore }}</strong>
                <span>综合匹配度</span>
              </div>
              <p class="diag-conclusion">{{ reportPanel?.evaluation ?? '尚未生成诊断结论，先完成对话建档。' }}</p>
            </div>
            <div class="diag-swot">
              <div v-for="s in swot" :key="s.key" :class="`swot-cell t-${s.tone}`">
                <b>{{ s.label }}</b>
                <em>{{ s.items.length }}</em>
                <p>{{ s.items.slice(0, 3).join(' · ') || '—' }}</p>
              </div>
            </div>
          </section>

          <section class="wb-timeline" aria-label="长期跟踪时间线">
            <header class="sec-head">
              <div><h2>成长时间线</h2></div>
            </header>
            <ol class="tl">
              <li v-for="(node, i) in timeline" :key="node.no" :class="node.status">
                <div class="tl-rail" aria-hidden="true">
                  <span class="tl-dot">{{ node.no }}</span>
                  <span v-if="i < timeline.length - 1" class="tl-line"></span>
                </div>
                <button type="button" class="tl-node" :aria-expanded="openNode === node.no" @click="toggleNode(node.no)">
                  <span class="tl-head"><b>{{ node.title }}</b><span class="tl-time">{{ node.time }}</span></span>
                  <span class="tl-detail">{{ node.detail }}</span>
                </button>
                <div v-if="openNode === node.no" class="tl-extra">
                  <div v-if="node.theories.length" class="tl-block">
                    <span class="tl-label">理论依据</span>
                    <div class="tl-theories"><TheoryTag v-for="(t, ti) in node.theories" :key="ti" :theory="t" /></div>
                  </div>
                  <div class="tl-block">
                    <span class="tl-label">历史差异</span>
                    <p v-if="node.diff" class="tl-diff">{{ node.diff }}</p>
                    <p v-else class="tl-empty">暂无差异，资产尚未因新信息重算。</p>
                  </div>
                </div>
              </li>
            </ol>
          </section>
        </div>

        <div class="col-side">
          <section class="wb-profile" aria-label="画像状态">
            <header class="sec-head">
              <div><h2>个人画像</h2></div>
            </header>
            <div class="prof-stats">
              <div><b>{{ coverage }}%</b><span>字段覆盖</span></div>
              <div><b>{{ confidence }}%</b><span>置信度</span></div>
            </div>
            <ul class="prof-fields">
              <li v-for="f in profileFields" :key="String(f.name)">
                <span class="pf-name">{{ String(f.name) }}</span>
                <span class="pf-value">{{ String(f.value ?? '—') }}</span>
                <i :class="f.status === 'done' ? 'ok' : 'pending'"></i>
              </li>
            </ul>
            <p v-if="profileGaps.length" class="prof-gap">待补：{{ profileGaps.map((g) => String(g.name)).join('、') }}</p>
          </section>

          <section class="wb-calendar" aria-label="关键节点日历">
            <header class="sec-head">
              <div><h2>关键节点</h2></div>
            </header>
            <ul class="cal-list">
              <li v-for="item in calendar" :key="item.date" :class="{ urgent: item.urgent }">
                <span class="cal-date">{{ item.date }}</span>
                <span class="cal-title">{{ item.title }}</span>
                <span class="cal-count">{{ item.countdown }}</span>
              </li>
            </ul>
          </section>

          <section class="wb-badges" aria-label="成长与成就">
            <header class="sec-head">
              <div><h2>成长与成就</h2></div>
            </header>
            <div class="badge-grid">
              <div v-for="b in badges" :key="b.label" :class="{ on: b.on }">
                <span class="badge-ico">{{ b.char }}</span>{{ b.label }}
              </div>
            </div>
          </section>
        </div>
      </div>

      <!-- 今日行动 · 教练建议 -->
      <CoachMessageStream />
    </div>
  </main>
</template>

<style scoped>
.wb-page {
  min-height: 100%;
  background: var(--paper);
}

.wb-container {
  max-width: var(--content-max-width);
  margin-inline: auto;
  padding: var(--space-8) var(--page-gutter) var(--space-16);
  display: grid;
  gap: var(--space-7);
}

/* 智能体主题色（与 agentCatalog.theme 对应） */
.a-blue { --c: var(--blue); --cSoft: var(--blueSoft); }
.a-green { --c: var(--greenD); --cSoft: var(--greenSoft); }
.a-amber { --c: var(--amber); --cSoft: var(--amberSoft); }
.a-violet { --c: var(--violet); --cSoft: var(--purpleSoft); }
.a-slate { --c: var(--color-text-secondary); --cSoft: var(--color-bg); }

/* ============ hero ============ */
.wb-hero {
  position: relative;
  overflow: hidden;
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-areas: 'main side' 'loop loop';
  gap: var(--space-5) var(--space-8);
  align-items: center;
  padding: var(--space-8) var(--space-8) var(--space-7);
  border-radius: var(--radius-xl, 20px);
  color: #fff;
  background: linear-gradient(135deg, #16283c, var(--blueD) 60%, var(--blue));
}

.hero-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(48px);
  opacity: 0.4;
  pointer-events: none;
}

.hero-glow-a { top: -80px; right: 6%; width: 260px; height: 260px; background: #fff; }
.hero-glow-b { bottom: -100px; left: 36%; width: 300px; height: 300px; background: var(--green); }

.hero-badge {
  position: absolute;
  top: var(--space-5);
  right: var(--space-6);
  z-index: 2;
}

.hero-main { grid-area: main; position: relative; z-index: 1; }

.hero-tag {
  display: inline-block;
  padding: 3px 10px;
  border: 1px solid rgb(255 255 255 / 35%);
  border-radius: var(--radius-pill);
  background: rgb(255 255 255 / 12%);
  font-size: var(--font-size-xs);
  font-weight: 700;
  letter-spacing: 0.04em;
}

.hero-main h1 {
  margin: var(--space-4) 0 0;
  font-size: var(--font-size-3xl);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.hero-sub {
  margin: 10px 0 0;
  max-width: 540px;
  font-size: var(--font-size-sm);
  line-height: 1.7;
  opacity: 0.9;
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
  margin-top: var(--space-5);
}

.hero-stage {
  padding: 5px 14px;
  border-radius: var(--radius-pill);
  background: rgb(255 255 255 / 16%);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.hero-correct {
  padding: 5px 14px;
  border: 1px solid rgb(255 255 255 / 45%);
  border-radius: var(--radius-pill);
  background: transparent;
  color: #fff;
  font-size: var(--font-size-xs);
  cursor: pointer;
}

.correct-panel {
  display: grid;
  gap: var(--space-2);
  margin-top: var(--space-3);
  max-width: 420px;
}

.correct-panel textarea {
  width: 100%;
  padding: var(--space-3);
  border: 0;
  border-radius: var(--radius-sm);
  background: rgb(255 255 255 / 95%);
  color: var(--color-text-primary);
  font-size: var(--font-size-xs);
  resize: vertical;
}

.correct-panel button {
  justify-self: start;
  padding: 6px 14px;
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--color-action-bg);
  color: #fff;
  font-size: var(--font-size-xs);
  font-weight: 600;
  cursor: pointer;
}

.correct-done { margin: 0; font-size: var(--font-size-xs); color: #d9ffe9; }

.hero-side {
  grid-area: side;
  position: relative;
  z-index: 1;
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  align-self: center;
}

.hero-ring {
  position: relative;
  display: grid;
  width: 176px;
  height: 176px;
  place-items: center;
  border-radius: 50%;
  background: conic-gradient(#fff var(--score), rgb(255 255 255 / 20%) 0);
}

.hero-ring::before {
  position: absolute;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--blueD), var(--blue));
  content: '';
}

.hero-ring div { position: relative; z-index: 1; display: grid; text-align: center; }
.hero-ring strong { font-size: 40px; line-height: 1; }
.hero-ring span { margin-top: 6px; font-size: var(--font-size-xs); opacity: 0.9; }

.hero-since { margin: 0; font-size: var(--font-size-xs); opacity: 0.88; }
.hero-since b { font-weight: 800; }

/* 五环节闭环（内嵌 hero，铺满整行） */
.wb-loop {
  grid-area: loop;
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  margin: 0;
  padding: var(--space-5) 0 0;
  border-top: 1px solid rgb(255 255 255 / 16%);
  list-style: none;
}

.wb-loop li {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: rgb(255 255 255 / 72%);
  white-space: nowrap;
}

.wb-loop li {
  flex: 1;
}

.wb-loop li:not(:last-child)::after {
  content: '';
  flex: 1;
  height: 2px;
  margin: 0 12px;
  border-radius: 2px;
  background: rgb(255 255 255 / 22%);
}

.wb-loop i {
  font-style: normal;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex: none;
  border-radius: 50%;
  border: 1.5px solid rgb(255 255 255 / 45%);
  font-size: 12px;
}

.wb-loop li.done { color: #fff; }
.wb-loop li.done i { background: #fff; border-color: #fff; color: var(--blueD); }
.wb-loop li.done:not(:last-child)::after { background: rgb(255 255 255 / 55%); }
.wb-loop li.current i { background: var(--green); border-color: var(--green); color: #fff; box-shadow: 0 0 0 5px rgb(56 185 121 / 25%); }
.wb-loop li.next { opacity: 0.7; }

/* ============ 通用小节 ============ */
.sec-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  margin-bottom: var(--space-4);
}

.sec-head h2 {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 800;
  letter-spacing: -0.01em;
}

.sec-head > p { margin: 0; color: var(--color-text-secondary); font-size: var(--font-size-xs); }

.link-btn {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-link);
  font-size: var(--font-size-xs);
  font-weight: 700;
  cursor: pointer;
}

/* 卡片统一：无阴影，仅边框分层，避免「盒中盒」堆叠 */
.wb-agents,
.wb-diag,
.wb-timeline,
.wb-profile,
.wb-calendar,
.wb-badges {
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

/* ============ 智能体矩阵 ============ */
.agent-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-3);
}

.agent-card {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  text-align: left;
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-standard), transform var(--duration-fast) var(--ease-standard);
}

.agent-card:hover { border-color: var(--c); transform: translateY(-2px); }

.ac-ico {
  display: grid;
  width: 40px;
  height: 40px;
  flex: none;
  place-items: center;
  border-radius: var(--radius-sm);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 800;
  background: var(--c);
}

.ac-body { display: grid; gap: 5px; min-width: 0; }

.ac-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ac-top b { font-size: var(--font-size-sm); font-weight: 700; }

.ac-top em {
  padding: 1px 8px;
  border-radius: var(--radius-pill);
  font-style: normal;
  font-size: var(--font-size-xs);
  font-weight: 700;
  background: var(--cSoft);
  color: var(--c);
}

.ac-role {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  line-height: 1.6;
  min-height: calc(1.6em * 2);
}

.ac-time { color: var(--color-text-muted); font-size: var(--font-size-xs); }

/* ============ 双列 ============ */
.wb-grid {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: var(--space-7);
  align-items: stretch;
}

.col-main,
.col-side {
  display: flex;
  flex-direction: column;
  gap: var(--space-7);
}

/* ============ 诊断结论 ============ */
.diag-top {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.diag-score {
  display: grid;
  place-items: center;
  flex: none;
  min-width: 104px;
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--blueD), var(--blue));
  color: #fff;
}

.diag-score strong { font-size: 40px; line-height: 1; font-weight: 800; }
.diag-score span { margin-top: 6px; font-size: var(--font-size-xs); opacity: 0.9; }

.diag-conclusion {
  margin: 0;
  font-size: var(--font-size-sm);
  line-height: 1.7;
  color: var(--color-text-primary);
}

.diag-swot {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.swot-cell {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.swot-cell b { display: inline-block; font-size: var(--font-size-xs); font-weight: 800; }
.swot-cell em { float: right; font-style: normal; font-size: var(--font-size-xs); font-weight: 800; }
.swot-cell p { margin: 8px 0 0; color: var(--color-text-secondary); font-size: var(--font-size-xs); line-height: 1.6; }

.swot-cell.t-green b, .swot-cell.t-green em { color: var(--greenD); }
.swot-cell.t-blue b, .swot-cell.t-blue em { color: var(--blueD); }
.swot-cell.t-amber b, .swot-cell.t-amber em { color: var(--amber); }
.swot-cell.t-red b, .swot-cell.t-red em { color: var(--red); }

/* ============ 时间线 ============ */
.wb-timeline {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
}

.tl {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  margin: 0;
  padding: 0;
  list-style: none;
}

.tl li {
  display: grid;
  grid-template-columns: 40px 1fr;
  gap: var(--space-3);
  align-items: start;
  flex: 1 1 auto;
  min-height: 0;
}

.tl-rail { display: flex; flex-direction: column; align-items: center; align-self: stretch; }

.tl-dot {
  display: grid;
  width: 32px;
  height: 32px;
  flex: none;
  place-items: center;
  border-radius: 50%;
  background: var(--color-bg);
  color: var(--color-text-secondary);
  font-weight: 800;
  font-size: var(--font-size-xs);
  border: 1.5px solid var(--color-border);
}

.tl-line { flex: 1; width: 2px; margin: 6px 0; background: var(--color-border); }

.tl li.done .tl-dot { background: var(--green); border-color: var(--green); color: #fff; }
.tl li.done .tl-line { background: var(--green); }
.tl li.current .tl-dot { background: var(--blue); border-color: var(--blue); color: #fff; box-shadow: 0 0 0 5px var(--blueSoft); }

.tl-node {
  width: 100%;
  display: grid;
  gap: 4px;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  text-align: left;
  cursor: pointer;
}

.tl-node:hover { background: var(--color-bg); }

.tl-head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-3); flex-wrap: wrap; }
.tl-head b { font-size: var(--font-size-sm); font-weight: 700; }
.tl-time { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.tl-detail { margin: 0; color: var(--color-text-secondary); font-size: var(--font-size-xs); line-height: 1.6; }

.tl-extra {
  grid-column: 2;
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.tl-block { display: grid; gap: 6px; }
.tl-label { color: var(--color-text-muted); font-size: var(--font-size-xs); font-weight: 600; }
.tl-theories { display: flex; flex-wrap: wrap; gap: 6px; }
.tl-diff { margin: 0; color: var(--color-text-primary); font-size: var(--font-size-xs); line-height: 1.7; }
.tl-empty { margin: 0; color: var(--color-text-muted); font-size: var(--font-size-xs); }

/* ============ 画像状态 ============ */
.prof-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.prof-stats > div {
  display: grid;
  gap: 2px;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--greenSoft);
  text-align: center;
}

.prof-stats b { color: var(--greenD); font-size: var(--font-size-xl); font-weight: 800; }
.prof-stats span { color: var(--color-text-secondary); font-size: var(--font-size-xs); }

.prof-fields { display: grid; margin: 0; padding: 0; list-style: none; }

.prof-fields li {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--space-3);
  padding: 7px 0;
  font-size: var(--font-size-xs);
}

.prof-fields li + li { border-top: 1px solid var(--color-border); }

.pf-name { color: var(--color-text-secondary); white-space: nowrap; }
.pf-value { color: var(--color-text-primary); text-align: right; overflow-wrap: anywhere; }
.prof-fields i { width: 8px; height: 8px; border-radius: 50%; }
.prof-fields i.ok { background: var(--color-success); }
.prof-fields i.pending { background: var(--color-text-muted); }

.prof-gap {
  margin: var(--space-3) 0 0;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--amberSoft);
  color: var(--amber);
  font-size: var(--font-size-xs);
  line-height: 1.6;
}

/* ============ 日历 ============ */
.cal-list { display: grid; margin: 0; padding: 0; list-style: none; }

.cal-list li {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  font-size: var(--font-size-xs);
}

.cal-list li + li { border-top: 1px solid var(--color-border); }

.cal-date {
  display: grid;
  min-width: 46px;
  height: 46px;
  place-items: center;
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  font-weight: 700;
}

.cal-list li.urgent .cal-date { background: var(--redSoft); color: var(--red); }
.cal-title { color: var(--color-text-primary); line-height: 1.5; }
.cal-count { color: var(--color-text-muted); white-space: nowrap; }
.cal-list li.urgent .cal-count { color: var(--red); font-weight: 700; }

/* ============ 成就徽章 ============ */
.badge-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-3); }

.badge-grid > div {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.badge-grid > div.on { background: var(--greenSoft); color: var(--greenD); }

.badge-ico {
  display: grid;
  width: 26px;
  height: 26px;
  flex: none;
  place-items: center;
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-weight: 800;
}

.badge-grid > div.on .badge-ico { background: var(--green); color: #fff; }

/* ============ 响应式 ============ */
@media (max-width: 1080px) {
  .agent-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 900px) {
  .wb-hero {
    grid-template-columns: 1fr;
    grid-template-areas: 'main' 'side' 'loop';
  }

  .hero-side {
    grid-template-columns: auto 1fr;
    justify-items: start;
    align-items: center;
  }

  .wb-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .wb-container {
    padding-top: var(--space-6);
  }

  .wb-hero {
    padding: var(--space-6) var(--space-5);
  }

  .hero-main h1 {
    font-size: var(--font-size-2xl);
  }

  .wb-loop {
    flex-wrap: wrap;
    gap: var(--space-3);
  }

  .wb-loop li:not(:last-child) {
    flex: 0 0 auto;
  }

  .wb-loop li:not(:last-child)::after {
    display: none;
  }

  .agent-grid {
    grid-template-columns: 1fr;
  }
}
</style>

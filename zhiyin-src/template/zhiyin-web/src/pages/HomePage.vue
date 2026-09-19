<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useConversationStore } from '@/stores/conversation'
import { enterTask, trackEvent } from '@/api/endpoints'
import { ApiError, ErrorCode } from '@/api/client'
import { useGuestGuard } from '@/composables'
import ShowcaseStage from '@/components/home/ShowcaseStage.vue'
import AgentsShowcase from '@/components/home/AgentsShowcase.vue'
import TaskCardGroup from '@/components/home/TaskCardGroup.vue'
import TrustSection from '@/components/home/TrustSection.vue'

const session = useSessionStore()
const conversation = useConversationStore()
const router = useRouter()
const { handleGuestError } = useGuestGuard()
const selected = ref('')
const busy = ref(false)
const message = ref('')

// 首屏文案来自动态资源（AGENTS.md §8：文案不得硬编码到 Vue）。
// 这里曾写死标题「不用填表，开口就能聊出一条职业路径」，同时副标题宣称
// 「上传简历 或直接对话」——但本期并不接收简历，`faqs.json` 的答复正好相反
// （"我们不接收真实简历…将来若支持上传简历，会作为单独功能另行说明"）。
// 文案包缺失时留空，不退回写死的那一份。
const heroTitle = computed(() => session.copyBundle['home.hero_title'] ?? '')
const heroTitleHl = computed(() => session.copyBundle['home.hero_title_hl'] ?? '')
const heroSub = computed(() => session.copyBundle['home.hero_sub'] ?? '')
const heroNote = computed(() => session.copyBundle['home.hero_note'] ?? '')
// 工作台矩阵（HOME-005）：场景名 / 说明 / 时间窗口 / 状态动作。
// 未开放项点击「预约提醒」会记录一次真实埋点。
// ⚠️ 这里曾为每张卡内联一份"产出样例"（含编造的匹配度数字与节点），已删除：
//    产出只来自真实账号，不在首页预置样例。
const workbenches = [
  { key: 'campus', name: '校招求职', desc: '秋招 / 春招 / 网申窗口，岗位画像与面试节点全流程', window: '秋招 9–11 月 · 春招 3–4 月', audience: '面向大三、大四', open: true, color: 'b-blue' },
  { key: 'postgrad', name: '考研 / 保研 / 留学', desc: '择校定位、备考与申请季时间线', window: '考研 12 月 · 申请季 9–1 月', audience: '面向大三、大四', open: false, color: 'b-green' },
  { key: 'civil', name: '考公 / 考编', desc: '选岗建议、公告节点、备考节奏', window: '国考 11–12 月 · 省考 3–4 月', audience: '面向大四及以上', open: false, color: 'b-amber' },
  { key: 'early', name: '职场新人转型', desc: '0–3 年竞争力校准与进阶路径', window: '全年可进入 · 每季度校准', audience: '面向职场新人', open: false, color: 'b-purple' },
]

const reserved = ref<string[]>([])
function reserve(key: string) {
  if (reserved.value.includes(key)) return
  reserved.value.push(key)
  void trackEvent('home_reserve_click', { code: key }).catch(() => {})
}
watch(() => session.isLoggedIn, loggedIn => {
  if (loggedIn && session.pendingTaskCode) {
    const code = session.pendingTaskCode
    session.pendingTaskCode = ''
    void selectTask(code)
  }
})

// 滚动叙事（§2.5 / HOME-003）：区块进入视口时淡入上移，只触发一次。
let revealObserver: IntersectionObserver | undefined
onMounted(() => {
  const els = document.querySelectorAll<HTMLElement>('.reveal')
  if (!('IntersectionObserver' in window)) {
    els.forEach(el => el.classList.add('is-revealed'))
    return
  }
  revealObserver = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed')
          revealObserver?.unobserve(entry.target)
        }
      })
    },
    { threshold: 0.15 },
  )
  els.forEach(el => revealObserver?.observe(el))
})
onUnmounted(() => revealObserver?.disconnect())

// 首页里所有「开始聊 / 进入工作台」都走同一条兜底入口链路（§4.1 兜底「直接开聊」常驻）：
// 先按 bootstrap 下发的兜底任务入口建出真实任务，再进对话页。
// 曾经这里直接 `router.push` 裸跳对话页——对话页没有当前任务，用户一开口只会失败。
// 拿不到任务入口（bootstrap 未送达）时才退回只切页，由对话页显示空态。
function startChat() {
  const fallback = session.fallbackTaskEntry
  if (fallback) {
    void selectTask(fallback.code)
    return
  }
  void router.push({ name: 'conversation' })
}

function openReport() {
  void trackEvent('diagnosis_view', { source: 'home' }).catch(() => {})
  void router.push({ name: 'report' })
}

async function selectTask(code: string) {
  if (busy.value) return
  const entry = session.taskEntries.find(x => x.code === code)
  if (!entry) return
  selected.value = code
  message.value = ''
  if (!session.isLoggedIn && entry.target_stage != null) {
    session.pendingTaskCode = code
    session.openLogin('已保留你选择的任务，登录后继续。')
    return
  }
  busy.value = true
  try {
    const task = await enterTask(code)
    if (!task?.task_id) throw new Error('Missing task')
    conversation.$patch(state => {
      const index = state.sessions.findIndex(x => x.task_id === task.task_id)
      if (index < 0) state.sessions.push(task)
      else state.sessions[index] = task
      state.currentTaskId = task.task_id
    })
    await router.push({ name: 'conversation' })
  } catch (error) {
    if (handleGuestError(error)) session.pendingTaskCode = code
    else if (error instanceof ApiError && error.code === ErrorCode.STAGE_UNCERTAIN) message.value = '暂时无法确定入口，请选择更贴近当前困惑的任务，或稍后直接开聊。'
    else message.value = '暂时无法进入任务，请稍后重试。你的选择已保留。'
  } finally { busy.value = false }
}
</script>

<template>
  <main data-anchor="screen-home" class="home">
    <!-- HERO -->
    <div class="hero">
      <div class="hero-bg" aria-hidden="true">
        <span class="glow glow-a"></span>
        <span class="glow glow-b"></span>
      </div>
      <div class="hero-float" aria-hidden="true">
        <span class="float-chip f-1 lg">霍兰德 · RIASEC</span>
        <span class="float-chip f-2 sm">画像逐字段沉淀</span>
        <span class="float-chip f-3">五环节闭环</span>
        <span class="float-chip f-4">SMART 目标</span>
        <span class="float-chip f-5 sm">长期跟踪</span>
        <span class="float-chip f-6 lg">CASVE 决策循环</span>
        <span class="float-chip f-7 sm">能力三核</span>
        <span class="float-chip f-8">职业锚 · 价值取向</span>
      </div>
      <div class="container">
        <h1>{{ heroTitle }}<br /><span class="hl">{{ heroTitleHl }}</span></h1>
        <p class="hero-sub">{{ heroSub }}</p>
        <div class="hero-cta">
          <button class="btn btn-pri btn-lg" :disabled="busy" @click="startChat">开始和 AI 聊职业 →</button>
          <button class="btn btn-ghost btn-lg" @click="openReport">打开完整报告 →</button>
        </div>
        <p class="hero-note">{{ heroNote }}</p>

        <div class="hero-preview">
          <div class="hp-shadow-a" aria-hidden="true"></div>
          <div class="hp-shadow-b" aria-hidden="true"></div>
          <div class="hp-card">
            <div class="hp-top"><span class="dot-live"></span><b>你的核心对话</b></div>
            <!-- 这里曾放一张"对话预览卡"，里面的问答与画像覆盖度都是编造的。
                 改为如实说明真实对话在哪里发生。 -->
            <div class="hp-msg ai">
              <p>真实对话在「核心对话页」发生：你说自己的情况，系统边聊边沉淀画像，并逐环节产出报告、方向方案与行动计划。</p>
            </div>
            <div class="hp-msg ai">
              <p>页面不预置任何示例结论；打开工作台与完整报告页看到的就是你账号的真实产出。</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 任务卡组（§4.1 页面结构：主区 → 任务卡组 → 信任区 → 页脚）：7 条入口全部来自 bootstrap -->
    <TaskCardGroup :selected="selected" :busy="busy" :message="message" @select="selectTask" />

    <!-- 信任区：横幅 / 信任背书 / FAQ，三块内容全部来自 bootstrap，前端不写死文案 -->
    <TrustSection />

    <ShowcaseStage @start="startChat" />

    <!-- AGENTS -->
    <AgentsShowcase />

    <!-- WORKBENCH -->
    <div class="sec" id="workbench">
      <div class="container">
        <div class="head">
          <h2>选择职业工作台</h2>
          <p>按你的阶段与方向选择入口；各工作台共用解析引擎，配备专属规划模板与时间线。先做透「校招求职」，其余陆续开放。</p>
        </div>
        <div class="cats">
          <div
            v-for="(w, i) in workbenches"
            :key="w.key"
            class="cat reveal"
            :class="[w.color, { soon: !w.open }]"
            :style="{ transitionDelay: (i * 0.06).toFixed(2) + 's' }"
          >
            <span class="swatch"></span>
            <span class="cn">{{ w.name }}</span>
            <span class="ds">{{ w.desc }}</span>
            <span class="win">{{ w.window }}</span>
            <span class="meta">
              <span>{{ w.audience }}</span>
              <span v-if="w.open" class="tag-open">已开放 ↗</span>
              <span v-else class="tag-soon">即将开放</span>
            </span>
            <button v-if="w.open" class="wb-action" type="button" :disabled="busy" @click="startChat">进入 ↗</button>
            <button v-else class="wb-action" type="button" :class="{ reserved: reserved.includes(w.key) }" @click="reserve(w.key)">
              {{ reserved.includes(w.key) ? '已登记 ✓' : '预约提醒' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- FOOTER -->
    <footer>
      <div class="container">
        <div class="footer-brand"><span class="dot"></span>职引 ZHIYIN</div>
        <p class="footer-tag">面向大学生与职场新人的 AI 职业规划工具</p>
        <div class="footer-meta">
          <div class="footer-item"><b>数据来源</b><span>专业 / 职业知识库、政策与理论卡均登记来源、版本与更新时间；未登记的来源不进入结论。</span></div>
          <div class="footer-item"><b>方法论出处</b><span>舒伯 · 帕森斯 · 霍兰德 · 三叶草 · CD · CASVE · SMART 等职业咨询经典框架。</span></div>
          <div class="footer-item"><b>内容说明</b><span>页面不预置任何演示数据；对话、画像、报告、方案与计划都来自你的真实账号产出，未产出即显示为空。</span></div>
        </div>
      </div>
    </footer>
  </main>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 26px;
  border: none;
  border-radius: var(--pill);
  font-size: 14px;
  font-weight: 600;
  transition: transform 0.15s, box-shadow 0.15s, background 0.15s;
}

.btn:active {
  transform: translateY(1px);
}

.btn-pri {
  background: var(--blue);
  color: #fff;
  box-shadow: 0 8px 20px rgba(55, 138, 221, 0.28);
}

.btn-pri:hover {
  background: var(--blueD);
}

.btn-ghost {
  background: transparent;
  color: var(--gray);
  border: 1px solid var(--line);
}

.btn-ghost:hover {
  border-color: var(--blue);
  color: var(--blue);
}

.btn-lg {
  padding: 15px 34px;
  font-size: 15px;
}

.btn[disabled] {
  opacity: 0.45;
  pointer-events: none;
}

/* Landing: hero */
.hero {
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at 14% 12%, rgba(55, 138, 221, 0.1), transparent 30%),
    radial-gradient(circle at 88% 26%, rgba(56, 185, 121, 0.1), transparent 30%),
    radial-gradient(circle at 60% 96%, rgba(245, 188, 41, 0.08), transparent 34%),
    var(--paper);
  padding: 96px 0 72px;
  text-align: center;
}

.hero .container {
  position: relative;
  z-index: 1;
}

/* HOME-003 动态背景层：分层光晕 + 细网格缓慢流动，作为首屏的技术感记忆点。 */
.hero-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.hero-bg .glow {
  position: absolute;
  width: 520px;
  height: 520px;
  border-radius: 50%;
  filter: blur(70px);
  opacity: 0.55;
}

.hero-bg .glow-a {
  background: radial-gradient(circle, rgba(55, 138, 221, 0.32), transparent 66%);
  top: -140px;
  left: -90px;
  animation: heroDriftA 18s var(--ease-standard) infinite alternate;
}

.hero-bg .glow-b {
  background: radial-gradient(circle, rgba(56, 185, 121, 0.28), transparent 66%);
  bottom: -160px;
  right: -110px;
  animation: heroDriftB 22s var(--ease-standard) infinite alternate;
}

@keyframes heroDriftA {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(64px, 42px) scale(1.12); }
}

@keyframes heroDriftB {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(-52px, -32px) scale(1.08); }
}

/* 首屏浮动小组件：装饰性标签缓慢上下浮动。容器与正文同宽居中，标签贴近两侧而非屏幕边缘。 */
.hero-float {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: min(100%, 1240px);
  z-index: 0;
  pointer-events: none;
}

.float-chip {
  position: absolute;
  padding: 8px 16px;
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-secondary);
  letter-spacing: 0.02em;
  animation: chipFloat 6s var(--ease-standard) infinite;
}

.float-chip.lg {
  padding: 12px 22px;
  font-size: 15px;
  box-shadow: 0 10px 26px rgba(18, 26, 39, 0.14);
}

.float-chip.sm {
  padding: 5px 11px;
  font-size: 11px;
  opacity: 0.85;
}

.float-chip.f-1 { top: 22%; left: 8%; color: var(--green); border-color: var(--greenLine); background: var(--greenSoft); }
.float-chip.f-2 { top: 40%; right: 6%; color: var(--blue); border-color: var(--blueLine); background: var(--blueSoft); animation-delay: 1.2s; }
.float-chip.f-3 { top: 13%; right: 13%; color: var(--amber); border-color: var(--amberLine); background: var(--amberSoft); animation-delay: 2.1s; }
.float-chip.f-4 { bottom: 26%; left: 11%; color: var(--violet); border-color: var(--purpleLine); background: var(--purpleSoft); animation-delay: 0.7s; }
.float-chip.f-5 { bottom: 12%; right: 15%; color: var(--color-text-secondary); animation-delay: 1.7s; }
.float-chip.f-6 { top: 56%; left: 4%; color: var(--blue); border-color: var(--blueLine); background: var(--blueSoft); animation-delay: 3.2s; }
.float-chip.f-7 { top: 66%; right: 8%; color: var(--green); border-color: var(--greenLine); background: var(--greenSoft); animation-delay: 0.4s; }
.float-chip.f-8 { bottom: 6%; left: 14%; color: var(--amber); border-color: var(--amberLine); background: var(--amberSoft); animation-delay: 2.6s; }

@keyframes chipFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12px); }
}

.hero h1 {
  font-size: clamp(36px, 5.8vw, 62px);
  line-height: 1.14;
  font-weight: 780;
  letter-spacing: -0.02em;
  margin: 0 auto;
  max-width: 800px;
}

.hero h1 .hl {
  position: relative;
  color: var(--ink);
}

.hero h1 .hl::after {
  content: "";
  position: absolute;
  left: -2px;
  right: -2px;
  bottom: 6px;
  height: 12px;
  background: linear-gradient(90deg, var(--blueSoft), var(--greenSoft));
  z-index: -1;
  border-radius: 6px;
}

.hero-sub {
  margin: 22px auto 0;
  max-width: 680px;
  color: var(--gray);
  font-size: 17px;
  line-height: 1.75;
}

.hero-sub b {
  color: var(--blue);
}

.hero-cta {
  margin-top: 34px;
  display: flex;
  gap: 16px;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
}

.hero-note {
  margin-top: 16px;
  color: var(--muted);
  font-size: 13.5px;
}

/* hero conversation preview card */
.hero-preview {
  position: relative;
  max-width: 460px;
  margin: 46px auto 6px;
  text-align: left;
}

.hp-shadow-a,
.hp-shadow-b {
  position: absolute;
  inset: 0;
  border-radius: 20px;
  background: var(--card);
  border: 1px solid var(--line);
}

.hp-shadow-a {
  transform: rotate(-3.2deg) translateY(4px);
  box-shadow: var(--shadow);
}

.hp-shadow-b {
  transform: rotate(2.4deg) translateY(2px);
  box-shadow: var(--shadow);
}

.hp-card {
  position: relative;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 20px;
  box-shadow: var(--shadowLg);
  padding: 18px 20px 20px;
  animation: heroFloat 5s ease-in-out infinite;
}

@keyframes heroFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-7px); }
}

.hp-top {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 13px;
  padding-bottom: 12px;
  margin-bottom: 13px;
  border-bottom: 1px solid var(--line);
}

.hp-top .dot-live {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 0 4px var(--greenSoft);
  flex: none;
}

.hp-top b {
  font-weight: 700;
}

.hp-msg {
  font-size: 13px;
  line-height: 1.65;
  border-radius: 14px;
  padding: 9px 13px;
  margin-bottom: 9px;
  max-width: 88%;
}

.hp-msg.ai {
  background: var(--paper);
  border: 1px solid var(--line);
  border-top-left-radius: 4px;
  color: var(--ink);
}

.hp-msg.user {
  background: var(--blue);
  color: #fff;
  border-top-right-radius: 4px;
  margin-left: auto;
  box-shadow: 0 4px 12px rgba(55, 138, 221, 0.22);
}

.hp-msg p {
  margin: 0;
}

/* landing sections common */
.sec {
  padding: 72px 0;
}

.sec .head {
  text-align: center;
  max-width: 660px;
  margin: 0 auto 44px;
}

.sec .head h2 {
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.015em;
  margin: 0;
}

.sec .head p {
  color: var(--gray);
  margin-top: 12px;
}

/* workbench (category) grid */
.cats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.cat {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r);
  padding: 26px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: transform 0.18s, box-shadow 0.18s, border-color 0.18s;
  position: relative;
  overflow: hidden;
  text-align: left;
}

.cat:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadowLg);
  border-color: var(--blueLine);
}

.cat .cn {
  font-size: 19px;
  font-weight: 700;
  margin-top: 2px;
}

.cat .ds {
  color: var(--gray);
  font-size: 13px;
  flex: 1;
}

.cat .meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 600;
  color: var(--gray);
}

.tag-open {
  background: var(--greenSoft);
  color: var(--greenD);
  padding: 4px 12px;
  border-radius: var(--pill);
  font-size: 11.5px;
  font-weight: 700;
}

.tag-soon {
  background: var(--paper);
  color: var(--muted);
  padding: 4px 12px;
  border-radius: var(--pill);
  font-size: 11.5px;
  font-weight: 600;
}

.cat.soon {
  background: var(--card);
  border-style: dashed;
}

.cat.b-blue {
  background: linear-gradient(160deg, #fff, var(--blueSoft));
}

.cat .swatch {
  position: absolute;
  right: -30px;
  top: -30px;
  width: 110px;
  height: 110px;
  border-radius: 50%;
  opacity: 0.55;
  background: var(--blueSoft);
}

.cat.b-green .swatch { background: var(--greenSoft); }
.cat.b-amber .swatch { background: var(--amberSoft); }
.cat.b-purple .swatch { background: var(--purpleSoft); }

.cat .win {
  align-self: flex-start;
  font-size: 12px;
  color: var(--gray);
  padding: 3px 10px;
  border-radius: var(--pill);
  background: var(--paper);
  border: 1px solid var(--line);
}

.cat .wb-action {
  margin-top: 4px;
  width: 100%;
  padding: 10px 0;
  border-radius: var(--pill);
  border: 1px solid var(--blueLine);
  background: var(--blue);
  color: #fff;
  font-weight: 700;
  font-size: 13.5px;
  cursor: pointer;
}

.cat.soon .wb-action {
  background: #fff;
  color: var(--blueD);
}

.cat .wb-action.reserved {
  background: var(--greenSoft);
  color: var(--greenD);
  border-color: var(--greenLine);
  cursor: default;
}

.cat .wb-action:disabled {
  opacity: 0.6;
  cursor: default;
}

/* footer */
footer {
  border-top: 1px solid var(--line);
  padding: 40px 0;
  color: var(--muted);
  font-size: 12.5px;
  text-align: center;
  background: var(--paper);
}

.footer-brand {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 0.02em;
  color: var(--ink);
}

.footer-brand .dot {
  width: 11px;
  height: 11px;
  border-radius: 4px;
  background: var(--blue);
  box-shadow: 0 0 0 4px var(--blueSoft);
}

.footer-tag {
  margin: 8px 0 22px;
}

.footer-meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  text-align: left;
  max-width: 920px;
  margin: 0 auto;
}

.footer-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.footer-item b {
  color: var(--gray);
  font-size: 12px;
  font-weight: 700;
}

.footer-item span {
  color: var(--muted);
  line-height: 1.7;
}

@media (prefers-reduced-motion: reduce) {
  .hp-card { animation: none; }
  .float-chip { animation: none; }
}

@media (max-width: 900px) {
  .hero-float { display: none; }
  .cats { grid-template-columns: repeat(2, 1fr); }
  .footer-meta { grid-template-columns: 1fr; text-align: center; }
  .footer-item { text-align: center; }
}

@media (max-width: 560px) {
  .hero-preview { max-width: 340px; }
  .hp-shadow-a, .hp-shadow-b { display: none; }
  .cats { grid-template-columns: 1fr; }
}
</style>

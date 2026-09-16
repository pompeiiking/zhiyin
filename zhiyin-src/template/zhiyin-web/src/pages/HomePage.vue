<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useConversationStore } from '@/stores/conversation'
import { enterTask } from '@/api/endpoints'
import { ApiError, ErrorCode } from '@/api/client'
import { useGuestGuard } from '@/composables'
import TaskCardGroup from '@/components/home/TaskCardGroup.vue'
import TrustSection from '@/components/home/TrustSection.vue'
import ShowcaseStage from '@/components/home/ShowcaseStage.vue'

const session = useSessionStore()
const conversation = useConversationStore()
const router = useRouter()
const { handleGuestError } = useGuestGuard()
const selected = ref('')
const busy = ref(false)
const message = ref('')
const freeChat = computed(() => session.taskEntries.find(x => x.target_stage == null))
const isGuest = computed(() => !session.isLoggedIn)
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

async function selectTask(code: string) {
  if (busy.value) return
  const entry = session.taskEntries.find(x => x.code === code)
  if (!entry) return
  selected.value = code
  message.value = ''
  if (session.preview) {
    message.value = `已选择「${entry.label}」。当前为只读界面演示，连接服务后才能开始对话。`
    return
  }
  if (!session.isLoggedIn && entry.target_stage != null) {
    session.pendingTaskCode = code
    session.openLogin('已保留你选择的任务，登录后继续。')
    return
  }
  busy.value = true
  try {
    // 首页只负责入口交接，不实现或调用对话域尚未完成的 action。
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
    <!-- 动态背景层（HOME-003）：渐变光晕 + 细网格，缓慢流动 -->
    <div class="bg-layer" aria-hidden="true">
      <i class="glow glow-a"></i>
      <i class="glow glow-b"></i>
      <i class="grid"></i>
    </div>

    <section class="hero container" aria-labelledby="home-title">
      <div class="hero-copy">
        <h1 id="home-title">不用一次想清所有答案，<br />从眼前一个困惑开始，找到你的下一步。</h1>
        <p class="hero-description">有理论依据的职业规划助手，陪你一步步把方向变清晰。</p>
        <div class="hero-actions">
          <button v-if="freeChat" class="primary-action" :disabled="busy" @click="selectTask(freeChat.code)">开始对话 <span aria-hidden="true">→</span></button>
          <a v-else class="primary-action" href="#task-entries">开始对话 <span aria-hidden="true">→</span></a>
          <RouterLink class="secondary-action" :to="{ name: 'report' }">先看示例报告</RouterLink>
        </div>
        <p class="hero-note"><span aria-hidden="true">○</span> 不替你做决定，陪你找到依据。</p>
      </div>

      <!-- 产品实感预览（HOME-002）：真实对话片段 + 画像逐步填充 -->
      <div class="preview" aria-label="产品实感预览">
        <div class="preview-header">产品预览 <span class="preview-tag">演示数据</span></div>
        <div class="preview-chat">
          <div class="pc"><span class="who">顾问</span>你最近更想做什么方向的工作？</div>
          <div class="pc"><span class="who">你</span>想试试数据分析，但不确定合不合适。</div>
          <div class="pc"><span class="who">顾问</span>我帮你把技能、兴趣、价值三块画像补完整，再给结论。</div>
        </div>
        <div class="preview-coverage">
          <div class="cl">画像覆盖度 <b>3 / 6</b></div>
          <div class="cb"><i></i></div>
        </div>
      </div>
    </section>

    <div class="container">
      <TrustSection class="reveal" />
      <ShowcaseStage />
      <TaskCardGroup class="reveal" :busy="busy" :selected="selected" @select="selectTask" />
      <p v-if="message" class="task-message" role="status">{{ message }}</p>

      <!-- 身份入口（HOME-007）：游客 / 学生 / 导师给不同路径，文案按身份区分 -->
      <section class="identity-entry reveal" aria-labelledby="identity-title">
        <h2 id="identity-title">你是哪种情况？</h2>
        <p class="identity-sub">按你的身份，给你不同的进入路径</p>
        <div class="identity-cards">
          <div class="identity-card" :class="{ current: isGuest }">
            <strong>游客</strong>
            <p>先不登录，直接体验一次对话</p>
            <button type="button" class="identity-action" @click="freeChat ? selectTask(freeChat.code) : session.openLogin()">立即体验</button>
          </div>
          <div class="identity-card" :class="{ current: !isGuest }">
            <strong>学生</strong>
            <p>进入完整任务，逐步建立你的活资产</p>
            <a class="identity-action" href="#task-entries">进入任务</a>
          </div>
          <div class="identity-card">
            <strong>导师</strong>
            <p>查看学生资产并写下建议</p>
            <span class="identity-soon">导师视图即将开放</span>
          </div>
        </div>
      </section>

      <section v-if="session.faqs.length" class="faq reveal" aria-labelledby="faq-title"><div><h2 id="faq-title">开始之前，你可能想知道</h2></div><div class="faq-list"><details v-for="faq in session.faqs" :key="faq.code"><summary>{{ faq.question }}</summary><p>{{ faq.answer }}</p></details></div></section>
    </div>

    <!-- 页脚（HOME-008）：数据来源与方法论脚注，明确标注示例数据 -->
    <footer class="site-footer">
      <div class="footer-inner">
        <p><strong>数据来源与方法论</strong>：演示数据 · 方法论出自职业咨询成熟方法（帕森斯人职匹配、霍兰德 RIASEC、CASVE 决策等）。</p>
        <p><strong>示例数据声明</strong>：本站展示的画像、诊断、方案均为演示数据，不包含任何真实个人信息。</p>
      </div>
    </footer>
  </main>
</template>

<style scoped>
.home {
  position: relative;
  min-height: 100dvh;
}

.bg-layer {
  position: absolute;
  inset: 0 0 auto;
  height: 720px;
  overflow: hidden;
  pointer-events: none;
}

.glow {
  position: absolute;
  width: 520px;
  height: 520px;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.35;
}

.glow-a {
  top: -160px;
  left: -80px;
  background: radial-gradient(circle, var(--color-brand), transparent 70%);
  animation: drift-a 22s ease-in-out infinite alternate;
}

.glow-b {
  top: 40px;
  right: -120px;
  background: radial-gradient(circle, var(--color-role), transparent 70%);
  animation: drift-b 26s ease-in-out infinite alternate;
}

.grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(var(--color-brand-border) 1px, transparent 1px),
    linear-gradient(90deg, var(--color-brand-border) 1px, transparent 1px);
  background-size: 48px 48px;
  opacity: 0.25;
  mask-image: radial-gradient(ellipse at 50% 0%, #000 30%, transparent 75%);
}

@keyframes drift-a {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(60px, 40px) scale(1.08); }
}

@keyframes drift-b {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(-60px, 60px) scale(1.1); }
}

.container {
  position: relative;
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: 0 var(--page-gutter);
}

.hero {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: var(--space-12);
  align-items: center;
  padding-block: 96px var(--space-12);
}

h1 {
  font-size: clamp(30px, 3.4vw, 44px);
  line-height: 1.4;
  letter-spacing: -0.03em;
  margin: 0 0 var(--space-5);
  max-width: 14em;
}

.hero-description {
  color: var(--color-text-secondary);
  font-size: var(--font-size-md);
  line-height: var(--line-height-relaxed);
  margin: 0 0 var(--space-8);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-4);
}

.primary-action {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 48px;
  padding: var(--space-3) var(--space-6);
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--color-action-bg);
  color: var(--color-text-inverse);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  text-decoration: none;
  cursor: pointer;
}

.primary-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.primary-action:hover:not(:disabled) {
  background: var(--color-brand);
}

.hero-note {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin: var(--space-5) 0 0;
}

.preview {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-overlay);
  padding: var(--space-5);
}

.preview-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
}

.preview-tag {
  margin-left: auto;
  padding: 2px var(--space-3);
  border-radius: var(--radius-pill);
  background: var(--color-warning-soft);
  color: var(--color-warning);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-regular);
}

.preview-chat {
  padding-block: var(--space-4);
}

.pc {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-brand-soft);
  margin-bottom: var(--space-2);
  font-size: var(--font-size-sm);
}

.pc:nth-child(2) {
  background: var(--color-role-soft);
}

.who {
  flex-shrink: 0;
  color: var(--color-link);
  font-weight: var(--font-weight-semibold);
}

.preview-coverage {
  padding-top: var(--space-2);
}

.cl {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
}

.cl b {
  color: var(--color-text-primary);
}

.cb {
  height: 10px;
  border-radius: var(--radius-pill);
  background: var(--color-border);
  overflow: hidden;
}

.cb i {
  display: block;
  height: 100%;
  width: 50%;
  border-radius: var(--radius-pill);
  background: var(--color-success);
}

.task-message {
  padding: var(--space-4);
  background: var(--color-brand-soft);
  border: 1px solid var(--color-brand-border);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-8);
}

.faq {
  padding-bottom: var(--space-16);
}

.faq h2 {
  font-size: var(--font-size-xl);
}

.faq details {
  border-bottom: 1px solid var(--color-border);
}

.faq summary {
  padding-block: var(--space-5);
  cursor: pointer;
  font-weight: var(--font-weight-semibold);
}

.faq details p {
  margin-top: 0;
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
}

/* 身份入口（HOME-007） */
.identity-entry {
  padding-block: var(--space-12);
  margin-bottom: var(--space-4);
}

.identity-entry h2 {
  font-size: var(--font-size-xl);
  margin: 0 0 var(--space-2);
}

.identity-sub {
  margin: 0 0 var(--space-6);
  color: var(--color-text-secondary);
}

.identity-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}

.identity-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.identity-card.current {
  border-color: var(--color-brand);
  background: var(--color-brand-soft);
  box-shadow: inset 3px 0 var(--color-brand);
}

.identity-card strong {
  font-size: var(--font-size-md);
}

.identity-card p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.identity-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  margin-top: auto;
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-brand);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--color-link);
  text-decoration: none;
  cursor: pointer;
}

.identity-action:hover {
  background: var(--color-brand);
  color: var(--color-text-inverse);
}

.identity-soon {
  margin-top: auto;
  padding: var(--space-2) 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

/* 页脚（HOME-008） */
.site-footer {
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.footer-inner {
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: var(--space-8) var(--page-gutter);
}

.footer-inner p {
  margin: 0 0 var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.footer-inner strong {
  color: var(--color-text-primary);
}

/* 微交互（§2.5）：主 CTA 按下反馈 */
.primary-action:active:not(:disabled) {
  transform: scale(0.98);
}

.secondary-action {
  display: inline-flex;
  align-items: center;
  min-height: 48px;
  padding: 0 var(--space-5);
  border: 1px solid var(--color-brand-border);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--color-link);
  text-decoration: none;
}

.secondary-action:hover { background: var(--color-brand-soft); }

@media (prefers-reduced-motion: reduce) {
  .glow { animation: none; }
}

/* 响应式三档（HOME-009）：>1280 完整；900–1280 收窄；<900 单列堆叠 */
@media (max-width: 1280px) {
  .hero { gap: var(--space-8); }
}

@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
    gap: var(--space-6);
    padding-top: var(--space-10);
  }
  .preview { margin-top: var(--space-4); }
  .identity-cards { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
  .hero { padding-top: var(--space-8); }
  .bg-layer { height: 560px; }
  .footer-inner { padding-block: var(--space-6); }
}
</style>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'

// 展示台（HOME-004）：五个标签对应五环节，每个标签展示「产出物本身」。
// 以下内容全部为演示数据，仅用于体现「产品会产出什么」，非真实能力。

interface Tab {
  key: string
  no: string
  label: string
  title: string
}

const tabs: Tab[] = [
  { key: 'collect', no: '①', label: '采集建模', title: '对话式建档，画像逐步填充' },
  { key: 'diagnose', no: '②', label: '诊断匹配', title: '15 维逐项比对，差距可溯源' },
  { key: 'decide', no: '③', label: '决策', title: '三套方向方案，可对比可微调' },
  { key: 'act', no: '④', label: '行动', title: '关键节点拆解，任务可勾选' },
  { key: 'review', no: '⑤', label: '复盘校准', title: '长期跟踪，版本随变化更新' },
]

const active = ref('collect')
const index = ref(0)

// ④ 行动：可勾选任务（演示反馈）
const tasks = reactive([
  { id: 't1', text: '整理作品集：2 个课程设计 + 1 个竞赛', done: true },
  { id: 't2', text: '投递 10 家结构设计岗网申', done: false },
  { id: 't3', text: '预约 2 场模拟面试', done: false },
])

// ① 采集建模：可交互体验（HOME-009）。用户亲手回答 3 个关键缺口，实时看到画像沉淀。
interface CollectStep {
  q: string
  options: string[]
  aiReply: string
}
const collectSteps: CollectStep[] = [
  { q: '先问「学业」——你的学校、专业、年级和成绩排名是？', options: ['大四 · 土木工程 · GPA 3.2', '大三 · 计算机 · GPA 3.0'], aiReply: '收到，已沉淀到「学业」。' },
  { q: '再聊聊你上手能用的工具和软件？', options: ['AutoCAD / PKPM / YJK 熟练', 'Python / 数据分析入门'], aiReply: '已沉淀到「技能」。' },
  { q: '有没有和目标岗位相关的实习或项目经历？', options: ['设计院实习 2 个月', '暂无，只有课程设计'], aiReply: '已沉淀到「经历」。' },
]
const collectLog = ref<Array<{ from: 'ai' | 'user'; text: string }>>([])
const collectStep = ref(0)
const collectDone = ref(false)

const coverFields = ['学业', '技能', '经历', '兴趣', '价值观', '目标']
const coveredCount = computed(() => (collectDone.value ? 3 : collectStep.value))

function answerCollect(option: string) {
  if (collectDone.value) return
  const step = collectSteps[collectStep.value]
  collectLog.value.push({ from: 'user', text: option })
  collectLog.value.push({ from: 'ai', text: step.aiReply })
  collectStep.value++
  if (collectStep.value >= collectSteps.length) collectDone.value = true
}

function resetCollect() {
  collectLog.value = []
  collectStep.value = 0
  collectDone.value = false
}

// 交互后自动滚到对话底部，保证新问题/新选项始终可见。
const chatRef = ref<HTMLElement | null>(null)
watch([collectStep, collectDone], async () => {
  await nextTick()
  if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight
})

function select(key: string) {
  active.value = key
  index.value = tabs.findIndex((t) => t.key === key)
}

function next() {
  index.value = (index.value + 1) % tabs.length
  active.value = tabs[index.value].key
}

function prev() {
  index.value = (index.value - 1 + tabs.length) % tabs.length
  active.value = tabs[index.value].key
}

let timer: ReturnType<typeof setInterval> | undefined
function startAuto() {
  if (timer) return
  timer = setInterval(next, 5000)
}
function stopAuto() {
  if (timer) { clearInterval(timer); timer = undefined }
}

function onKey(event: KeyboardEvent) {
  if (event.key === 'ArrowRight') next()
  else if (event.key === 'ArrowLeft') prev()
}

onMounted(() => {
  startAuto()
  window.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  stopAuto()
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <section id="showcase" class="showcase">
    <div class="container">
      <div class="head">
        <h2>一场对话，五环节闭环产出</h2>
        <p>不是文字介绍，而是每个环节真正会交给你的东西——以下为演示数据，仅供预览产品形态。</p>
      </div>

      <div class="stage" @mouseenter="stopAuto" @mouseleave="startAuto">
        <div class="tabs" role="tablist" aria-label="五环节展示台">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            role="tab"
            class="tab"
            :class="{ on: active === tab.key }"
            :aria-selected="active === tab.key"
            :tabindex="active === tab.key ? 0 : -1"
            @click="select(tab.key)"
          >
            <i>{{ tab.no }}</i>{{ tab.label }}
          </button>
        </div>

        <div class="panel">
          <Transition name="stage" mode="out-in">
            <!-- ① 采集建模 -->
            <div v-if="active === 'collect'" key="collect" class="pane">
              <div class="pane-head">
                <h3>{{ tabs[0].title }}</h3>
                <span class="badge-demo">演示数据</span>
              </div>
              <div class="pane-body split">
                <div ref="chatRef" class="chat">
                  <div class="bubble ai">
                    <span class="tag">主理 · 建档分析师</span>
                    <span class="tag theory">帕森斯 · 了解自我</span>
                    <p>我们边聊边建档。你来回答，我实时沉淀到画像。</p>
                  </div>

                  <div v-for="(msg, i) in collectLog" :key="'log' + i" class="bubble" :class="msg.from">
                    <p>{{ msg.text }}</p>
                  </div>

                  <div v-if="!collectDone" class="bubble ai">
                    <p>{{ collectSteps[collectStep].q }}</p>
                  </div>

                  <div v-if="!collectDone" class="collect-options">
                    <button
                      v-for="opt in collectSteps[collectStep].options"
                      :key="opt"
                      type="button"
                      class="collect-option"
                      @click="answerCollect(opt)"
                    >
                      {{ opt }}
                    </button>
                  </div>

                  <div v-else class="collect-complete">
                    <p>已沉淀 3 个关键字段，画像覆盖度实时更新。</p>
                    <button type="button" class="collect-reset" @click="resetCollect">↻ 再体验一次</button>
                  </div>
                </div>
                <div class="coverage">
                  <div class="cov-head"><span>个人画像覆盖度</span><b>{{ coveredCount }} / 6</b></div>
                  <div class="cov-bar"><i :style="{ width: (coveredCount / 6 * 100) + '%' }" /></div>
                  <ul class="cov-list">
                    <li v-for="(f, i) in coverFields" :key="f" :class="{ done: i < coveredCount }">{{ f }}</li>
                  </ul>
                </div>
              </div>
            </div>

            <!-- ② 诊断匹配 -->
            <div v-else-if="active === 'diagnose'" key="diagnose" class="pane">
              <div class="pane-head">
                <h3>{{ tabs[1].title }}</h3>
                <span class="badge-demo">演示数据</span>
              </div>
              <div class="pane-body split">
                <div class="dims">
                  <p class="dims-title">15 维深度解析 · 关键维度差距（要求 − 现状）</p>
                  <div v-for="d in [
                    { name: '结构软件熟练度', now: 78, req: 90 },
                    { name: 'BIM 协同经验', now: 20, req: 70 },
                    { name: '实习 / 项目经历', now: 45, req: 75 },
                    { name: '表达与面试能力', now: 60, req: 80 },
                    { name: '证书 / 资质', now: 30, req: 60 },
                  ]" :key="d.name" class="dim">
                    <span class="dim-name">{{ d.name }}</span>
                    <div class="dim-track"><i class="now" :style="{ width: d.now + '%' }" /><i class="gap" :style="{ left: d.now + '%', width: (d.req - d.now) + '%' }" /></div>
                    <span class="dim-val">{{ d.now }}%</span>
                  </div>
                </div>
                <div class="conclude">
                  <span class="tag theory">结论 · 能力三核</span>
                  <p class="conclude-main">你的技能侧明显偏向「结构设计」，差距集中在 BIM 协同与实习深度上。</p>
                  <ul class="gap-list">
                    <li><b>结构软件</b> 熟练 → 精通（差 1 档）</li>
                    <li><b>BIM 协同</b> 无 → 有（需补 1 段）</li>
                    <li><b>实习经历</b> 1 段 → 2 段（再补 1 段）</li>
                  </ul>
                </div>
              </div>
            </div>

            <!-- ③ 决策 -->
            <div v-else-if="active === 'decide'" key="decide" class="pane">
              <div class="pane-head">
                <h3>{{ tabs[2].title }}</h3>
                <span class="badge-demo">演示数据</span>
              </div>
              <div class="plans">
                <div v-for="p in [
                  { tag: '主攻', name: '结构设计岗', match: '82%', risk: '中', note: '契合度最高，需补 BIM 与实习' },
                  { tag: '平行', name: '施工管理岗', match: '71%', risk: '低', note: '软件与工地协调经验可迁移' },
                  { tag: '保底', name: '造价咨询岗', match: '65%', risk: '低', note: '门槛较低，作为安全选择' },
                ]" :key="p.name" class="plan" :class="p.tag === '主攻' ? 'main' : ''">
                  <span class="plan-tag">{{ p.tag }}</span>
                  <h4>{{ p.name }}</h4>
                  <div class="plan-row"><span>匹配度</span><b>{{ p.match }}</b></div>
                  <div class="plan-row"><span>风险</span><b>{{ p.risk }}</b></div>
                  <p class="plan-note">{{ p.note }}</p>
                </div>
              </div>
            </div>

            <!-- ④ 行动 -->
            <div v-else-if="active === 'act'" key="act" class="pane">
              <div class="pane-head">
                <h3>{{ tabs[3].title }}</h3>
                <span class="badge-demo">演示数据</span>
              </div>
              <div class="pane-body split">
                <ol class="timeline">
                  <li class="done"><b>9 月</b> 网申开放，集中投递</li>
                  <li class="on"><b>10 月</b> 笔试 + 测评</li>
                  <li><b>11 月</b> 面试 + 复试</li>
                  <li><b>12 月</b> offer 与签约</li>
                </ol>
                <ul class="tasks">
                  <li v-for="t in tasks" :key="t.id" :class="{ done: t.done }">
                    <button type="button" class="task-check" :aria-pressed="t.done" @click="t.done = !t.done">{{ t.done ? '✓' : '' }}</button>
                    <span>{{ t.text }}</span>
                  </li>
                </ul>
              </div>
            </div>

            <!-- ⑤ 复盘校准 -->
            <div v-else key="review" class="pane">
              <div class="pane-head">
                <h3>{{ tabs[4].title }}</h3>
                <span class="badge-demo">演示数据</span>
              </div>
              <div class="pane-body split">
                <div class="versions">
                  <div class="ver">
                    <span class="ver-tag">画像 v2</span>
                    <p>因更新「实习经历」，诊断结论从「施工方向」调整为「结构方向」。</p>
                  </div>
                  <div class="coach">
                    <span class="tag theory">教练提醒</span>
                    <p>已 3 天未更新进度，建议补一次面试复盘（约 5 分钟）。</p>
                  </div>
                </div>
                <ol class="timeline">
                  <li class="done"><b>6 月</b> 建档</li>
                  <li class="done"><b>7 月</b> 诊断</li>
                  <li class="done"><b>8 月</b> 决策</li>
                  <li class="on"><b>9 月</b> 行动</li>
                </ol>
              </div>
            </div>
          </Transition>
        </div>

        <div class="stage-foot">
          <button type="button" class="arrow" aria-label="上一个环节" @click="prev">←</button>
          <span class="dots"><i v-for="(tab, i) in tabs" :key="tab.key" :class="{ on: i === index }" /></span>
          <button type="button" class="arrow" aria-label="下一个环节" @click="next">→</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.showcase {
  padding: 72px 0;
  background: var(--color-bg);
  border-top: 1px solid var(--color-border);
}

.container {
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: 0 var(--page-gutter);
}

.head {
  text-align: center;
  max-width: 660px;
  margin: 0 auto 40px;
}

.kicker {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  color: var(--color-text-muted);
}

.head h2 {
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.015em;
  margin: 0;
}

.head p {
  color: var(--color-text-secondary);
  margin: 12px 0 0;
}

.stage {
  max-width: 100%;
  margin: 0 auto;
}

.tabs {
  display: flex;
  gap: var(--space-2);
  flex-wrap: nowrap;
  overflow-x: auto;
  scrollbar-width: none;
}

.tabs::-webkit-scrollbar { display: none; }

.tab {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  white-space: nowrap;
  padding: 10px 18px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-standard);
}

.tab i { font-style: normal; }

.tab.on {
  background: var(--color-brand);
  border-color: var(--color-brand);
  color: #fff;
  box-shadow: 0 6px 16px rgba(55, 138, 221, 0.25);
}

.panel {
  margin-top: var(--space-5);
  height: 460px;
}

.pane {
  height: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  padding: var(--space-6);
}

.pane-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-4);
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.pane-head h3 { margin: 0; font-size: 17px; }

.badge-demo {
  font-size: 10.5px;
  font-weight: 700;
  color: var(--color-warning);
  background: var(--color-warning-soft);
  border: 1px solid var(--color-warning-border);
  padding: 3px 10px;
  border-radius: var(--radius-pill);
}

.pane-body.split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6);
  flex: 1;
  min-height: 0;
}

/* ① 对话 + 覆盖度 */
.chat {
  display: grid;
  gap: 10px;
  align-content: start;
  min-height: 0;
  overflow-y: auto;
}

.bubble {
  max-width: 88%;
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.6;
}

.bubble.ai {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-top-left-radius: 4px;
  color: var(--color-text-primary);
}

.bubble.user {
  background: var(--color-brand);
  color: #fff;
  border-top-right-radius: 4px;
  margin-left: auto;
}

.bubble p { margin: 6px 0 0; }

.tag {
  display: inline-block;
  margin-right: 6px;
  margin-bottom: 2px;
  font-size: 10.5px;
  font-weight: 700;
  color: var(--color-role);
  background: var(--color-role-soft);
  border: 1px solid var(--color-role-border);
  padding: 2px 8px;
  border-radius: var(--radius-pill);
}

.tag.theory {
  color: var(--color-link);
  background: var(--color-brand-soft);
  border-color: var(--color-brand-border);
}

.coverage { align-self: center; }

.cov-head {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.cov-head b { color: var(--color-brand-strong); }

.cov-bar {
  height: 8px;
  margin: 10px 0 16px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}

.cov-bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--color-brand), var(--color-success));
  border-radius: 8px;
  transition: width var(--duration-slow) var(--ease-standard);
}

.cov-list {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0;
  padding: 0;
}

.cov-list li {
  font-size: 13px;
  padding: 4px 11px;
  border-radius: var(--radius-pill);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.cov-list li.done {
  background: var(--color-success-soft);
  border-color: var(--color-success-border);
  color: var(--color-success-strong);
}

/* ① 采集建模 · 可交互体验 */
.collect-options {
  display: grid;
  gap: 8px;
  padding-left: 12%;
}

.collect-option {
  text-align: left;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid var(--color-brand-border);
  background: var(--color-surface);
  color: var(--color-brand-strong);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard), color var(--duration-fast) var(--ease-standard), transform var(--duration-fast) var(--ease-standard);
}

.collect-option:hover {
  background: var(--color-brand);
  color: #fff;
  border-color: var(--color-brand);
  transform: translateX(3px);
}

.collect-complete {
  display: grid;
  gap: 10px;
  padding: 12px 14px;
  border: 1px dashed var(--color-success-border);
  border-radius: 12px;
  background: var(--color-success-soft);
}

.collect-complete p {
  margin: 0;
  font-size: 13px;
  color: var(--color-success-strong);
}

.collect-reset {
  justify-self: start;
  padding: 8px 14px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-success-border);
  background: var(--color-surface);
  color: var(--color-success-strong);
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard), color var(--duration-fast) var(--ease-standard);
}

.collect-reset:hover {
  background: var(--color-success);
  color: #fff;
  border-color: var(--color-success);
}

/* ② 维度 */
.dims-title { margin: 0 0 14px; font-size: 13px; color: var(--color-text-secondary); font-weight: 600; }

.dim { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }

.dim-name { width: 128px; flex: none; font-size: 12.5px; color: var(--color-text-secondary); }

.dim-track {
  position: relative;
  flex: 1;
  height: 10px;
  border-radius: 6px;
  background: var(--color-bg);
  overflow: hidden;
}

.dim-track .now { position: absolute; inset: 0 auto 0 0; background: var(--color-brand); }
.dim-track .gap { position: absolute; top: 0; bottom: 0; background: var(--color-warning); opacity: 0.7; }

.dim-val { width: 38px; flex: none; text-align: right; font-size: 12px; color: var(--color-text-secondary); }

.conclude { align-self: center; }

.conclude-main { margin: 10px 0 14px; font-size: 14px; line-height: 1.6; }

.gap-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }

.gap-list li { font-size: 13px; color: var(--color-text-secondary); padding-left: 12px; border-left: 3px solid var(--color-warning); }

.gap-list b { color: var(--color-text-primary); }

/* ③ 方案 */
.plans { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-4); }

.plan {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  background: var(--color-bg);
}

.plan.main {
  background: var(--color-brand-soft);
  border-color: var(--color-brand-border);
  box-shadow: inset 3px 0 var(--color-brand);
}

.plan-tag {
  font-size: 11px;
  font-weight: 700;
  color: var(--color-brand-strong);
  background: var(--color-surface);
  border: 1px solid var(--color-brand-border);
  padding: 2px 9px;
  border-radius: var(--radius-pill);
}

.plan h4 { margin: 12px 0 14px; font-size: 17px; }

.plan-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--color-text-secondary);
  padding: 6px 0;
  border-bottom: 1px solid var(--color-border);
}

.plan-row b { color: var(--color-text-primary); }

.plan-note { margin: 12px 0 0; font-size: 12.5px; color: var(--color-text-secondary); }

/* ④ 时间线 + 任务 */
.timeline { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }

.timeline li {
  position: relative;
  padding-left: 22px;
  font-size: 13.5px;
  color: var(--color-text-secondary);
}

.timeline li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 4px;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 2px solid var(--color-border);
}

.timeline li b { color: var(--color-text-primary); margin-right: 6px; }

.timeline li.done::before { background: var(--color-success); border-color: var(--color-success); }
.timeline li.on::before { background: var(--color-brand); border-color: var(--color-brand); box-shadow: 0 0 0 4px var(--color-brand-soft); }
.timeline li.on { color: var(--color-text-primary); }

.tasks { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }

.tasks li { display: flex; align-items: center; gap: 10px; font-size: 13.5px; color: var(--color-text-secondary); }

.tasks li.done span { color: var(--color-text-muted); text-decoration: line-through; }

.task-check {
  width: 22px;
  height: 22px;
  flex: none;
  border: 1.5px solid var(--color-border);
  border-radius: 7px;
  background: var(--color-surface);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  display: grid;
  place-items: center;
}

.tasks li.done .task-check { background: var(--color-success); border-color: var(--color-success); }

/* ⑤ 版本 */
.versions { display: grid; gap: 12px; align-content: start; }

.ver, .coach {
  border-radius: var(--radius-md);
  padding: var(--space-4);
  font-size: 13.5px;
  line-height: 1.6;
}

.ver { background: var(--color-bg); border: 1px solid var(--color-border); }
.ver p { margin: 8px 0 0; }
.coach { background: var(--color-role-soft); border: 1px solid var(--color-role-border); }
.coach p { margin: 6px 0 0; }

.ver-tag {
  font-size: 11px;
  font-weight: 700;
  color: var(--color-brand-strong);
  background: var(--color-brand-soft);
  border: 1px solid var(--color-brand-border);
  padding: 2px 9px;
  border-radius: var(--radius-pill);
}

.stage-foot {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  margin-top: var(--space-4);
}

.arrow {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 15px;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-standard);
}

.arrow:hover { border-color: var(--color-brand); color: var(--color-brand); }

.dots { display: flex; gap: 6px; }

.dots i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-border);
  transition: all var(--duration-base) var(--ease-standard);
}

.dots i.on { width: 20px; border-radius: 6px; background: var(--color-brand); }

/* 内容切换过渡（≤ 400ms） */
.stage-enter-active, .stage-leave-active { transition: opacity var(--duration-base) var(--ease-standard), transform var(--duration-base) var(--ease-standard); }
.stage-enter-from { opacity: 0; transform: translateY(8px); }
.stage-leave-to { opacity: 0; transform: translateY(-8px); }

@media (max-width: 900px) {
  .panel { height: auto; }
  .pane-body.split { grid-template-columns: 1fr; }
  .plans { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
  .pane { padding: var(--space-4); }
  .dim-name { width: 96px; }
}
</style>

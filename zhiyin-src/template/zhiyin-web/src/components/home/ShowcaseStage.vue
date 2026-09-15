<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { trackEvent } from '@/api/endpoints'

/**
 * 首页 · 五环节展示台（HOME-004）。
 * 五个标签对应五环节，每个标签展示该环节的「产出物本身」，不是文字介绍。
 * 内容为前端演示数据，已标注「演示数据」，不依赖后端接口（改版 §3.4 / OTH-006）。
 */

const tabs = [
  { key: 'collect', stage: '①', label: '采集建模', intro: '从对话中逐步建立你的职业画像' },
  { key: 'diagnose', stage: '②', label: '诊断匹配', intro: '把画像与目标岗位做逐维比对' },
  { key: 'decide', stage: '③', label: '决策', intro: '给出主攻 / 平行 / 保底三套方向' },
  { key: 'act', stage: '④', label: '行动', intro: '把方向拆成可执行的关键节点' },
  { key: 'review', stage: '⑤', label: '复盘校准', intro: '跟踪变化，持续校准下一步' },
] as const

const active = ref(0)
const paused = ref(false)
let timer: number | undefined

function go(index: number) {
  active.value = (index + tabs.length) % tabs.length
}

// 用户主动切换标签时上报（HOME-011）；自动轮播不视为用户行为，不上报。
function select(index: number) {
  go(index)
  void trackEvent('home_showcase_switch', { stage: tabs[index]?.key ?? '' }).catch(() => {})
}

function next() {
  go(active.value + 1)
}

function prev() {
  go(active.value - 1)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowRight') next()
  else if (e.key === 'ArrowLeft') prev()
}

onMounted(() => {
  // 尊重「减少动态效果」：不自动轮播，仅保留手动切换（§2.5 无障碍降级）。
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    timer = window.setInterval(() => {
      if (!paused.value) next()
    }, 9000)
  }
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
  window.removeEventListener('keydown', onKeydown)
})

// 演示数据：五个环节的产出物示例
const diagnoseGaps = [
  { dim: '数据分析', require: '熟练 SQL', current: '基础 SQL', gap: '缺项目实战' },
  { dim: '沟通表达', require: '能独立汇报', current: '小组汇报经历', gap: '缺独立主讲' },
  { dim: '行业认知', require: '了解目标行业', current: '泛泛了解', gap: '缺一手信息' },
]

const decidePlans = [
  { name: '主攻', target: '数据分析师', match: '82%', risk: '竞争激烈，需补实战' },
  { name: '平行', target: '商业分析', match: '74%', risk: '岗位少，可作备选' },
  { name: '保底', target: '运营数据岗', match: '68%', risk: '门槛较低，先入行' },
]

const actionTasks = [
  { label: '完成一个 SQL 实战项目', done: true },
  { label: '约一位从业者做信息访谈', done: false },
  { label: '投递 3 个实习岗位', done: false },
]

const doneCount = actionTasks.filter((x) => x.done).length

function toggleTask(index: number) {
  actionTasks[index]!.done = !actionTasks[index]!.done
}

// 六维能力雷达图（②诊断匹配的数据可视化，演示数据，§3.4 / §2.5）。
const radarAxes = ['数据分析', '沟通表达', '行业认知', '技能匹配', '学习能力', '实践经验']
const radarValues = [80, 65, 50, 75, 85, 40]

function radarPoint(value: number, index: number, radius: number) {
  const angle = ((-90 + index * 60) * Math.PI) / 180
  const rr = (radius * value) / 100
  return `${(120 + rr * Math.cos(angle)).toFixed(1)},${(120 + rr * Math.sin(angle)).toFixed(1)}`
}

const radarPoints = computed(() =>
  radarValues.map((v, i) => radarPoint(v, i, 88)).join(' '),
)

const radarGrid = [0.33, 0.66, 1].map(scale =>
  radarAxes.map((_, i) => radarPoint(100 * scale, i, 88)).join(' '),
)

const radarLabels = radarAxes.map((label, i) => {
  const angle = ((-90 + i * 60) * Math.PI) / 180
  return {
    label,
    x: Number((120 + 108 * Math.cos(angle)).toFixed(1)),
    y: Number((120 + 108 * Math.sin(angle)).toFixed(1)),
    anchor: i === 0 || i === 3 ? 'middle' : i < 3 ? 'start' : 'end',
  }
})

const radarAxesPoints = radarAxes.map((_, i) => radarPoint(100, i, 88))
</script>

<template>
  <section
    id="showcase"
    class="showcase"
    aria-roledescription="轮播"
    aria-label="五环节产出示例"
    @mouseenter="paused = true"
    @mouseleave="paused = false"
  >
    <div class="showcase-head">
      <h2 class="group-title">看看每个环节，你会得到什么</h2>
      <p class="group-sub">下面是每个环节的产出示例，均为演示数据</p>
    </div>

    <div class="tabs" role="tablist" aria-label="五环节">
      <button
        v-for="(tab, i) in tabs"
        :key="tab.key"
        type="button"
        role="tab"
        :aria-selected="active === i"
        :tabindex="active === i ? 0 : -1"
        class="tab"
        :class="{ 'is-active': active === i }"
        @click="select(i)"
      >
        <span class="stage" aria-hidden="true">{{ tab.stage }}</span>
        {{ tab.label }}
      </button>
    </div>

    <div class="panel" role="tabpanel" :aria-label="tabs[active].label">
      <p class="panel-intro">{{ tabs[active].intro }}</p>

      <!-- ① 采集建模：对话片段 + 画像覆盖度 -->
      <div v-if="tabs[active].key === 'collect'" class="collect">
        <div class="chat-line"><span class="who">顾问</span>你最近更想做「和人打交道」还是「和数据打交道」的工作？</div>
        <div class="chat-line"><span class="who">你</span>更想做数据分析，但不确定自己够不够格。</div>
        <div class="chat-line"><span class="who">顾问</span>收到，我会从技能、兴趣、价值三块帮你把画像补完整。</div>
        <div class="coverage">
          <div class="coverage-label">画像覆盖度 <b>6 / 6</b></div>
          <div class="coverage-bar"><i style="width: 100%"></i></div>
        </div>
      </div>

      <!-- ② 诊断匹配：结论 + 雷达图 + 差距清单 -->
      <div v-else-if="tabs[active].key === 'diagnose'" class="diagnose">
        <p class="verdict">结论：你的技能基础与「数据分析师」匹配度中等，主要差距在实战经验与表达呈现。</p>
        <div class="diagnose-main">
          <svg class="radar" viewBox="0 0 240 240" role="img" aria-label="六维能力雷达图（演示数据）">
            <polygon v-for="(grid, gi) in radarGrid" :key="gi" :points="grid" class="radar-grid" />
            <line
              v-for="(pt, ai) in radarAxesPoints"
              :key="ai"
              x1="120"
              y1="120"
              :x2="pt.split(',')[0]"
              :y2="pt.split(',')[1]"
              class="radar-axis"
            />
            <polygon :points="radarPoints" class="radar-data" />
            <text
              v-for="l in radarLabels"
              :key="l.label"
              :x="l.x"
              :y="l.y"
              :text-anchor="l.anchor"
              class="radar-label"
            >
              {{ l.label }}
            </text>
          </svg>
          <div class="gaps">
            <div v-for="g in diagnoseGaps" :key="g.dim" class="gap-row">
              <span class="dim">{{ g.dim }}</span>
              <span class="require">{{ g.require }}</span>
              <span class="current">{{ g.current }}</span>
              <span class="gap">{{ g.gap }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ③ 决策：三套方案对比 -->
      <div v-else-if="tabs[active].key === 'decide'" class="decide">
        <div v-for="p in decidePlans" :key="p.name" class="plan">
          <span class="plan-name">{{ p.name }}</span>
          <span class="plan-target">{{ p.target }}</span>
          <span class="plan-match">{{ p.match }}</span>
          <span class="plan-risk">{{ p.risk }}</span>
        </div>
      </div>

      <!-- ④ 行动：可勾选任务 + 时间线 -->
      <div v-else-if="tabs[active].key === 'act'" class="act">
        <div class="act-progress">已完成 {{ doneCount }} / {{ actionTasks.length }}</div>
        <button
          v-for="(t, i) in actionTasks"
          :key="t.label"
          type="button"
          class="act-task"
          :class="{ done: t.done }"
          @click="toggleTask(i)"
        >
          <span class="check" aria-hidden="true">{{ t.done ? '✓' : '' }}</span>
          {{ t.label }}
        </button>
      </div>

      <!-- ⑤ 复盘校准：版本变化 + 教练提醒 -->
      <div v-else class="review">
        <div class="version">
          <span class="v-tag">v2</span>
          <span class="v-desc">因为补充了「一段实习经历」，诊断结论由「待验证」更新为「可投递」</span>
        </div>
        <div class="coach"><span class="coach-mark" aria-hidden="true">✦</span>你已经 3 天没更新进展，花 5 分钟记录一下最近的行动。</div>
      </div>
    </div>

    <div class="showcase-foot">
      <div class="dots" role="presentation">
        <button
          v-for="(tab, i) in tabs"
          :key="tab.key"
          type="button"
          class="dot"
          :class="{ 'is-active': active === i }"
          :aria-label="`切换到${tab.label}`"
          @click="select(i)"
        ></button>
      </div>
      <p class="demo-tag">演示数据 · 连接服务后展示你的真实产出</p>
    </div>
  </section>
</template>

<style scoped>
.showcase {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  padding: var(--space-8);
  margin-bottom: var(--space-12);
}

.showcase-head {
  margin-bottom: var(--space-6);
}

.group-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  margin: 0 0 var(--space-2);
}

.group-sub {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.tabs {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-bottom: var(--space-6);
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 40px;
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition:
    border-color 0.15s,
    color 0.15s,
    background 0.15s;
}

.tab:hover {
  border-color: var(--color-brand-border);
}

.tab:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-focus);
  outline-offset: var(--focus-ring-offset);
}

.tab.is-active {
  border-color: var(--color-brand);
  background: var(--color-brand-soft);
  color: var(--color-link);
  font-weight: var(--font-weight-semibold);
}

.tab:active {
  transform: scale(0.96);
}

.stage {
  color: var(--color-brand);
  font-weight: var(--font-weight-bold);
}

.panel {
  min-height: 240px;
  border: 1px solid var(--color-brand-border);
  border-radius: var(--radius-md);
  background: var(--color-brand-soft);
  padding: var(--space-6);
}

.panel-intro {
  margin: 0 0 var(--space-5);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.chat-line {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  margin-bottom: var(--space-3);
  font-size: var(--font-size-base);
}

.who {
  flex-shrink: 0;
  color: var(--color-link);
  font-weight: var(--font-weight-semibold);
}

.coverage {
  margin-top: var(--space-5);
}

.coverage-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
}

.coverage-label b {
  color: var(--color-text-primary);
}

.coverage-bar {
  height: 10px;
  border-radius: var(--radius-pill);
  background: var(--color-border);
  overflow: hidden;
}

.coverage-bar i {
  display: block;
  height: 100%;
  border-radius: var(--radius-pill);
  background: var(--color-success);
}

.verdict {
  margin: 0 0 var(--space-5);
  font-size: var(--font-size-base);
}

.diagnose-main {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: var(--space-5);
  align-items: start;
}

.radar {
  width: 100%;
  max-width: 260px;
}

.radar-grid {
  fill: none;
  stroke: var(--color-border);
  stroke-width: 1;
}

.radar-axis {
  stroke: var(--color-border);
  stroke-width: 1;
}

.radar-data {
  fill: var(--color-brand-soft);
  stroke: var(--color-brand);
  stroke-width: 2;
  fill-opacity: 0.5;
}

.radar-label {
  fill: var(--color-text-secondary);
  font-size: 11px;
}

.gaps {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.gap-row {
  display: grid;
  grid-template-columns: 1fr 1.2fr 1.2fr 1.4fr;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  font-size: var(--font-size-sm);
}

.dim {
  font-weight: var(--font-weight-semibold);
}

.require,
.current {
  color: var(--color-text-secondary);
}

.gap {
  color: var(--color-warning);
}

.decide {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.plan {
  display: grid;
  grid-template-columns: 64px 1fr 64px 1.4fr;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-4);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  font-size: var(--font-size-sm);
}

.plan-name {
  font-weight: var(--font-weight-bold);
  color: var(--color-brand);
}

.plan-match {
  color: var(--color-success-strong);
  font-weight: var(--font-weight-semibold);
}

.plan-risk {
  color: var(--color-text-secondary);
}

.act-progress {
  margin-bottom: var(--space-4);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.act-task {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  cursor: pointer;
  margin-bottom: var(--space-2);
  text-align: left;
}

.act-task:hover {
  border-color: var(--color-brand-border);
}

.act-task:active {
  transform: scale(0.99);
}

.act-task.done {
  opacity: 0.7;
}

.check {
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  border: 1px solid var(--color-success);
  border-radius: var(--radius-pill);
  color: var(--color-success-strong);
  flex-shrink: 0;
}

.version {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-4);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  margin-bottom: var(--space-3);
  font-size: var(--font-size-sm);
}

.v-tag {
  padding: 2px var(--space-3);
  border-radius: var(--radius-pill);
  background: var(--color-brand);
  color: var(--color-text-inverse);
  font-weight: var(--font-weight-semibold);
  flex-shrink: 0;
}

.coach {
  padding: var(--space-4);
  border-radius: var(--radius-sm);
  background: var(--color-role-soft);
  border: 1px solid var(--color-role-border);
  color: var(--color-role);
  font-size: var(--font-size-sm);
}

.coach-mark {
  margin-right: var(--space-2);
}

.showcase-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-top: var(--space-5);
}

.dots {
  display: flex;
  gap: var(--space-2);
}

.dot {
  width: 8px;
  height: 8px;
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--color-border);
  padding: 0;
  cursor: pointer;
}

.dot.is-active {
  width: 20px;
  background: var(--color-brand);
}

.demo-tag {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

@media (max-width: 640px) {
  .gap-row,
  .plan {
    grid-template-columns: 1fr;
    gap: var(--space-1);
  }

  .diagnose-main {
    grid-template-columns: 1fr;
  }

  .showcase-foot {
    flex-direction: column;
    align-items: flex-start;
  }

  /* 移动端：标签横向滑动，一次一屏，不压缩内容（HOME-009） */
  .tabs {
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }

  .tabs::-webkit-scrollbar {
    display: none;
  }

  .tab {
    flex-shrink: 0;
  }
}
</style>

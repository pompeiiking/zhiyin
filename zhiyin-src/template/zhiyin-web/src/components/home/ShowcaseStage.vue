<script setup lang="ts">
import { useSessionStore } from '@/stores/session'

// 五环节说明区（HOME-004）。
//
// ⚠️ 这里曾经是一个"展示台"：五个标签各自渲染一份**前端编造的产出样本**
//    （假报告、假方案、假任务清单），还带一个假的采集问答与可勾选任务。
//    这些都不是后端产出，会让访问者把演示当成产品真实能力。已全部删除。
//
// 现在这一区只做一件事：如实说明每个环节产出什么、边界在哪。
// 真实产出在核心对话页完成后写回工作台与完整报告页。
const session = useSessionStore()

// CTA 只把"开始"抛给页面：进任务的链路（建兜底任务 / 登录拦截 / 错误处理 / 跳转）只有一个持有者。
// 这里曾经自己 `router.push({ name: 'conversation' })`，与首页其它入口一样是"裸跳对话页"，
// 到了对话页没有当前任务，第一条消息必然失败。
const emit = defineEmits<{ start: [] }>()

interface StageCard {
  key: string
  no: string
  label: string
  produces: string
  detail: string
}

const STAGES: StageCard[] = [
  {
    key: 'collect',
    no: '①',
    label: '采集建模',
    produces: '结构化画像',
    detail: '用对话补齐关键字段，每个字段带置信度与证据；没有表达的字段记为缺口继续追问，不替你下判断。',
  },
  {
    key: 'diagnose',
    no: '②',
    label: '诊断匹配',
    produces: '诊断报告',
    detail: '逐项比对画像与目标要求，给出结论、差距与依据；没有证据的地方写明缺少依据，不编造外部事实。',
  },
  {
    key: 'decide',
    no: '③',
    label: '决策',
    produces: '方向方案',
    detail: '给出主攻 / 平行 / 保底三档候选与取舍依据；方向由你自己选定，系统不代选，也不自动重算。',
  },
  {
    key: 'act',
    no: '④',
    label: '行动',
    produces: '行动计划',
    detail: '把方向拆成带时间点的任务，可勾选、可跟踪；只做拆解，不评判方向对错。',
  },
  {
    key: 'review',
    no: '⑤',
    label: '复盘校准',
    produces: '复盘与校准',
    detail: '按真实行为日志做归因并给出下一步建议；浏览、登录、页面停留不计为有效行动。',
  },
]

function toStart() {
  emit('start')
}

const hasEntries = () => session.taskEntries.length > 0
</script>

<template>
  <section id="showcase" class="showcase">
    <div class="container">
      <div class="head">
        <h2>一场对话，五环节闭环产出</h2>
        <p>每个环节产出什么、边界在哪，下面如实说明；真实产出在你的工作台与完整报告页里。</p>
      </div>

      <ol class="stage-grid">
        <li v-for="stage in STAGES" :key="stage.key" class="stage-card">
          <span class="no" aria-hidden="true">{{ stage.no }}</span>
          <span class="label">{{ stage.label }}</span>
          <span class="produces">产出 · {{ stage.produces }}</span>
          <p class="detail">{{ stage.detail }}</p>
        </li>
      </ol>

      <div class="foot">
        <p>产出只在核心对话页发生，完成后写回同一份画像与资产；换主理不换结论。</p>
        <button v-if="hasEntries()" class="cta" type="button" @click="toStart">开始一场对话 →</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.showcase {
  padding: 64px 0;
  background: var(--paper);
  border-top: 1px solid var(--color-border);
}

.container { max-width: var(--content-max-width); margin: 0 auto; padding: 0 var(--page-gutter); }

.head { margin-bottom: 28px; }
.head h2 { margin: 0 0 6px; font-size: 26px; font-weight: 800; color: var(--color-text-primary); }
.head p { margin: 0; color: var(--color-text-secondary); font-size: 14px; line-height: 1.6; }

.stage-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-4);
  margin: 0;
  padding: 0;
  list-style: none;
}

.stage-card {
  display: grid;
  gap: 8px;
  align-content: start;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--card);
}

.no {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border-radius: 50%;
  background: var(--blueSoft);
  color: var(--blueD);
  font-weight: 800;
  font-size: 13px;
}

.label { font-size: var(--font-size-sm); font-weight: 800; color: var(--color-text-primary); }
.produces { color: var(--greenD); font-size: var(--font-size-xs); font-weight: 700; }
.detail { margin: 0; color: var(--color-text-secondary); font-size: var(--font-size-xs); line-height: 1.7; }

.foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
  margin-top: 28px;
}

.foot p { margin: 0; color: var(--color-text-muted); font-size: var(--font-size-xs); }

.cta {
  flex: none;
  padding: 9px 18px;
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--blueD);
  color: #fff;
  font-size: var(--font-size-sm);
  font-weight: 700;
  cursor: pointer;
}

@media (max-width: 1080px) {
  .stage-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 640px) {
  .stage-grid { grid-template-columns: 1fr; }
}
</style>

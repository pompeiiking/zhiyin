<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { useProfileCoverage } from '@/composables'

// 核心对话页中栏顶部的「建档完成 → ② 诊断」状态条（#screen-conv）。
//
// 口径（《职引-前端页面设计》§2.3「长内容不进对话流」与 §4.7）：这一条只说最短状态与
// 下一步，15 维全文去完整报告页。
//
// ⚠️ 这里**不再有「生成 15 维解析」按钮，也不再自判"已达解析门槛"**。
//    后端没有提供"触发诊断"的接口；"画像是否达标"是决策 5 的口径，由后端按关键
//    字段覆盖率与整体置信度判定，达标时**自动交接给②并在对话里显式告知**。
//    前端只如实显示后端下发的两个指标，不自己算、不自己下结论。
const { gaps, coverageText, confidenceText } = useProfileCoverage()
const router = useRouter()

const gapText = computed(() => (gaps.value.length ? gaps.value.join(' / ') : ''))

function toReport() {
  void router.push({ name: 'report' })
}
</script>

<template>
  <section class="handoff" aria-label="诊断解析交接">
    <span class="kicker">① 采集建模</span>
    <p class="line" :title="gapText ? `待补：${gapText}` : ''">
      画像覆盖 {{ coverageText }} · 整体置信度 {{ confidenceText }}
      <template v-if="gapText">　待补：{{ gapText }}</template>
    </p>
    <button class="act ghost" type="button" @click="toReport">查看完整报告 →</button>
  </section>
</template>

<style scoped>
.handoff {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 8px var(--space-5);
  border-bottom: 1px solid var(--blueLine);
  background: linear-gradient(180deg, var(--blueSoft), transparent);
}

.kicker {
  flex: none;
  color: var(--blueD);
  font-size: var(--font-size-xs);
  font-weight: 800;
  letter-spacing: 0.06em;
}

.line {
  flex: 1;
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.line b { color: var(--blueD); font-size: var(--font-size-sm); }

.bar {
  flex: 0 1 110px;
  height: 6px;
  border-radius: 5px;
  background: var(--card);
  overflow: hidden;
}

.bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--blue), var(--green));
  transition: width var(--duration-base) var(--ease-standard);
}

.act {
  flex: none;
  padding: 7px 15px;
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--blueD);
  color: #fff;
  font-size: var(--font-size-xs);
  font-weight: 700;
  cursor: pointer;
}

.act.ghost { background: var(--card); border: 1px solid var(--blueLine); color: var(--blueD); }
.act:hover { filter: brightness(1.05); }

@media (max-width: 640px) {
  .handoff { flex-wrap: wrap; }
  .bar { flex-basis: 100%; }
}
</style>

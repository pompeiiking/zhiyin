<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { useProfileCoverage } from '@/composables'

// 核心对话页中栏顶部的「建档完成 → ② 诊断」状态条（#screen-conv）。
//
// 口径（《职引-前端页面设计》§2.3「长内容不进对话流」与 §4.7）：这一条只说最短状态与
// 下一步，15 维全文去完整报告页。
//
// ⚠️ 这里**不再有「生成 15 维解析」按钮**。后端没有提供"触发诊断"的接口，
//    此前那个按钮只是在前端跑一个定时器、再合成一份演示分数，属于纯前端表演。
//    真实的②诊断入口是：在对话里表达"想验证方向"，由编排器判定环节后产出。
const { gaps, coverageText, confidenceText, archiveReady } = useProfileCoverage()
const router = useRouter()

const gapText = computed(() => (gaps.value.length ? `待补：${gaps.value.join(' / ')}` : '关键字段已齐'))

function toReport() {
  void router.push({ name: 'report' })
}
</script>

<template>
  <section class="handoff" aria-label="诊断解析交接">
    <span class="kicker">② 诊断</span>
    <p class="line" :title="gapText">
      {{
        archiveReady
          ? '画像已达解析门槛，继续对话即可进入诊断'
          : `画像覆盖 ${coverageText} · 置信度 ${confidenceText}`
      }}
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

.pct { flex: none; color: var(--blueD); font-size: var(--font-size-xs); }

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

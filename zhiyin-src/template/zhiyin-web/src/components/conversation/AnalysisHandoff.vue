<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { useProfileCoverage } from '@/composables'
import { ANALYSIS_STEPS, useAgentsStore } from '@/stores/agents'

// 核心对话页中栏顶部的「建档完成 → ② 诊断」交接条（#screen-conv）。
//
// 口径（《职引-前端页面设计》§2.3「长内容不进对话流」与 §4.7）：这一条只说最短状态与
// 下一步，15 维全文去完整报告页；「进入智能体小队 →」的入口就挂在这一条上。
// 建档门槛不在这里自定：口径集中在 composables/useProfileCoverage（关键字段 6 项、
// 覆盖率 ≥ 0.8、置信度 ≥ 0.7，出自 data/registry/policy_params.json::profile_collection）。
const agents = useAgentsStore()
const { gaps, coverageText, confidenceText, archiveReady } = useProfileCoverage()
const router = useRouter()

const status = computed(() => agents.analysisStatus)
const progress = computed(() => agents.analysisProgress)
const currentStep = computed(() => ANALYSIS_STEPS[agents.analysisStepIndex] ?? ANALYSIS_STEPS[0])
const result = computed(() => agents.analysis)

const gapText = computed(() => (gaps.value.length ? `待补：${gaps.value.join(' / ')}` : '关键字段已齐'))

function startAnalysis() {
  agents.startAnalysis()
}

function toAgentHub() {
  void router.push({ name: 'agents' })
}

function toReport() {
  void router.push({ name: 'report' })
}
</script>

<template>
  <section class="handoff" aria-label="诊断解析交接">
    <span class="kicker">② 诊断</span>

    <!-- 未开始：只报门槛与缺口，给一个动作 -->
    <template v-if="status === 'idle'">
      <p class="line" :title="gapText">
        {{ archiveReady ? '画像已达解析门槛，可生成 15 维解析' : `画像覆盖 ${coverageText} · 置信度 ${confidenceText}` }}
      </p>
      <button class="act" type="button" @click="startAnalysis">
        {{ archiveReady ? '生成 15 维解析' : '生成解析（演示补全）' }}
      </button>
    </template>

    <!-- 生成中：只说当前在做什么 -->
    <template v-else-if="status === 'running'">
      <p class="line" role="status">正在解析 · {{ currentStep.title }}</p>
      <span class="bar" aria-hidden="true"><i :style="{ width: `${progress}%` }"></i></span>
      <b class="pct">{{ progress }}%</b>
    </template>

    <!-- 已完成：最短结论 + 下一步入口（全文在完整报告页） -->
    <template v-else>
      <p class="line" title="解析已完成，结论依据已写入完整报告"><b>综合匹配 {{ result?.matchScore }}%</b></p>
      <button class="act" type="button" @click="toAgentHub">进入智能体小队 →</button>
      <button class="act ghost" type="button" @click="toReport">完整解析 →</button>
    </template>
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

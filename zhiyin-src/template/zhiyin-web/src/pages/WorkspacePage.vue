<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'

import { useWorkspaceStore } from '@/stores/workspace'
import { useSessionStore } from '@/stores/session'
import BlockEntryCard from '@/components/workspace/BlockEntryCard.vue'
import CoachMessageStream from '@/components/workspace/CoachMessageStream.vue'
import StagePanel from '@/components/workspace/StagePanel.vue'

const workspace = useWorkspaceStore()
const session = useSessionStore()
const {
  profilePanel,
  reportPanel,
  planPanel,
  actionPanel,
  reviewPanel,
  coachMessages,
  blocks,
  axisAStage,
} = storeToRefs(workspace)

onMounted(() => {
  if (!workspace.loaded) void workspace.load()
})

const coverage = computed(() => Math.round((profilePanel.value?.coverage ?? 0) * 100))
const confidence = computed(() => Math.round((profilePanel.value?.overall_confidence ?? 0) * 100))
const gapCount = computed(() => profilePanel.value?.gaps?.length ?? 0)

function stageTitle(panel: { title?: string } | null, fallback: string) {
  return panel?.title || fallback
}
</script>

<template>
  <main data-anchor="screen-wb" class="wb-page container">
    <!-- L1 总览层：轴 A 阶段定位 + 资产健康度 -->
    <section class="overview">
      <div class="axis-a">
        <small>阶段定位</small>
        <strong>{{ axisAStage || '尚未判断' }}</strong>
      </div>
      <dl class="health">
        <div>
          <dt>画像覆盖度</dt>
          <dd>{{ coverage }}%</dd>
        </div>
        <div>
          <dt>整体置信度</dt>
          <dd>{{ confidence }}%</dd>
        </div>
        <div>
          <dt>待补缺口</dt>
          <dd>{{ gapCount }}</dd>
        </div>
      </dl>
    </section>

    <!-- L2 环节层：五张区域卡 -->
    <section class="stages">
      <article class="profile-panel">
        <header class="panel-head">
          <span class="number">1</span>
          <div class="panel-title">
            <strong>① 采集建模</strong>
            <small v-if="profilePanel?.updated_at">更新于 {{ new Date(profilePanel.updated_at).toLocaleString() }}</small>
          </div>
        </header>
        <p class="status">{{ gapCount ? `还有 ${gapCount} 个关键字段待采集` : '画像字段已采集' }}</p>
      </article>

      <StagePanel :title="stageTitle(reportPanel, '② 诊断匹配')" :panel="reportPanel" :index="1" />
      <StagePanel :title="stageTitle(planPanel, '③ 方向决策')" :panel="planPanel" :index="2" />
      <StagePanel :title="stageTitle(actionPanel, '④ 行动计划')" :panel="actionPanel" :index="3" />
      <StagePanel :title="stageTitle(reviewPanel, '⑤ 复盘校准')" :panel="reviewPanel" :index="4" />
    </section>

    <!-- 教练消息 + 功能入口 -->
    <div class="side">
      <CoachMessageStream :messages="coachMessages" />
      <BlockEntryCard :blocks="blocks" :feature-flags="session.featureFlags" />
    </div>
  </main>
</template>

<style scoped>
.wb-page {
  padding-block: var(--space-8);
  display: grid;
  gap: var(--space-6);
}

.overview {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-6);
  align-items: stretch;
}

.axis-a {
  flex: 1 1 220px;
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  background: var(--color-brand-soft);
}

.axis-a small {
  display: block;
  margin-bottom: var(--space-2);
  color: var(--color-text-muted);
}

.axis-a strong {
  color: var(--color-brand);
  font-size: var(--font-size-lg);
}

.health {
  display: flex;
  gap: var(--space-4);
  margin: 0;
}

.health > div {
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.health dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.health dd {
  margin: var(--space-2) 0 0;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
}

.stages {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
}

.profile-panel {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.panel-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-pill);
  background: var(--color-brand-soft);
  color: var(--color-brand);
  font-size: var(--font-size-sm);
}

.panel-title strong {
  display: block;
  font-size: var(--font-size-md);
}

.panel-title small {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.status {
  margin: var(--space-3) 0 0;
  color: var(--color-text-secondary);
}

.side {
  display: grid;
  gap: var(--space-6);
}
</style>

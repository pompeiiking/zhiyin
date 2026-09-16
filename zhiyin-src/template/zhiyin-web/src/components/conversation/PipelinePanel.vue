<script setup lang="ts">
import { computed } from 'vue'
import type { PipelineCardView } from '@/api/schema'
import { useConversationStore } from '@/stores/conversation'
import { useSessionStore } from '@/stores/session'
import PipelineCard from './PipelineCard.vue'

const conversation = useConversationStore()
const session = useSessionStore()

const fallbackPipeline: PipelineCardView[] = [
  { stage: 'collect', title: '采集建模', status: 'in_progress', active: true },
  { stage: 'diagnose', title: '诊断匹配', status: 'empty' },
  { stage: 'decide', title: '决策', status: 'empty' },
  { stage: 'act', title: '行动', status: 'empty' },
  { stage: 'review', title: '复盘校准', status: 'empty' },
]

const pipeline = computed(() => {
  if (!conversation.pipeline.length) return fallbackPipeline
  return conversation.pipeline as unknown as PipelineCardView[]
})

const title = computed(() => String(session.copyBundle['conv.pipeline_title'] ?? '微循环管线'))
const leadName = computed(() => String(conversation.badge.name ?? '待分配'))
</script>

<template>
  <aside class="pipeline-panel" aria-label="微循环管线">
    <header class="head">
      <small>你的进展</small>
      <h2>{{ title }}</h2>
    </header>
    <div class="cards">
      <PipelineCard
        v-for="(card, index) in pipeline"
        :key="card.stage"
        :card="card"
        :index="index"
        :lead-name="card.active ? leadName : undefined"
      />
    </div>
    <p class="loop-hint">完成复盘后，可带着新信息再次进入下一轮。</p>
  </aside>
</template>

<style scoped>
.pipeline-panel {
  min-height: 0;
  overflow: auto;
  padding: var(--space-5);
  border-left: 1px solid var(--color-border);
  background: var(--color-bg);
}

.head small {
  color: var(--color-text-muted);
}

.head h2 {
  margin: var(--space-1) 0 var(--space-5);
  font-size: var(--font-size-lg);
}

.cards {
  display: grid;
  gap: var(--space-3);
}

.loop-hint {
  margin: var(--space-4) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}
</style>

<script setup lang="ts">
import { computed } from 'vue'
import type { PipelineCardView, ProfilePanelView } from '@/api/schema'
import { useConversationStore } from '@/stores/conversation'
import { useSessionStore } from '@/stores/session'
import PipelineCard from './PipelineCard.vue'
import ProfileFields from './ProfileFields.vue'

const conversation = useConversationStore()
const session = useSessionStore()

const pipeline = computed(() => conversation.pipeline as unknown as PipelineCardView[])
const profile = computed(() => conversation.profile as unknown as ProfilePanelView | null)

const title = computed(() => String(session.copyBundle['conv.pipeline_title'] ?? '微循环管线'))
const leadName = computed(() => String(conversation.badge.name ?? '待分配'))
</script>

<template>
  <aside class="pipeline-panel" aria-label="微循环管线">
    <header class="head">
      <small>你的进展</small>
      <h2>{{ title }}</h2>
    </header>
    <ProfileFields :profile="profile" />
    <div class="cards">
      <PipelineCard
        v-for="(card, index) in pipeline"
        :key="card.stage"
        :card="card"
        :index="index"
        :lead-name="card.active ? leadName : undefined"
      />
    </div>
    <p v-if="!pipeline.length" class="empty-state">当前暂无管线数据，进入任务后会显示你的五环节进度。</p>
    <p class="loop-hint"><span class="loop-arrow" aria-hidden="true">↺</span>完成复盘后，可带着新信息再次进入下一轮。</p>
  </aside>
</template>

<style scoped>
.pipeline-panel {
  min-height: 0;
  overflow: auto;
  padding: var(--space-5);
  border: 1px solid var(--line);
  border-radius: var(--r);
  background: var(--card);
  box-shadow: var(--shadow);
}

.head small {
  color: var(--muted);
}

.head h2 {
  margin: var(--space-1) 0 var(--space-5);
  font-size: var(--font-size-lg);
  font-weight: 800;
}

.cards {
  display: grid;
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.empty-state {
  margin: var(--space-4) 0 0;
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px dashed var(--color-border);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  text-align: center;
}

.loop-hint {
  margin: var(--space-4) 0 0;
  padding: var(--space-3);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

.loop-arrow {
  color: var(--color-brand);
  font-size: var(--font-size-md);
  line-height: 1;
}
</style>

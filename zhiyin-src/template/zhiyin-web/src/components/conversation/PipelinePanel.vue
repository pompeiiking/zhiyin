<script setup lang="ts">
import { computed, onMounted } from 'vue'
import type { PipelineCardView, ProfilePanelView } from '@/api/schema'
import { useConversationStore } from '@/stores/conversation'
import { useSessionStore } from '@/stores/session'
import { useWorkspaceStore } from '@/stores/workspace'
import PipelineCard from './PipelineCard.vue'
import ProfileFields from './ProfileFields.vue'

const conversation = useConversationStore()
const session = useSessionStore()
const workspace = useWorkspaceStore()

const pipeline = computed(() => conversation.pipeline as unknown as PipelineCardView[])
// 画像面板取真实来源：`GET /app/workspace` 的 profile_panel。
// 对话回合的 DTO 不带画像面板，此前这里读的是 store 里一份从未被写入的状态，
// 页面因此永远显示覆盖 0 / 置信度 0。
const profile = computed(() => workspace.profilePanel as unknown as ProfilePanelView | null)

const title = computed(() => String(session.copyBundle['conv.pipeline_title'] ?? '微循环管线'))
const leadName = computed(() => String(conversation.badge?.name ?? '待分配'))

onMounted(() => {
  void workspace.load()
})
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
    <!--
      空态如实区分两种情形：还没选中会话（可进入任务），与已选中会话但后端确实没给出环节进度。
      合成一句"进入任务后就会显示"会让已选中的空会话看起来像没进过任务，掩盖真实缺数。
    -->
    <p v-if="!pipeline.length" class="empty-state">
      {{
        conversation.currentTaskId
          ? '该会话暂无环节进度数据。'
          : '当前未选择任务会话，进入任务后会显示你的五环节进度。'
      }}
    </p>
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

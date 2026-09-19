<script setup lang="ts">
import { onMounted } from 'vue'

import ChatStream from '@/components/conversation/ChatStream.vue'
import PipelinePanel from '@/components/conversation/PipelinePanel.vue'
import SessionList from '@/components/conversation/SessionList.vue'
import { useConversationStore } from '@/stores/conversation'

const conversation = useConversationStore()

// 左栏会话来自 GET /app/sessions。此前没有任何调用点：直接打开 /conv（或刷新页面）时
// 左栏永远是空的，而后端其实存着真实会话——"刷新一下任务就没了"就是这么来的。
// 失败时保持空列表并显示空态（loadSessions 不塞演示数据）；这里 catch 只为不产生未处理拒绝，
// 页面仍以空态如实呈现，不假装有会话。
//
// 列表到手后必须再读一次当前会话的历史：中栏气泡与右栏管线卡同样只在内存里，
// 刷新后会连同左栏一起消失（"刷新后对话被清空"）。`loadHistory` 自己处理失败并
// 如实提示，不会把失败静默成空态。
onMounted(async () => {
  await conversation.loadSessions().catch(() => {})
  const taskId = conversation.currentTaskId
  if (taskId) await conversation.loadHistory(taskId)
})
</script>

<template>
  <main data-anchor="screen-conv" class="conv-page">
    <SessionList />
    <ChatStream />
    <PipelinePanel />
  </main>
</template>

<style scoped>
.conv-page {
  height: calc(100dvh - 72px);
  min-height: 0;
  display: grid;
  grid-template-columns: 280px minmax(480px, 760px) 340px;
  justify-content: center;
  gap: var(--space-5);
  padding: var(--space-5);
  overflow: hidden;
  background: var(--paper);
}

/* 屏宽收紧时把中栏（对话）放在第一位：两侧栏先变窄，再降级为抽屉与步骤条（§6.1/§6.2）。 */
@media (max-width: 1440px) {
  .conv-page { grid-template-columns: 224px minmax(0, 1fr) 296px; justify-content: stretch; }
}

@media (max-width: 1180px) {
  .conv-page { grid-template-columns: 172px minmax(0, 1fr) 240px; gap: var(--space-3); padding: var(--space-3); }
  /* 两侧栏同步减小内边距，把宽度让给中间对话 */
  :deep(.pipeline-panel), :deep(.session-list) { padding: var(--space-3); }
}

@media (max-width: 900px) {
  .conv-page { grid-template-columns: 64px minmax(0, 1fr) 240px; }
  :deep(.session-list) { padding-inline:var(--space-3); }
  :deep(.session-list h2), :deep(.session-list .empty) { display:none; }
}

@media (max-width: 640px) {
  .conv-page {
    height: auto;
    min-height: calc(100dvh - 72px);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-3);
    overflow: visible;
  }
  /* 左栏 → 顶部横向会话切换条 */
  :deep(.session-list) {
    order: 1;
    flex: none;
    border: 0;
    border-radius: 0;
    box-shadow: none;
    background: transparent;
  }
  /* 中栏 → 固定高度，内部继续滚动 */
  :deep(.chat-stream) {
    order: 2;
    flex: none;
    height: 70vh;
    min-height: 420px;
  }
  /* 右栏 → 底部步骤条 / 展开面板 */
  :deep(.pipeline-panel) { order: 3; flex: none; }
}
</style>

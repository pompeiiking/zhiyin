<script setup lang="ts">
import ChatStream from '@/components/conversation/ChatStream.vue'
import PipelinePanel from '@/components/conversation/PipelinePanel.vue'
import SessionList from '@/components/conversation/SessionList.vue'
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
  height: calc(100dvh - 60px);
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(220px, 270px) minmax(420px, 1fr) minmax(250px, 320px);
  overflow: hidden;
}

@media (max-width: 1280px) {
  .conv-page { grid-template-columns: 220px minmax(360px, 1fr) 280px; }
}

@media (max-width: 900px) {
  .conv-page { grid-template-columns: 64px minmax(0, 1fr) 260px; }
  :deep(.session-list) { padding-inline:var(--space-3); }
  :deep(.session-list h2), :deep(.session-list .empty) { display:none; }
}

@media (max-width: 640px) {
  .conv-page { height:calc(100dvh - 60px); grid-template-columns:1fr; }
  :deep(.session-list) { display:none; }
  :deep(.pipeline-panel) { display:none; }
}
</style>

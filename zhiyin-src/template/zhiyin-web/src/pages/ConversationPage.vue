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
</style>

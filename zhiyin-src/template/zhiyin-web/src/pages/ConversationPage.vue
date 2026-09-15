<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useConversationStore } from '@/stores/conversation'
import { useGuestGuard } from '@/composables'
import ChatStream from '@/components/conversation/ChatStream.vue'
import PipelinePanel from '@/components/conversation/PipelinePanel.vue'
import SessionList from '@/components/conversation/SessionList.vue'
const conversation = useConversationStore()
const { handleGuestError } = useGuestGuard()
const showSessions = ref(false)
const showPipeline = ref(false)
onMounted(async () => {
  if (conversation.sessions.length) return
  try { await conversation.loadSessions() } catch (error) {
    if (!handleGuestError(error)) conversation.error = '会话列表加载失败，请稍后重试。'
  }
})
</script>
<template>
  <main data-anchor="screen-conv" class="conv-page"><div class="mobile-tools"><button :aria-expanded="showSessions" @click="showSessions = !showSessions">任务会话</button><button :aria-expanded="showPipeline" @click="showPipeline = !showPipeline">微循环进度</button></div><SessionList :class="{ mobileOpen: showSessions }" /><ChatStream /><PipelinePanel :class="{ mobileOpen: showPipeline }" /></main>
</template>
<style scoped>
.conv-page { height: calc(100dvh - 80px); display: grid; grid-template-columns: minmax(220px, 270px) minmax(420px, 1fr) minmax(250px, 320px); overflow: hidden; }.mobile-tools { display: none; }
@media (max-width: 900px) { .conv-page { height: auto; min-height: calc(100dvh - 80px); grid-template-columns: 220px minmax(0, 1fr); }.pipeline-panel { display: none; grid-column: 1 / -1; }.pipeline-panel.mobileOpen { display: block; } }
@media (max-width: 560px) { .conv-page { display: block; }.mobile-tools { position: sticky; top: 118px; z-index: 8; display: flex; gap: var(--space-2); padding: var(--space-2) var(--page-gutter); background: var(--color-bg); border-bottom: 1px solid var(--color-border); }.mobile-tools button { flex: 1; min-height: 40px; border: 1px solid var(--color-border); border-radius: var(--radius-pill); background: var(--color-surface); }.session-list, .pipeline-panel { display: none; max-height: 50dvh; border: 0; border-bottom: 1px solid var(--color-border); }.session-list.mobileOpen, .pipeline-panel.mobileOpen { display: block; }.chat-stream { min-height: calc(100dvh - 170px); } }
</style>

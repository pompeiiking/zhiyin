<script setup lang="ts">
import { useConversationStore } from '@/stores/conversation'
import { useSessionStore } from '@/stores/session'
import PipelineCard from './PipelineCard.vue'
const conversation = useConversationStore()
const session = useSessionStore()
</script>
<template><aside class="pipeline-panel" aria-label="微循环管线"><div class="head"><small>你的进展</small><h2>{{ session.copyBundle['conv.pipeline_title'] || '微循环管线' }}</h2></div><div v-if="conversation.pipeline.length" class="cards"><PipelineCard v-for="(card, index) in conversation.pipeline" :key="card.stage" :card="card" :index="index" /></div><p v-else class="empty">开始对话后，这里会呈现五个环节的产出与依据。</p><RouterLink :to="{ name: 'workspace' }">查看智能工作台 <span aria-hidden="true">→</span></RouterLink></aside></template>
<style scoped>.pipeline-panel { padding: var(--space-5); border-left: 1px solid var(--color-border); background: var(--color-bg); overflow: auto; }.head small { color: var(--color-text-muted); letter-spacing: .12em; }.head h2 { margin: var(--space-1) 0 var(--space-5); font-size: var(--font-size-lg); }.cards { display: grid; gap: var(--space-3); }.empty { color: var(--color-text-secondary); }.pipeline-panel > a { display: inline-flex; gap: var(--space-2); margin-top: var(--space-6); min-height: 44px; align-items: center; }</style>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useConversationStore } from '@/stores/conversation'
import AgentBadge from './AgentBadge.vue'
import BehaviorGuide from './BehaviorGuide.vue'
import DisclosureRow from './DisclosureRow.vue'
import MessageBubble from './MessageBubble.vue'
import QuickActions from './QuickActions.vue'
const conversation = useConversationStore()
const text = ref('')
const input = ref<HTMLTextAreaElement>()
const stream = ref<HTMLElement>()
watch(() => conversation.turns.length, async () => { await nextTick(); stream.value?.scrollTo({ top: stream.value.scrollHeight, behavior: 'smooth' }) })
async function submit(value = text.value) {
  const outgoing = value.trim(); if (!outgoing) return
  text.value = ''
  try { await conversation.send(outgoing) } catch { conversation.error = '消息发送失败，请稍后重试。'; text.value = outgoing }
}
function act(value: string) { text.value = value; input.value?.focus() }
</script>
<template>
  <section class="chat-stream" aria-label="当前对话"><header><AgentBadge :badge="conversation.badge" /><div v-if="!conversation.badge.name"><small>CURRENT CONVERSATION</small><h1>{{ conversation.currentSession?.task_name || '开始一次职业探索' }}</h1></div></header>
    <div ref="stream" class="messages"><DisclosureRow :disclosure="conversation.disclosure" /><div v-if="!conversation.turns.length" class="empty"><span aria-hidden="true">✳</span><h2>把眼前的困惑说出来</h2><p>我会一次问一个问题，陪你找到有依据的下一步。</p></div><MessageBubble v-for="(message, index) in conversation.turns" :key="`${message.created_at ?? ''}-${index}`" :message="message" /><BehaviorGuide :guide="conversation.guide" :disabled="conversation.sending" @act="act" /></div>
    <div class="composer"><QuickActions :disabled="conversation.sending" @select="act" /><label class="sr-only" for="conversation-input">输入消息</label><div class="input-row"><textarea id="conversation-input" ref="input" v-model="text" rows="1" placeholder="说说你现在的想法…" :disabled="!conversation.currentTaskId || conversation.sending" @keydown.enter.exact.prevent="submit()"></textarea><button :disabled="!text.trim() || !conversation.currentTaskId || conversation.sending" @click="submit()">{{ conversation.sending ? '发送中' : '发送' }}</button></div><p v-if="conversation.error" role="alert">{{ conversation.error }}</p></div>
  </section>
</template>
<style scoped>
.chat-stream { min-width: 0; display: grid; grid-template-rows: auto 1fr auto; background: var(--color-surface); }.chat-stream > header { padding: var(--space-5) var(--space-6); border-bottom: 1px solid var(--color-border); }.chat-stream > header small { color: var(--color-text-muted); letter-spacing: .12em; }.chat-stream > header h1 { margin: var(--space-1) 0 0; font-size: var(--font-size-lg); }.messages { min-height: 360px; overflow: auto; display: flex; flex-direction: column; gap: var(--space-5); padding: var(--space-6); }.empty { margin: auto; text-align: center; color: var(--color-text-secondary); }.empty > span { font-size: var(--font-size-2xl); color: var(--color-link); }.empty h2 { color: var(--color-text-primary); }.composer { padding: var(--space-4) var(--space-6); border-top: 1px solid var(--color-border); }.input-row { display: flex; gap: var(--space-3); margin-top: var(--space-3); }.input-row textarea { flex: 1; min-height: 48px; padding: var(--space-3); resize: none; border: 1px solid var(--color-border); border-radius: var(--radius-md); }.input-row > button { min-width: 72px; border: 0; border-radius: var(--radius-md); background: var(--color-action-bg); color: var(--color-text-inverse); }.composer > p { color: var(--color-danger); font-size: var(--font-size-xs); }
</style>

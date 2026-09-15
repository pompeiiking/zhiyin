<script setup lang="ts">
import type { ConversationMessageView } from '@/api/schema'
import TheoryTag from './TheoryTag.vue'
defineProps<{ message: ConversationMessageView }>()
</script>
<template>
  <article class="message" :class="`is-${message.role}`"><span class="avatar" aria-hidden="true">{{ message.role === 'user' ? '我' : message.role === 'agent' ? '引' : 'i' }}</span><div><p v-if="message.agent_name" class="author">{{ message.agent_name }}</p><div class="bubble">{{ message.text }}</div><div class="refs"><TheoryTag v-for="(item, index) in (message.theory_refs ?? [])" :key="String(item.theory_id ?? index)" :theory="item" /></div></div></article>
</template>
<style scoped>
.message { display: flex; align-items: flex-start; gap: var(--space-3); max-width: 86%; }.message.is-user { flex-direction: row-reverse; margin-left: auto; }.avatar { flex: 0 0 34px; height: 34px; display: grid; place-items: center; border-radius: var(--radius-md); background: var(--color-brand-soft); color: var(--color-link); }.is-user .avatar { background: var(--color-action-bg); color: var(--color-text-inverse); }.author { margin: 0 0 var(--space-1); color: var(--color-text-secondary); font-size: var(--font-size-xs); }.bubble { padding: var(--space-3) var(--space-4); border: 1px solid var(--color-border); border-radius: 4px var(--radius-lg) var(--radius-lg); background: var(--color-surface); white-space: pre-wrap; line-height: var(--line-height-relaxed); }.is-user .bubble { border: 0; border-radius: var(--radius-lg) 4px var(--radius-lg) var(--radius-lg); background: var(--color-action-bg); color: var(--color-text-inverse); }.is-system { max-width: 100%; justify-content: center; color: var(--color-text-secondary); }.is-system .avatar { display: none; }.refs { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-2); }
</style>

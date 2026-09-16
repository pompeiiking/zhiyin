<script setup lang="ts">
import TheoryTag from './TheoryTag.vue'
defineProps<{ role: 'agent' | 'user' | 'system'; content: string; author?: string; theory?: Record<string, unknown> }>()
</script>

<template>
  <article class="message-bubble" :class="role"><small v-if="role !== 'user'">{{ author || (role === 'system' ? '系统提示' : '职业顾问') }}</small><p>{{ content }}</p><TheoryTag v-if="theory && role === 'agent'" :theory="theory" /></article>
</template>

<style scoped>
.message-bubble { max-width:78%; padding:var(--space-3) var(--space-4); border-radius:var(--radius-lg); background:var(--color-surface); border:1px solid var(--color-border); box-shadow:var(--shadow-card); }
.message-bubble.user { margin-left:auto; background:var(--color-action-bg); border-color:var(--color-action-bg); color:var(--color-text-inverse); border-top-right-radius:var(--space-1); }
.message-bubble.agent { border-top-left-radius:var(--space-1); }
.message-bubble.system { max-width:100%; padding-block:var(--space-2); border:0; box-shadow:none; background:transparent; color:var(--color-text-muted); text-align:center; }
small { display:block; margin-bottom:var(--space-1); color:var(--color-text-secondary); font-size:var(--font-size-xs); }
.user small { color:inherit; opacity:.8; }
p { margin:0; line-height:var(--line-height-relaxed); }
</style>

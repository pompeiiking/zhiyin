<script setup lang="ts">
import { useConversationStore } from '@/stores/conversation'
const conversation = useConversationStore()
function percent(value?: number) { return `${Math.round((value ?? 0) * 100)}%` }
</script>
<template>
  <aside class="session-list" aria-label="任务会话"><div class="head"><div><small>MY JOURNEYS</small><h2>我的任务</h2></div><RouterLink :to="{ name: 'home' }" aria-label="新建任务">＋</RouterLink></div>
    <p v-if="conversation.loadingSessions" class="empty">正在加载…</p><p v-else-if="!conversation.sessions.length" class="empty">还没有任务，从首页选择一件想解决的事。</p>
    <button v-for="item in conversation.sessions" :key="item.task_id" :class="{ active: item.task_id === conversation.currentTaskId }" @click="conversation.selectSession(item.task_id)"><span class="title">{{ item.task_name }}</span><span class="meta">{{ item.stage_label }} · {{ percent(item.progress) }}</span><span class="progress"><i :style="{ width: percent(item.progress) }"></i></span></button>
  </aside>
</template>
<style scoped>
.session-list { padding: var(--space-5); border-right: 1px solid var(--color-border); background: var(--color-bg); overflow: auto; }.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-5); }.head small { color: var(--color-text-muted); letter-spacing: .12em; }.head h2 { margin: var(--space-1) 0 0; font-size: var(--font-size-lg); }.head a { width: 40px; height: 40px; display: grid; place-items: center; border: 1px solid var(--color-border); border-radius: 50%; text-decoration: none; }.session-list > button { width: 100%; display: grid; gap: var(--space-2); text-align: left; padding: var(--space-4); margin-bottom: var(--space-3); border: 1px solid transparent; border-radius: var(--radius-md); background: transparent; }.session-list > button.active { border-color: var(--color-brand-border); background: var(--color-brand-soft); }.title { font-weight: var(--font-weight-semibold); }.meta, .empty { color: var(--color-text-secondary); font-size: var(--font-size-xs); }.progress { height: 3px; overflow: hidden; border-radius: var(--radius-pill); background: var(--color-border); }.progress i { display: block; height: 100%; background: var(--color-brand); }
</style>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ messages: Array<Record<string, unknown>> }>()

/** 本地已关闭的消息 id（仅前端会话态，不落库） */
const dismissed = ref<string[]>([])

function title(item: Record<string, unknown>) {
  return String(item.title ?? item.reason ?? '教练提醒')
}

function detail(item: Record<string, unknown>) {
  return String(item.detail ?? '')
}

function time(item: Record<string, unknown>) {
  const value = item.occurred_at
  return value ? new Date(String(value)).toLocaleString() : ''
}

function id(item: Record<string, unknown>) {
  return String(item.id ?? '')
}

function visible() {
  return props.messages.filter((item) => !dismissed.value.includes(id(item)))
}

function dismiss(item: Record<string, unknown>) {
  dismissed.value.push(id(item))
}
</script>

<template>
  <section class="coach-message-stream">
    <h3>教练消息</h3>
    <p v-if="!visible().length" class="empty">暂无新的教练消息。</p>
    <ul v-else class="stream">
      <li v-for="(item, index) in visible()" :key="id(item) || index" class="bubble">
        <div class="bubble-head">
          <strong>{{ title(item) }}</strong>
          <small v-if="time(item)">{{ time(item) }}</small>
        </div>
        <p v-if="detail(item)" class="detail">{{ detail(item) }}</p>
        <div class="actions">
          <button type="button" class="primary" @click="dismiss(item)">知道了</button>
          <button type="button" class="ghost" @click="dismiss(item)">不再提醒</button>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.coach-message-stream h3 {
  margin: 0 0 var(--space-3);
  font-size: var(--font-size-md);
}

.empty {
  color: var(--color-text-muted);
}

.stream {
  display: grid;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.bubble {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-role-soft);
}

.bubble-head {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  align-items: baseline;
}

.bubble-head strong {
  color: var(--color-role);
}

.bubble-head small {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.detail {
  margin: var(--space-2) 0;
  color: var(--color-text-secondary);
}

.actions {
  display: flex;
  gap: var(--space-2);
}

.primary {
  min-height: 36px;
  padding: var(--space-1) var(--space-4);
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--color-role);
  color: var(--color-text-inverse);
}

.ghost {
  min-height: 36px;
  padding: var(--space-1) var(--space-4);
  border: 1px solid var(--color-role-border);
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--color-role);
}
</style>

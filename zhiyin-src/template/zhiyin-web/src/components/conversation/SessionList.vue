<script setup lang="ts">
import { useConversationStore } from '@/stores/conversation'

const conversation = useConversationStore()
const pct = (item: Record<string, unknown>) => `${Math.round((Number(item.progress) || 0) * 100)}%`
</script>

<template>
  <aside class="session-list" aria-label="任务会话">
    <header>
      <h2>我的任务</h2>
      <RouterLink :to="{ name: 'home' }" aria-label="新建任务">＋</RouterLink>
    </header>
    <div v-if="conversation.sessions.length" class="session-items">
      <button
        v-for="item in conversation.sessions"
        :key="String(item.task_id)"
        type="button"
        class="session-item"
        :class="{ active: item.task_id === conversation.currentTaskId }"
      >
        <strong>{{ String(item.task_name ?? '未命名任务') }}</strong>
        <small>{{ String(item.stage_label ?? '进行中') }}</small>
        <span class="progress-row">
          <i class="bar"><i class="fill" :style="{ width: pct(item) }"></i></i>
          <b>{{ pct(item) }}</b>
        </span>
      </button>
    </div>
    <p v-else class="empty">当前暂无会话，从首页选择一件想解决的事。</p>
  </aside>
</template>

<style scoped>
.session-list {
  min-height: 0;
  overflow: auto;
  padding: var(--space-5);
  border: 1px solid var(--line);
  border-radius: var(--r);
  background: var(--card);
  box-shadow: var(--shadow);
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-5);
}

h2 {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 800;
}

header a {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border: 1px solid var(--line);
  border-radius: 50%;
  background: var(--card);
  color: var(--ink);
  text-decoration: none;
  font-weight: 700;
}

header a:hover { border-color: var(--blue); color: var(--blueD); }

.session-items { display: grid; gap: var(--space-2); }

.session-item {
  display: grid;
  gap: var(--space-1);
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.session-item:hover, .session-item.active { border-color: var(--blueLine); background: var(--blueSoft); }
.session-item.active strong { color: var(--blueD); }
.session-item strong { font-size: var(--font-size-sm); font-weight: 600; }
.session-item small { color: var(--muted); font-size: var(--font-size-xs); }

.progress-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.progress-row .bar {
  flex: 1;
  height: 5px;
  border-radius: 3px;
  background: var(--line);
  overflow: hidden;
}

.progress-row .fill {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: var(--blue);
}

.progress-row b {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--muted);
}

.empty {
  margin: 0;
  padding: var(--space-4);
  border: 1px dashed var(--line);
  border-radius: var(--radius-md);
  color: var(--muted);
  font-size: var(--font-size-xs);
  line-height: 1.6;
}

@media (max-width: 640px) {
  .session-list { padding: 0; }
  .session-list header { display: none; }
  .session-items { display: flex; gap: var(--space-2); overflow-x: auto; padding-bottom: 2px; }
  .session-item { flex: 0 0 auto; width: auto; min-width: 180px; }
}
</style>

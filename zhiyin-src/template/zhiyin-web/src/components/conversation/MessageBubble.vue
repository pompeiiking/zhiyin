<script setup lang="ts">
import TheoryTag from './TheoryTag.vue'
defineProps<{ role: 'agent' | 'user' | 'system' | 'coach'; content: string; author?: string; theory?: Record<string, unknown>; action?: string; long?: boolean }>()
</script>

<template>
  <article class="msg" :class="role">
    <span v-if="role !== 'user' && role !== 'system'" class="avatar" aria-hidden="true">{{ (author || '职业顾问').slice(0, 1) }}</span>
    <div class="bubble">
      <small v-if="role !== 'user'">{{ author || (role === 'system' ? '系统提示' : role === 'coach' ? '教练 · 主动提醒' : '职业顾问') }}</small>
      <p>{{ content }}</p>
      <button v-if="long && role === 'agent'" type="button" class="report-link">查看完整报告 →</button>
      <TheoryTag v-if="theory && role === 'agent'" :theory="theory" />
      <div v-if="role === 'coach'" class="coach-actions">
        <button type="button" class="coach-btn">{{ action || '立即行动' }}</button>
        <button type="button" class="coach-btn ghost">稍后</button>
      </div>
    </div>
  </article>
</template>

<style scoped>
.msg { display: flex; gap: 9px; align-items: flex-end; }
.msg.user { justify-content: flex-end; }
.msg.system { justify-content: center; }

.avatar {
  flex: none;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  margin-bottom: 1px;
  background: linear-gradient(155deg, var(--blue), var(--greenD));
  color: #fff;
  box-shadow: 0 3px 8px rgba(55, 138, 221, 0.32);
}

.bubble {
  max-width: 78%;
  border-radius: 16px;
  padding: 12px 16px;
  font-size: 15px;
  line-height: 1.6;
  box-shadow: 0 1px 2px rgba(28, 24, 22, 0.03);
}

.msg.agent .bubble { background: #fff; border: 1px solid var(--line); border-top-left-radius: 5px; color: var(--ink); }
.msg.user .bubble { background: var(--blue); color: #fff; border-top-right-radius: 5px; box-shadow: 0 4px 12px rgba(55, 138, 221, 0.22); }
.msg.system .bubble { max-width: 100%; border: 0; background: transparent; color: var(--muted); text-align: center; box-shadow: none; }
.msg.coach .bubble { background: var(--purpleSoft); border: 1px solid var(--purpleLine); border-top-left-radius: 5px; color: var(--ink); }
.msg.coach .avatar { background: linear-gradient(155deg, var(--violet), var(--blue)); box-shadow: 0 3px 8px rgba(108, 91, 216, 0.32); }

.coach-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.coach-btn { border: 0; border-radius: var(--pill); background: var(--violet); color: #fff; padding: 8px 15px; font-size: 13.5px; font-weight: 700; cursor: pointer; }
.coach-btn.ghost { background: #fff; color: var(--violet); border: 1px solid var(--purpleLine); }

.report-link { display: inline-block; margin-top: 8px; border: 0; background: none; padding: 0; color: var(--blueD); font-size: 13.5px; font-weight: 700; cursor: pointer; }
.report-link:hover { text-decoration: underline; }

small { display: block; margin-bottom: 2px; color: var(--gray); font-size: 12px; }
.msg.user small { color: inherit; opacity: 0.85; }
p { margin: 0; }
</style>

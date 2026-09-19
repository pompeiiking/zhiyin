<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { trackEvent } from '@/api/endpoints'
import { useWorkspaceStore } from '@/stores/workspace'

// 工作台 · 教练消息流（§4.3 第 ⑤ 层 / FR-WB-006 / PSH-002）。
//
// 陪伴教练的主动消息（提醒 / 预警 / 复盘邀请）集中在这里呈现，
// 数据来自 workspace.coachMessages（后端来自 TrackEvent）。
//
// 口径：**主动干预必须由真实行为信号触发**（停滞阈值等参数来自
// data/registry/policy_params.json），前端不自己判断"该提醒了"，
// 只负责展示与响应（review_warning_show / review_warning_response）。
const store = useWorkspaceStore()
const router = useRouter()
const messages = computed(() => store.coachMessages)

// 演示阶段：教练建议的响应在组件内闭环——主行动跳转对话页续接，
// 「稍后 / 不再提醒」收起当前消息；全部收起后回到空状态。
const hidden = ref<Set<number>>(new Set())
const items = computed(() =>
  messages.value.map((msg, index) => ({ msg, index })).filter((item) => !hidden.value.has(item.index)),
)

function respond(msg: Record<string, unknown>) {
  void trackEvent('review_warning_response', { action: String(msg.action) }).catch(() => {})
  router.push({ name: 'conversation' })
}

function hide(index: number, action: 'snooze' | 'mute') {
  hidden.value.add(index)
  void trackEvent('review_warning_response', { action }).catch(() => {})
}
</script>

<template>
  <section class="coach-message-stream" aria-label="教练消息">
    <header class="cms-head">
      <small>今日行动</small>
      <h3>教练建议</h3>
    </header>

    <div v-if="items.length" class="cms-list">
      <article v-for="item in items" :key="item.index" class="cms-bubble">
        <span class="cms-reason">{{ String(item.msg.reason) }}</span>
        <p class="cms-text">{{ String(item.msg.text) }}</p>
        <div class="cms-actions">
          <button type="button" class="cms-btn" @click="respond(item.msg)">{{ String(item.msg.action) }}</button>
          <button type="button" class="cms-btn ghost" @click="hide(item.index, 'snooze')">稍后</button>
          <button type="button" class="cms-btn ghost" @click="hide(item.index, 'mute')">不再提醒</button>
        </div>
      </article>
    </div>
    <p v-else class="cms-empty">暂无教练建议。有新信号时，这里会出现一条带最小行动的提醒。</p>
  </section>
</template>

<style scoped>
.coach-message-stream {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.cms-head small {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.cms-head h3 {
  margin: 2px 0 var(--space-3);
  font-size: var(--font-size-md);
  font-weight: 800;
}

.cms-list {
  display: grid;
  gap: var(--space-3);
}

.cms-bubble {
  padding: var(--space-3);
  border: 1px solid var(--color-role-border);
  border-radius: var(--radius-md);
  background: var(--color-role-soft);
}

.cms-reason {
  display: inline-block;
  padding: 1px 8px;
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--color-role);
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.cms-text {
  margin: var(--space-2) 0 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-xs);
  line-height: 1.7;
}

.cms-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: var(--space-3);
}

.cms-btn {
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--color-role);
  color: #fff;
  padding: 6px 14px;
  font-size: var(--font-size-xs);
  font-weight: 700;
  cursor: pointer;
}

.cms-btn.ghost {
  background: var(--color-surface);
  color: var(--color-role);
  border: 1px solid var(--color-role-border);
}

.cms-empty {
  margin: 0;
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  text-align: center;
}
</style>

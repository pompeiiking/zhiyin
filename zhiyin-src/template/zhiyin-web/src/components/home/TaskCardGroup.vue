<script setup lang="ts">
import { computed } from 'vue'

import { useSessionStore } from '@/stores/session'

// 首页任务卡组（《前端页面设计》§4.1「任务卡组：7 个任务入口（用户语言，点击即路由）」）。
//
// ⚠️ 这里曾经**根本没有这一区**：bootstrap 下发的 7 条 `task_entries` 与文案包
//    `home.task_group_title` 在前端零消费，首页只有一张主 CTA 裸跳核心对话页。
//    结果是从首页进对话页时没有任何任务，发消息必然报"缺少当前任务"。
//
// 现在：入口清单与标题**全部来自 bootstrap**（任务入口属动态资源，《AGENTS.md》§8），
// 前端不硬编码任何一条任务、也不在点卡片时上报埋点——`home_task_select` 在
// `data/registry/track_events.json` 里是 `channel: backend`（"进入任务即可派生"），
// 前端上报会被后端拒绝。
//
// 点击只向外抛 code：进任务的完整链路（登录拦截 / 错误处理 / 写会话 / 跳转）由页面统一持有，
// 避免首页两处入口各写一套。
const session = useSessionStore()

defineProps<{
  /** 正在进入的任务入口 code，用于高亮 */
  selected: string
  /** 进入任务请求进行中，用于禁用重复点击 */
  busy: boolean
  /** 进入失败或需要登录时的提示；空串表示无提示 */
  message: string
}>()

const emit = defineEmits<{ select: [code: string] }>()

const title = computed(() => session.copyBundle['home.task_group_title'] ?? '')
</script>

<template>
  <section v-if="session.taskEntries.length" id="task-group" class="task-group">
    <div class="container">
      <div class="head">
        <h2>{{ title }}</h2>
        <p>选一件现在最想解决的事，直接进入对应环节；不知道选哪个就选最后一条，开口聊也行。</p>
      </div>

      <ul class="task-grid">
        <li v-for="entry in session.taskEntries" :key="entry.code">
          <button
            type="button"
            class="task-card"
            :class="{ fallback: entry.target_stage == null, active: entry.code === selected }"
            :disabled="busy"
            @click="emit('select', entry.code)"
          >
            <span class="task-label">{{ entry.label }}</span>
            <span class="task-meta">
              <template v-if="entry.target_stage == null">由编排器判定入口</template>
              <template v-else>主理 · {{ entry.lead_agent_name ?? '按环节分配' }}</template>
            </span>
            <span class="task-go">{{ busy && entry.code === selected ? '正在进入…' : '进入 →' }}</span>
          </button>
        </li>
      </ul>

      <p v-if="message" class="task-message" role="alert">{{ message }}</p>
    </div>
  </section>
</template>

<style scoped>
.task-group {
  padding: 56px 0;
  background: var(--color-bg);
  border-top: 1px solid var(--color-border);
}

.container { max-width: var(--content-max-width); margin: 0 auto; padding: 0 var(--page-gutter); }

.head { max-width: 680px; margin: 0 auto 26px; text-align: center; }
.head h2 { margin: 0 0 8px; font-size: 26px; font-weight: 800; color: var(--color-text-primary); }
.head p { margin: 0; color: var(--color-text-secondary); font-size: 14px; line-height: 1.6; }

.task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(196px, 1fr));
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.task-card {
  display: grid;
  gap: 6px;
  align-content: start;
  width: 100%;
  height: 100%;
  padding: 18px;
  text-align: left;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: transform var(--duration-base) var(--ease-standard), box-shadow var(--duration-base), border-color var(--duration-base);
}

.task-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-card); border-color: var(--blueLine); }
.task-card:disabled { opacity: 0.55; cursor: default; transform: none; box-shadow: none; }

/* 兜底「直接开聊」入口常驻：没有明确环节，视觉上与定向入口区分开 */
.task-card.fallback { background: var(--blueSoft); border-color: var(--blueLine); }

.task-card.active { border-color: var(--blue); box-shadow: var(--shadow-card); }

.task-label {
  font-size: var(--font-size-base);
  font-weight: 800;
  line-height: 1.5;
  color: var(--color-text-primary);
}

.task-meta { color: var(--color-text-muted); font-size: var(--font-size-xs); }

.task-go { margin-top: auto; padding-top: 8px; color: var(--blueD); font-size: var(--font-size-sm); font-weight: 700; }

.task-message {
  margin: 18px 0 0;
  padding: 10px 16px;
  border: 1px solid var(--amberLine);
  border-radius: var(--radius-md);
  background: var(--amberSoft);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  text-align: center;
}

@media (max-width: 640px) {
  .task-grid { grid-template-columns: minmax(0, 1fr); }
}
</style>

<script setup lang="ts">
import { computed, ref } from 'vue'

/**
 * 行为引导四选一（CONV-006，后端契约 contracts/common.py::BehaviorGuide）。
 *
 * 后端真实字段是 kind / text / question / options / task / reminder。
 * 这里不设任何兜底文案：没有 guide 就整行不渲染，字段缺失就如实留空，
 * 不用"先选一个最容易开始的动作"之类的自编内容冒充后端引导。
 */
type GuideOption = { option_id?: string; label?: string; value?: unknown }
type GuideTask = { task_id?: string; text?: string; due_date?: string | null }
type GuideReminder = { title?: string; due_at?: string | null; detail?: string }

const props = defineProps<{ guide?: Record<string, unknown> | null }>()
const emit = defineEmits<{ (event: 'choose', value: string): void; (event: 'focus-input'): void }>()

const kind = computed(() => String(props.guide?.kind ?? ''))
const text = computed(() => String(props.guide?.text ?? ''))
const question = computed(() => (props.guide?.question ? String(props.guide.question) : ''))
const task = computed<GuideTask | null>(() => (props.guide?.task as GuideTask | undefined) ?? null)
const reminder = computed<GuideReminder | null>(
  () => (props.guide?.reminder as GuideReminder | undefined) ?? null,
)
const options = computed<GuideOption[]>(() => {
  const raw = props.guide?.options
  return Array.isArray(raw) ? (raw as GuideOption[]) : []
})

/** 追问优先显示 question，其余显示 text；都没有才留空。 */
const headline = computed(() => (kind.value === 'question' ? question.value || text.value : text.value))

const done = ref(false)
const labels: Record<string, string> = { question: '追问', options: '下一步', task: '小任务', reminder: '提醒' }
const typeLabel = computed(() => labels[kind.value] ?? '行为引导')
</script>

<template>
  <div v-if="guide" class="behavior-guide">
    <span class="guide-label">{{ typeLabel }}</span>
    <span class="guide-text">{{ headline }}</span>

    <div class="guide-actions">
      <template v-if="kind === 'options'">
        <button
          v-for="(item, index) in options"
          :key="item.option_id ?? index"
          type="button"
          @click="emit('choose', String(item.label ?? ''))"
        >
          {{ item.label }}
        </button>
      </template>

      <template v-else-if="kind === 'question'">
        <button type="button" class="primary" @click="emit('focus-input')">现在就说</button>
      </template>

      <template v-else-if="kind === 'task' && task">
        <label>
          <input v-model="done" type="checkbox" @change="emit('choose', String(task.text ?? ''))" />
          {{ task.text }}
        </label>
      </template>

      <template v-else-if="kind === 'reminder' && reminder">
        <span class="guide-reminder">{{ reminder.title }}</span>
        <button type="button" class="primary" @click="emit('choose', text)">知道了</button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.behavior-guide {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 10px;
  padding: 8px var(--space-5);
  border-top: 1px solid var(--blueLine);
  background: var(--blueSoft);
}

.guide-label {
  flex: none;
  padding: 2px 9px;
  border-radius: var(--pill);
  background: var(--blue);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.guide-text { flex: 1 1 160px; min-width: 0; color: var(--gray); font-size: var(--font-size-xs); }

.guide-actions { flex: none; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }

.guide-reminder { color: var(--gray); font-size: 13px; font-weight: 600; }
button, label { min-height: 30px; padding: 5px 12px; border: 1px solid var(--blueLine); border-radius: var(--pill); background: #fff; color: var(--blueD); cursor: pointer; font-size: 13px; font-weight: 600; }
button:hover { background: var(--blueSoft); }
button.primary { background: var(--blue); border-color: var(--blue); color: #fff; }
button.primary:hover { background: var(--blueD); }
label { display: inline-flex; align-items: center; gap: var(--space-1); }
</style>

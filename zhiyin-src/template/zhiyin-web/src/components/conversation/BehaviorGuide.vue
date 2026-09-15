<script setup lang="ts">
import { computed, ref } from 'vue'
const props = defineProps<{ guide: Record<string, unknown> | null; disabled?: boolean }>()
const emit = defineEmits<{ act: [value: string] }>()
const done = ref(false)
const kind = computed(() => String(props.guide?.kind ?? ''))
const options = computed(() => (props.guide?.options as Record<string, unknown>[] | undefined) ?? [])
const task = computed(() => (props.guide?.task as Record<string, unknown> | undefined))
const reminder = computed(() => (props.guide?.reminder as Record<string, unknown> | undefined))
</script>
<template>
  <section v-if="guide?.text" class="behavior-guide" aria-label="下一步"><p class="label">下一步</p><p class="prompt">{{ String(guide.text) }}</p>
    <button v-if="kind === 'question'" type="button" :disabled="disabled" @click="emit('act', String(guide.question ?? guide.text))">回答这个问题 <span aria-hidden="true">→</span></button>
    <div v-else-if="kind === 'options'" class="options"><button v-for="(option, index) in options" :key="String(option.option_id ?? index)" :disabled="disabled" @click="emit('act', String(option.value ?? option.label ?? ''))">{{ String(option.label ?? option.value ?? '') }}</button></div>
    <label v-else-if="kind === 'task' && task" class="task"><input v-model="done" type="checkbox" :disabled="disabled" @change="done && emit('act', String(task.text ?? guide.text))" /><span>{{ String(task.text ?? guide.text) }}</span></label>
    <button v-else-if="kind === 'reminder'" type="button" :disabled="disabled" @click="emit('act', String(reminder?.title ?? guide.text))">{{ String(reminder?.title ?? '知道了') }}</button>
  </section>
</template>
<style scoped>
.behavior-guide { padding: var(--space-4); border: 1px solid var(--color-brand-border); border-radius: var(--radius-lg); background: var(--color-brand-soft); }.label { margin: 0; font-size: var(--font-size-xs); color: var(--color-link); font-weight: var(--font-weight-semibold); }.prompt { margin: var(--space-2) 0 var(--space-4); font-weight: var(--font-weight-semibold); }.options { display: flex; flex-wrap: wrap; gap: var(--space-2); }button, .task { min-height: 44px; display: inline-flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-4); border: 1px solid var(--color-brand-border); border-radius: var(--radius-pill); background: var(--color-surface); color: var(--color-link); cursor: pointer; }.task input { width: 18px; height: 18px; }
</style>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ guide?: Record<string, unknown> | null }>()
const emit = defineEmits<{ (event: 'choose', value: string): void }>()

// 行为引导四选一（CONV-006）：追问 / 选项 / 小任务 / 提醒
const type = () => String(props.guide?.type ?? 'options')
const text = () => String(props.guide?.text ?? '先选一个最容易开始的动作')
const options = () => (props.guide?.options as string[] | undefined) ?? []
const task = () => String(props.guide?.task ?? '完成一次自我盘点')
const action = () => String(props.guide?.action ?? '知道了')

const done = ref(false)
const typeLabel = () =>
  ({ ask: '追问', options: '下一步', task: '小任务', remind: '提醒' } as Record<string, string>)[type()] ?? '下一步'
</script>

<template>
  <div class="behavior-guide">
    <span class="guide-label">{{ typeLabel() }}</span>
    <span class="guide-text">{{ text() }}</span>

    <div class="guide-actions">
      <template v-if="type() === 'options'">
        <button v-for="item in options()" :key="item" type="button" @click="emit('choose', item)">{{ item }}</button>
      </template>

      <template v-else-if="type() === 'ask'">
        <button type="button" class="primary" @click="emit('choose', text())">现在就说</button>
      </template>

      <template v-else-if="type() === 'task'">
        <label><input v-model="done" type="checkbox" @change="emit('choose', task())" /> {{ task() }}</label>
      </template>

      <template v-else>
        <button type="button" class="primary" @click="emit('choose', action())">{{ action() }}</button>
        <button type="button" class="ghost" @click="emit('choose', '稍后提醒')">稍后</button>
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

.guide-actions { flex: none; display: flex; flex-wrap: wrap; gap: 6px; }
button, label { min-height: 30px; padding: 5px 12px; border: 1px solid var(--blueLine); border-radius: var(--pill); background: #fff; color: var(--blueD); cursor: pointer; font-size: 13px; font-weight: 600; }
button:hover { background: var(--blueSoft); }
button.primary { background: var(--blue); border-color: var(--blue); color: #fff; }
button.primary:hover { background: var(--blueD); }
button.ghost { background: transparent; color: var(--blueD); }
label { display: inline-flex; align-items: center; gap: var(--space-1); }
</style>

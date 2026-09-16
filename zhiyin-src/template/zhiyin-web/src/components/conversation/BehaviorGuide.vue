<script setup lang="ts">
import { ref } from 'vue'
const props = defineProps<{ guide?: Record<string, unknown> | null }>()
const emit = defineEmits<{ (event: 'choose', value: string): void }>()
const done = ref(false)
const options = ['先说说你最在意的条件', '我想先看看可选方向']
const title = () => String(props.guide?.text ?? '先选一个最容易开始的动作')
</script>

<template>
  <div class="behavior-guide"><div><strong>下一步</strong><span>{{ title() }}</span></div><div class="guide-actions"><button v-for="item in options" :key="item" type="button" @click="emit('choose', item)">{{ item }}</button><label><input v-model="done" type="checkbox" @change="emit('choose', '完成一次自我盘点')" /> 完成一次自我盘点</label></div></div>
</template>

<style scoped>
.behavior-guide { padding:var(--space-3) var(--space-4); border-top:1px solid var(--color-brand-border); background:var(--color-brand-soft); }
.behavior-guide > div:first-child { display:flex; gap:var(--space-3); align-items:center; margin-bottom:var(--space-2); color:var(--color-text-secondary); }
strong { color:var(--color-link); }
.guide-actions { display:flex; flex-wrap:wrap; gap:var(--space-2); }
button,label { min-height:36px; padding:var(--space-2) var(--space-3); border:1px solid var(--color-brand-border); border-radius:var(--radius-pill); background:var(--color-surface); color:var(--color-link); cursor:pointer; font-size:var(--font-size-xs); }
label { display:inline-flex; align-items:center; gap:var(--space-1); }
</style>

<script setup lang="ts">
const emit = defineEmits<{ (event: 'choose', value: string): void }>()
const actions = ['认领一个差距', '比较方案', '查看行动任务', '我要复盘']
</script>

<template>
  <div class="quick-actions" aria-label="快捷动作"><button v-for="item in actions" :key="item" type="button" @click="emit('choose', item)">{{ item }}</button></div>
</template>

<style scoped>
.quick-actions { display:flex; flex-wrap:wrap; gap:var(--space-2); padding:var(--space-2) var(--space-6); }
button { border:0; border-radius:var(--radius-pill); background:var(--color-bg); color:var(--color-link); padding:var(--space-2) var(--space-3); cursor:pointer; font-size:var(--font-size-xs); }
button:hover { background:var(--color-brand-soft); }
</style>

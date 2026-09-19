<script setup lang="ts">
const emit = defineEmits<{ (event: 'choose', value: string): void }>()
const actions = ['认领一个差距', '比较方案', '查看行动任务', '我要复盘']
</script>

<template>
  <div class="quick-actions" aria-label="快捷动作"><button v-for="item in actions" :key="item" type="button" @click="emit('choose', item)">{{ item }}</button></div>
</template>

<style scoped>
.quick-actions { display: flex; flex-wrap: wrap; gap: 8px; padding: 11px var(--space-5) 0; }
button { border: 1px solid var(--blueLine); border-radius: var(--pill); background: #fff; color: var(--blueD); padding: 8px 15px; cursor: pointer; font-size: 14px; font-weight: 600; }
button:hover { background: var(--blueSoft); border-color: var(--blue); }
</style>

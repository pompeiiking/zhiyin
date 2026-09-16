<script setup lang="ts">
import { ref } from 'vue'
const props = defineProps<{ disclosure?: Record<string, unknown> | null }>()
const open = ref(false)
const text = () => String(props.disclosure?.message ?? props.disclosure?.reason ?? '本轮由新的主理继续协助你。')
</script>

<template>
  <div v-if="disclosure" class="disclosure-row"><button type="button" @click="open = !open"><strong>主理交接</strong>{{ text() }} <span aria-hidden="true">{{ open ? '收起' : '查看依据' }}</span></button><p v-if="open">系统根据当前任务环节、画像缺口与本轮目标安排协作角色。此处为演示说明。</p></div>
</template>

<style scoped>
.disclosure-row { padding:var(--space-2) var(--space-4); background:var(--color-role-soft); color:var(--color-text-secondary); font-size:var(--font-size-xs); }
button { width:100%; border:0; background:none; color:inherit; text-align:left; cursor:pointer; }
strong { color:var(--color-role); margin-right:var(--space-2); }
button span { float:right; color:var(--color-role); }
p { margin:var(--space-2) 0 0; padding-left:var(--space-8); }
</style>

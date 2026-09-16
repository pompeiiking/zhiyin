<script setup lang="ts">
import { ref } from 'vue'
const props = defineProps<{ theory?: Record<string, unknown> }>()
const open = ref(false)
const name = () => String(props.theory?.name ?? props.theory?.title ?? '职业咨询方法')
</script>

<template>
  <span class="theory-wrap"><button type="button" class="theory-tag" :aria-expanded="open" @click="open = !open">{{ name() }}</button><span v-if="open" class="theory-popover" role="status">把你的信息与成熟职业咨询框架对照，帮助解释当前结论。</span></span>
</template>

<style scoped>
.theory-wrap { position:relative; display:inline-flex; }
.theory-tag { border:1px solid var(--color-role-border); border-radius:var(--radius-pill); padding:2px var(--space-2); background:var(--color-role-soft); color:var(--color-role); font-size:var(--font-size-xs); cursor:pointer; }
.theory-popover { position:absolute; z-index:2; top:calc(100% + 6px); left:0; width:220px; padding:var(--space-3); border-radius:var(--radius-md); background:var(--color-ink-card, var(--inkCard)); color:var(--color-text-inverse); font-size:var(--font-size-xs); box-shadow:var(--shadow-overlay); }
</style>

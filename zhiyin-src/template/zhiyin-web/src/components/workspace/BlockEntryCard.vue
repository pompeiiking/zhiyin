<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  blocks: Record<string, unknown>
  featureFlags: Record<string, boolean>
}>()

/**
 * 功能块 code → 展示文案的兜底映射。
 * 后端 blocks 目前只下发 code 列表（available）与成就徽章键，未下发 label；
 * 文案以后应随动态资源下发（R-API-001），此处仅作 UI 兜底，避免空渲染。
 */
const LABELS: Record<string, string> = {
  report_full_text: '报告全文',
  export: '导出',
  calendar: '关键节点日历',
  achievements: '成长成就',
  mentor: '导师共享',
  demo: '自动演示',
}

const ROUTES: Record<string, string> = {
  report_full_text: '/report',
}

const available = computed(() => {
  const list = Array.isArray(props.blocks.available) ? (props.blocks.available as string[]) : []
  return list.filter((code) => props.featureFlags[code] === true)
})
</script>

<template>
  <section class="block-entry-card">
    <h3>功能入口</h3>
    <p v-if="!available.length" class="empty">暂无可用功能。</p>
    <ul v-else class="blocks">
      <li v-for="code in available" :key="code" class="block">
        <RouterLink v-if="ROUTES[code]" :to="ROUTES[code]" class="block-link">
          {{ LABELS[code] ?? code }} <span aria-hidden="true">→</span>
        </RouterLink>
        <button v-else type="button" class="block-link">{{ LABELS[code] ?? code }}</button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.block-entry-card h3 {
  margin: 0 0 var(--space-3);
  font-size: var(--font-size-md);
}

.empty {
  color: var(--color-text-muted);
}

.blocks {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.block-link {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  min-height: 44px;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  text-align: left;
  cursor: pointer;
}

.block-link:hover {
  border-color: var(--color-brand);
  color: var(--color-brand);
}
</style>

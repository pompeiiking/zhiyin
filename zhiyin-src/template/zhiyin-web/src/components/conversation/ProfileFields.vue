<script setup lang="ts">
import { computed } from 'vue'
import type { ProfilePanelView } from '@/api/schema'

// 画像字段卡（CONV-003）：右栏「详细属性」的层次化落点。
// L1 容器卡（仅此层描边）→ L2 维度分组（无描边、浅底）→ L3 属性行（字段名/值/状态徽记）。
type Field = Record<string, unknown>

const props = defineProps<{ profile?: ProfilePanelView | null }>()

const groups = computed(() => {
  const fields = (props.profile?.fields ?? []) as Field[]
  const map = new Map<string, Field[]>()
  for (const f of fields) {
    const g = String(f.group ?? '其他')
    if (!map.has(g)) map.set(g, [])
    map.get(g)!.push(f)
  }
  return Array.from(map.entries()).map(([group, items]) => ({ group, items }))
})

const coverage = computed(() => Math.round((props.profile?.coverage ?? 0) * 100))
const confidence = computed(() => Math.round((props.profile?.overall_confidence ?? 0) * 100))

function fieldName(f: Field) {
  return String(f.name ?? f.label ?? '字段')
}
function fieldValue(f: Field) {
  return String(f.value ?? '—')
}
function statusClass(s: unknown) {
  if (s === 'done') return 'ok'
  if (s === 'low') return 'low'
  if (s === 'risk') return 'risk'
  return 'pending'
}
</script>

<template>
  <section class="profile-fields" aria-label="个人画像字段">
    <header class="pf-head">
      <div>
        <small>① 采集建模</small>
        <h3>个人画像</h3>
      </div>
      <div class="pf-metrics">
        <span class="metric"><b>{{ coverage }}%</b><small>覆盖度</small></span>
        <span class="metric"><b>{{ confidence }}%</b><small>置信度</small></span>
      </div>
    </header>

    <div v-if="groups.length" class="pf-groups">
      <div v-for="group in groups" :key="group.group" class="pf-group">
        <p class="pf-group-title">{{ group.group }}</p>
        <div v-for="field in group.items" :key="fieldName(field)" class="pf-row">
          <span class="pf-name">{{ fieldName(field) }}</span>
          <span class="pf-value">{{ fieldValue(field) }}</span>
          <span class="pf-dot" :class="statusClass(field.status)" :title="fieldValue(field) === '待采集' ? '待采集' : '已沉淀'"></span>
        </div>
      </div>
    </div>
    <p v-else class="pf-empty">完成对话后，这里会沉淀你的画像字段。</p>
  </section>
</template>

<style scoped>
/* L1 容器卡：唯一允许描边的一层 */
.profile-fields {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.pf-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.pf-head > div:first-child { min-width: 0; }

.pf-head small {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  white-space: nowrap;
}

.pf-head h3 {
  margin: 2px 0 0;
  font-size: var(--font-size-md);
  font-weight: 800;
  white-space: nowrap;
}

.pf-metrics {
  display: flex;
  gap: var(--space-3);
}

.metric {
  display: grid;
  justify-items: end;
  gap: 1px;
}

.metric b {
  font-size: var(--font-size-sm);
  font-weight: 800;
  color: var(--color-brand-strong);
}

.metric small {
  color: var(--color-text-muted);
  font-size: 10px;
}

.pf-groups {
  display: grid;
  gap: var(--space-3);
}

/* L2 分组：无描边，靠浅底区分 */
.pf-group {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.pf-group-title {
  margin: 0 0 var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

/* L3 属性行：无边框无底色，行间用极浅分隔线 */
.pf-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--space-3);
  padding: 6px 0;
  font-size: var(--font-size-xs);
}

.pf-row + .pf-row {
  border-top: 1px solid var(--color-border);
}

.pf-name {
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.pf-value {
  color: var(--color-text-primary);
  overflow-wrap: break-word;
  text-align: right;
}

/* 状态徽记：已沉淀绿点、待采集灰点、低置信度琥珀、风险红 */
.pf-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}

.pf-dot.ok { background: var(--color-success); }
.pf-dot.pending { background: var(--color-text-muted); }
.pf-dot.low { background: var(--color-warning); }
.pf-dot.risk { background: var(--color-danger); }

.pf-empty {
  margin: 0;
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  text-align: center;
}
</style>

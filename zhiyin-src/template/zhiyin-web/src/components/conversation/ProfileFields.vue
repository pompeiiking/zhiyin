<script setup lang="ts">
import { computed } from 'vue'
import type { ProfilePanelView } from '@/api/schema'
import { useConversationStore } from '@/stores/conversation'
import { useSessionStore } from '@/stores/session'

// 画像字段卡（CONV-003）：右栏「详细属性」的层次化落点。
// L1 容器卡（仅此层描边）→ L2 维度分组（无描边、浅底）→ L3 属性行（字段名/值/状态徽记）。
//
// 字段形状来自后端 `profile_panel.fields`：`{ key, value, confidence, source, updated_at, evidence }`。
// 此前这里读 `f.group` / `f.name`——两个字段后端都不下发，于是所有字段都被归到"其他"、
// 名字统一显示成"字段"。现在按真实形状渲染：名字取文案包的 `profile.field.<key>`；
// 分组只在后端确实下发 `group` 时才分组，否则平铺。
type Field = Record<string, unknown>

const props = defineProps<{ profile?: ProfilePanelView | null }>()
const session = useSessionStore()
const conversation = useConversationStore()

// 环节标签只能来自后端下发的 pipeline_cards（谁是 active 就是谁）。
// 此前这里硬编码「① 采集建模」，导致在④复盘会话里也显示"①采集建模"，与中栏/左栏矛盾。
// 管线未下发时不猜环节，整行留空。
const stageLabel = computed(() => {
  const card = conversation.pipeline.find((item) => Boolean(item.active))
  return card ? String((card as Record<string, unknown>).title ?? '').trim() : ''
})

const groups = computed(() => {
  const fields = (props.profile?.fields ?? []) as Field[]
  const map = new Map<string, Field[]>()
  for (const f of fields) {
    const g = String(f.group ?? '')
    if (!map.has(g)) map.set(g, [])
    map.get(g)!.push(f)
  }
  return Array.from(map.entries()).map(([group, items]) => ({ group, items }))
})

const coverage = computed(() => Math.round((props.profile?.coverage ?? 0) * 100))
const confidence = computed(() => Math.round((props.profile?.overall_confidence ?? 0) * 100))

// FR-COLLECT-004：① 卡除了覆盖度/置信度，还要让用户看见「哪些还不够」。
// 缺口清单由后端按决策 5 口径算好经 `profile_panel.gaps` 下发，前端只把 key
// 翻成文案包里的字段名，不自行推断缺口。
const gaps = computed(() =>
  ((props.profile?.gaps ?? []) as Field[])
    .map((gap) => String(gap.key ?? ''))
    .filter(Boolean)
    .map((key) => session.copyBundle[`profile.field.${key}`] ?? key),
)

function fieldName(f: Field) {
  const key = String(f.key ?? '')
  if (!key) return String(f.name ?? f.label ?? '字段')
  return session.copyBundle[`profile.field.${key}`] ?? key
}
/** 值可能是字符串、字符串数组或对象，统一成可读文本；空值如实显示"待采集"。 */
function fieldValue(f: Field) {
  const value = f.value
  if (value === null || value === undefined) return '待采集'
  if (Array.isArray(value)) return value.map((item) => String(item)).join(' / ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
function statusClass(f: Field) {
  if (f.value === null || f.value === undefined) return 'pending'
  const confidence = typeof f.confidence === 'number' ? f.confidence : 1
  if (confidence < 0.6) return 'low'
  if (f.status === 'risk') return 'risk'
  return 'ok'
}
</script>

<template>
  <section class="profile-fields" aria-label="个人画像字段">
    <header class="pf-head">
      <div>
        <small v-if="stageLabel">{{ stageLabel }}</small>
        <h3>个人画像</h3>
      </div>
      <div class="pf-metrics">
        <span class="metric"><b>{{ coverage }}%</b><small>覆盖度</small></span>
        <span class="metric"><b>{{ confidence }}%</b><small>置信度</small></span>
      </div>
    </header>

    <div v-if="groups.length" class="pf-groups">
      <div v-for="group in groups" :key="group.group" class="pf-group">
        <p v-if="group.group" class="pf-group-title">{{ group.group }}</p>
        <div v-for="field in group.items" :key="String(field.key)" class="pf-row">
          <span class="pf-name">{{ fieldName(field) }}</span>
          <span class="pf-value">{{ fieldValue(field) }}</span>
          <span class="pf-dot" :class="statusClass(field)" :title="fieldValue(field) === '待采集' ? '待采集' : '已沉淀'"></span>
        </div>
      </div>
    </div>
    <p v-else class="pf-empty">完成对话后，这里会沉淀你的画像字段。</p>

    <p v-if="gaps.length" class="pf-gaps">
      <span class="pf-gaps-label">待补</span>{{ gaps.join('、') }}
    </p>
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

/* 缺口行：只在下发缺口时出现，颜色区分于已沉淀字段（提醒"还不够"而非报错） */
.pf-gaps {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  margin: var(--space-3) 0 0;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--color-warning-soft, var(--color-bg));
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  line-height: 1.7;
}

.pf-gaps-label {
  flex: none;
  color: var(--color-warning, var(--color-text-muted));
  font-weight: 800;
}
</style>

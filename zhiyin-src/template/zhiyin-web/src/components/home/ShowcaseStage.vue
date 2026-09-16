<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

type ShowcaseItem = {
  key: string
  label: string
  title: string
  summary: string
  rows: string[]
}

const props = defineProps<{ items?: ShowcaseItem[] }>()
const items = props.items ?? []

const active = ref(0)
let timer: number | undefined
const paused = ref(false)

function select(index: number) { active.value = index }
function advance() { if (!paused.value) active.value = (active.value + 1) % items.length }
function onKey(event: KeyboardEvent) {
  if (event.key === 'ArrowRight') { event.preventDefault(); active.value = (active.value + 1) % items.length }
  if (event.key === 'ArrowLeft') { event.preventDefault(); active.value = (active.value + items.length - 1) % items.length }
}
onMounted(() => { timer = window.setInterval(advance, 9000) })
onBeforeUnmount(() => { if (timer) window.clearInterval(timer) })
</script>

<template>
  <section v-if="items.length" class="showcase reveal" aria-labelledby="showcase-title" @mouseenter="paused = true" @mouseleave="paused = false">
    <div class="showcase-heading">
      <div>
        <span class="section-kicker">产品实感展示台</span>
        <h2 id="showcase-title">从困惑到行动，每一步都有产出</h2>
        <p>下面是一次完整职业探索的演示数据。切换环节，看看系统会留下什么。</p>
      </div>
      <span class="demo-tag">演示数据</span>
    </div>
    <div class="showcase-tabs" role="tablist" aria-label="五环节展示台" @keydown="onKey">
      <button v-for="(item, index) in items" :key="item.key" type="button" role="tab" :aria-selected="active === index" :tabindex="active === index ? 0 : -1" :class="{ active: active === index }" @click="select(index)">
        <span class="tab-number">0{{ index + 1 }}</span>{{ item.label }}
      </button>
    </div>
    <article class="showcase-panel" role="tabpanel" :aria-label="items[active].label">
      <div class="panel-copy"><span class="panel-stage">第 {{ active + 1 }} 环节</span><h3>{{ items[active].title }}</h3><p>{{ items[active].summary }}</p><button type="button" class="panel-link" @click="paused = !paused">{{ paused ? '继续播放' : '暂停播放' }} <span aria-hidden="true">↗</span></button></div>
      <div class="evidence-list"><div v-for="(row, index) in items[active].rows" :key="row" class="evidence-row"><span>{{ String(index + 1).padStart(2, '0') }}</span><strong>{{ row }}</strong><i :class="{ success: index === items[active].rows.length - 1 }" aria-hidden="true"></i></div></div>
    </article>
  </section>
</template>

<style scoped>
.showcase { margin-bottom: var(--space-12); }
.showcase-heading { display:flex; justify-content:space-between; gap:var(--space-6); align-items:flex-end; margin-bottom:var(--space-6); }
.section-kicker,.panel-stage { color:var(--color-link); font-size:var(--font-size-xs); }
h2 { margin:var(--space-2) 0; font-size:var(--font-size-2xl); }
.showcase-heading p,.panel-copy p { color:var(--color-text-secondary); margin:0; }
.demo-tag { flex-shrink:0; padding:var(--space-2) var(--space-3); border-radius:var(--radius-pill); background:var(--color-warning-soft); color:var(--color-warning); font-size:var(--font-size-xs); }
.showcase-tabs { display:grid; grid-template-columns:repeat(5,1fr); gap:var(--space-2); border-bottom:1px solid var(--color-border); }
.showcase-tabs button { min-height:52px; border:0; border-bottom:3px solid transparent; background:transparent; color:var(--color-text-secondary); text-align:left; cursor:pointer; }
.showcase-tabs button:hover,.showcase-tabs button.active { color:var(--color-link); border-bottom-color:var(--color-brand); }
.tab-number { display:block; margin-bottom:var(--space-1); color:var(--color-text-muted); font-size:var(--font-size-xs); }
.showcase-panel { display:grid; grid-template-columns:1fr 1.2fr; gap:var(--space-10); padding:var(--space-8); background:linear-gradient(135deg,var(--color-surface),var(--color-brand-soft)); border:1px solid var(--color-brand-border); border-top:0; border-radius:0 0 var(--radius-lg) var(--radius-lg); }
.panel-copy h3 { margin:var(--space-3) 0 var(--space-2); font-size:var(--font-size-xl); }
.panel-link { margin-top:var(--space-6); border:0; background:none; color:var(--color-link); padding:0; cursor:pointer; }
.evidence-list { display:grid; gap:var(--space-2); align-content:center; }
.evidence-row { display:grid; grid-template-columns:32px 1fr 10px; gap:var(--space-3); align-items:center; padding:var(--space-3) var(--space-4); background:var(--color-surface); border-radius:var(--radius-md); box-shadow:var(--shadow-card); }
.evidence-row > span { color:var(--color-text-muted); font-size:var(--font-size-xs); }
.evidence-row strong { font-size:var(--font-size-sm); font-weight:var(--font-weight-medium); }
.evidence-row i { width:8px; height:8px; border-radius:50%; background:var(--color-brand); }
.evidence-row i.success { background:var(--color-success); }
@media (max-width:900px) { .showcase-panel { grid-template-columns:1fr; gap:var(--space-6); padding:var(--space-6); } }
@media (max-width:640px) { .showcase-heading { align-items:flex-start; flex-direction:column; gap:var(--space-3); } .showcase-tabs { display:flex; overflow-x:auto; scroll-snap-type:x mandatory; } .showcase-tabs button { min-width:120px; scroll-snap-align:start; } .showcase-panel { border-radius:0 0 var(--radius-md) var(--radius-md); } }
@media (prefers-reduced-motion: reduce) { .showcase-panel { transition:none; } }
</style>

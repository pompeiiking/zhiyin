<script setup lang="ts">
import { ref } from 'vue'

// 理论标签（CONV-009）：气泡 / 主理徽章 / 管线卡里的理论依据统一可点开，
// 展开为一张「理论模型卡」，说明这个方法是什么、从哪来。
const props = defineProps<{ theory?: Record<string, unknown> }>()
const open = ref(false)

const name = () => String(props.theory?.name ?? props.theory?.title ?? '职业咨询方法')
const abbr = () => String(props.theory?.abbr ?? props.theory?.alias ?? '')
const def = () =>
  String(
    props.theory?.def ??
      props.theory?.definition ??
      '把一个成熟的职业咨询框架，套到你的真实信息上，帮助你解释「为什么会给出这个结论」。',
  )
const source = () => String(props.theory?.source ?? '职业咨询经典框架（演示数据）')
</script>

<template>
  <span class="theory-wrap">
    <button type="button" class="theory-tag" :aria-expanded="open" @click="open = !open">
      {{ name() }}
      <i aria-hidden="true">▾</i>
    </button>
    <Transition name="pop">
      <div v-if="open" class="theory-popover" role="dialog" aria-label="理论模型卡">
        <header class="tp-head">
          <strong>{{ name() }}</strong>
          <small v-if="abbr()">{{ abbr() }}</small>
        </header>
        <p class="tp-def">{{ def() }}</p>
        <p class="tp-source">出处：{{ source() }}</p>
      </div>
    </Transition>
  </span>
</template>

<style scoped>
.theory-wrap {
  position: relative;
  display: inline-flex;
}

.theory-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--color-role-border);
  border-radius: var(--radius-pill);
  padding: 2px 8px;
  background: var(--color-role-soft);
  color: var(--color-role);
  font-size: var(--font-size-xs);
  font-weight: 600;
  cursor: pointer;
  line-height: 1.5;
}

.theory-tag:hover {
  border-color: var(--color-role);
}

.theory-tag i {
  font-style: normal;
  font-size: 9px;
  opacity: 0.7;
  transition: transform var(--duration-fast) var(--ease-standard);
}

.theory-tag[aria-expanded='true'] i {
  transform: rotate(180deg);
}

.theory-popover {
  position: absolute;
  z-index: 30;
  top: calc(100% + 8px);
  left: 0;
  width: 240px;
  padding: var(--space-3);
  border: 1px solid var(--color-role-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-overlay);
}

.tp-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 8px;
}

.tp-head strong {
  font-size: var(--font-size-sm);
  font-weight: 800;
}

.tp-head small {
  font-size: var(--font-size-xs);
  color: var(--color-role);
  font-weight: 600;
}

.tp-def {
  margin: 0;
  font-size: var(--font-size-xs);
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.tp-source {
  margin: 8px 0 0;
  padding-top: 8px;
  border-top: 1px dashed var(--color-border);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

/* 展开过渡 */
.pop-enter-active,
.pop-leave-active {
  transition: opacity var(--duration-fast) var(--ease-standard), transform var(--duration-fast) var(--ease-standard);
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>

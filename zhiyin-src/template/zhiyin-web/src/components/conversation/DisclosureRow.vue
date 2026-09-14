<script setup lang="ts">
// 显式告知行（全局约束②）。
//
// 触发场合三种（对应后端 Disclosure.kind）：
//   lead_change        换主理 —— "接下来由 职业顾问 接手，因为…"
//   theory_change      换理论依据
//   conclusion_change  结论变化
//
// 位置：中栏对话顶部。必须是"一行可点开依据"的解释，不能只是一句提示。
// 没有告知内容时不渲染，不占位。
//
// 埋点：中栏出现换主理告知行 → conv_lead_handoff
// TODO(骨架): 按 disclosure.kind 渲染文案并支持点开依据
</script>

<template>
  <div v-if="false" class="disclosure-row">
    <!-- TODO(骨架): 告知文案 + 可点开的依据 -->
  </div>
</template>

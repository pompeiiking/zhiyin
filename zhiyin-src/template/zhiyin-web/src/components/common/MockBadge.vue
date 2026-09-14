<script setup lang="ts">
// 全局 · Mock / 演示来源标注（架构评估 B5 的落点）。
//
// 第一期模型走 LocalOrMockLLM，产出文案是"（第一期 Mock 产出，未接真实模型）"。
// 这类内容会**直接作为结论与主理标签流到 UI**：不加标注，演示会被误读成真实能力。
//
// 用法：包在结论、报告、方案、计划等"看起来像结论"的内容外层；
// 文案取 bootstrap.copyBundle['mock.source_notice']，不在组件里写死。
//
// 第二期接真实模型后，由后端把来源标记为 real，本组件自动不渲染。
// TODO(骨架): 按内容来源标记决定是否渲染
</script>

<template>
  <span class="mock-badge">
    <!-- TODO(骨架): Mock / 演示来源标注 -->
  </span>
</template>

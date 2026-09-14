<script setup lang="ts">
// 右栏 · 管线卡容器（①-⑤，§4.2）。
//
// 全局约束①的落点：报告 / 方案 / 计划的全文都挂在这里，不进对话流。
// 当前环节高亮；点击可展开三态内容。
//
// 埋点：进入某微循环环节（右栏卡高亮）→ conv_loop_enter
// TODO(骨架): 遍历 conversation.pipeline 渲染 5 张 PipelineCard，标记 active
</script>

<template>
  <aside class="pipeline-panel">
    <!-- TODO(骨架): ①-⑤ 五张 PipelineCard -->
  </aside>
</template>

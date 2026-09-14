<script setup lang="ts">
// 三态管线卡（§7 组件基线：三态管线卡）。
//
// 三种可展开状态，对应后端 PipelineCardView：
//   态① current_output  当前产出摘要
//   态② theory_models   可展开的理论模型
//   态③ evaluation      可展开的评价状态
//
// status: empty / in_progress / done 三值决定卡片外形态。
// TODO(骨架): 渲染卡头 + 三个可展开区
</script>

<template>
  <div class="pipeline-card">
    <!-- TODO(骨架): 卡头 + 三态展开区 -->
  </div>
</template>

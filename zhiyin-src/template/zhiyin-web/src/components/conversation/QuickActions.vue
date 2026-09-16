<script setup lang="ts">
// 对话页 · 快捷行为组（§4.2，中栏底部）。
//
// 与 BehaviorGuide 的分工：BehaviorGuide 承载后端下发的"本轮必做的下一步"
// （四选一，必须渲染出可点元素）；QuickActions 是**用户主动可选**的常用动作
// （认领差距 / 比较方案 / 勾任务 / 我要复盘），不替代行为引导。
//
// 口径：动作项不硬编码中文，取自 bootstrap.copyBundle 的 key；
// 触发后走 conversation store 的相应 action，并落对应埋点。
// TODO(骨架): 渲染动作按钮并绑定 store action
</script>

<template>
  <div class="quick-actions">
    <!-- TODO(骨架): 常用动作按钮组 -->
  </div>
</template>

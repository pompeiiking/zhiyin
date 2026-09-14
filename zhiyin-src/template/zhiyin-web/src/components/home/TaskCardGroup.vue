<script setup lang="ts">
// 首页 · 任务卡组（§4.1）。
//
// 口径（三条，缺一不可）：
//   1. 文案**全部来自 bootstrap.taskEntries**，前端不硬编码任何任务名；
//   2. 卡片点击 → conversation.enterTask(code) → 切到 #screen-conv；
//   3. 「直接开聊」常驻（targetStage 为空的那条），走编排器意图识别，
//      识别不准时回落到澄清追问，**不硬跳环节**。
//
// 埋点：home_task_select / home_chat_open（《前端设计 v1.0》§8）。
// TODO(骨架): 渲染任务卡并绑定 enterTask
</script>

<template>
  <section class="task-card-group">
    <!-- TODO(骨架): 任务卡列表（文案取自动态资源，不写死） -->
  </section>
</template>

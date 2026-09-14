<script setup lang="ts">
// 核心对话页 #screen-conv（P0，登录用户，三栏编排）
//
// 三栏布局（前端设计文档 §4.2）：
//   左栏 SessionList      并行任务会话管理
//   中栏 ChatStream       当前主理对话 + 显式告知 + 行为引导
//   右栏 PipelinePanel    ①-⑤ 三态管线卡
//
// 三条全局约束在本页强制成立：
//   1. 长内容不进对话流 —— 中栏只说最短结论，全文落右栏卡与工作台
//   2. 换主理必须显式告知 —— 中栏顶部出现 DisclosureRow
//   3. 每轮以行为引导收尾 —— BehaviorGuide 必须渲染出可点元素
//
// 窄屏重排见 §6.2（右栏折叠为 Sheet）。
// TODO(骨架): 组装三栏，绑定 conversation store
</script>

<template>
  <main data-anchor="screen-conv" class="conv-page">
    <!-- TODO(骨架): <SessionList /> <ChatStream /> <PipelinePanel /> -->
  </main>
</template>

<script setup lang="ts">
// 智能工作台 #screen-wb（P0，登录用户）
//
// 按 ①-⑤ 分层聚合活资产（前端设计文档 §4.3）：
//   ① 画像状态    ProfilePanel
//   ② 诊断与报告版本
//   ③ 方案与历史版本
//   ④ 计划与日历
//   ⑤ 跟踪与预警 + 教练消息流
//   功能块入口：报告全文 / 导出 / 日历 / 成就 / 导师 / 自动演示
//
// 埋点：进入工作台 → wb_enter
// TODO(骨架): 渲染五层折叠容器，进入时调 workspace.load()
</script>

<template>
  <main data-anchor="screen-wb" class="wb-page">
    <!-- TODO(骨架): ①-⑤ StagePanel + BlockEntryCard 功能块入口 -->
  </main>
</template>

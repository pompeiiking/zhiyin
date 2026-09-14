<script setup lang="ts">
// 完整报告页 #screen-report（P0，挂在工作台资产上）
//
// 口径（前端设计文档 §4.4）：左侧目录导航 + 全文区块 + 导出操作。
// 报告内容来自 GET /app/report/full-text（只读资产版本，不重新生成）。
//
// 埋点：打开完整报告页 → diagnosis_view
// TODO(骨架): 渲染目录与 15 维区块；导出按 feature_flags.export 决定是否可见
</script>

<template>
  <main data-anchor="screen-report" class="report-page">
    <!-- TODO(骨架): <ReportToc /> + 全文区块 + 导出按钮 -->
  </main>
</template>

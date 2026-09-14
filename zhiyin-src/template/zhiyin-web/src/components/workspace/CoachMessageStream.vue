<script setup lang="ts">
// 工作台 · 教练消息流（§4.3 第 ⑤ 层 / FR-WB-006）。
//
// 陪伴教练的主动消息（提醒 / 预警 / 复盘邀请）集中在这里呈现，
// 数据来自 workspace.coachMessages（后端来自 TrackEvent）。
//
// 口径：**主动干预必须由真实行为信号触发**（停滞阈值等参数来自
// data/registry/policy_params.json），前端不自己判断"该提醒了"，
// 只负责展示与响应（review_warning_show / review_warning_response）。
// TODO(骨架): 渲染消息流并绑定响应动作
</script>

<template>
  <section class="coach-message-stream">
    <!-- TODO(骨架): 教练消息列表 -->
  </section>
</template>

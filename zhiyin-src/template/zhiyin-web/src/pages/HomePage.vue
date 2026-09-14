<script setup lang="ts">
// 首页 #screen-home（P0，全身份可见）
//
// 内容口径（前端设计文档 §4.1）：
//   - 任务卡组：迷茫 / 验证方向 / 拿不准 / 不知怎么动 / 卡住 / 复盘 / 直接开聊
//     文案由 GET /app/bootstrap 下发，前端不硬编码
//   - 方法论示例入口（脱敏，标注演示数据）
//   - 顶栏身份区：[登录/注册] 或 [头像·昵称·身份徽章]
//
// 埋点：点击任务卡 → home_task_select；点击「直接开聊」→ home_chat_open
// TODO(骨架): 渲染任务卡组并绑定 conversation.enterTask
</script>

<template>
  <main data-anchor="screen-home">
    <!-- TODO(骨架): 任务卡组 / 方法论示例 / 信任区文案 -->
  </main>
</template>

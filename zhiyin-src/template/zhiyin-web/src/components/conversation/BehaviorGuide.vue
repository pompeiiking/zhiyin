<script setup lang="ts">
// 行为引导（全局约束③，最重要的一件）。
//
// 任何一轮回复的结尾必须是四选一，且页面上必须存在对应的可点元素：
//   question  一个追问         → 输入框聚焦 + 提示语
//   options   一组选项         → 渲染为可点选项
//   task      一个小任务       → 渲染为可勾选任务
//   reminder  一条提醒         → 渲染为提醒条
//
// 禁止空转寒暄与无下一步的总结。对应后端 BehaviorGuide。
//
// 埋点：认领差距 gap_claim / 比较方案 decision_compare / 做出选择 decision_select /
//       修改选择 decision_reselect / 勾掉任务 action_task_done
// TODO(骨架): 按 guide.kind 渲染四种形态并绑定动作
</script>

<template>
  <div class="behavior-guide">
    <!-- TODO(骨架): 按 kind 切换四种形态 -->
  </div>
</template>

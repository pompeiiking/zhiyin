<script setup lang="ts">
// 版本 diff 视图（§7 组件基线：版本 diff 视图）。
//
// 展示"因更新了 X，v1 → v2 的差异"。这是工作台"活资产"主张的可见证据：
// 让用户看到资产确实在跟着自己变，而不是一份生成完就死的报告。
//
// 数据来自后端 AssetVersionView：version / depends_on_profile_keys / diff_from_previous。
// TODO(骨架): 渲染版本号、依赖的画像字段、diff 文案
</script>

<template>
  <div class="version-diff">
    <!-- TODO(骨架): v(n-1) → v(n) 差异 -->
  </div>
</template>

<script setup lang="ts">
// 全局框架：顶栏 + 主线导航 + 页面出口。
// 口径见《前端页面设计 v1.0》§3.2。
// TODO(骨架): 组合 TopBar 与 RouterView；启动时调 session.loadBootstrap()
</script>

<template>
  <div class="app-shell">
    <!-- TODO(骨架): <TopBar /> <RouterView /> -->
    <slot />
  </div>
</template>

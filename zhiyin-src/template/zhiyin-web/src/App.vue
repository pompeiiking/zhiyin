<script setup lang="ts">
import { onMounted } from 'vue'

import AppShell from '@/components/common/AppShell.vue'
import { useSessionStore } from '@/stores/session'

// 全局框架：启动时拉一次 bootstrap，供顶栏与首页渲染。
// 对应前端设计文档 §3.2：顶层导航仅「首页 / 核心对话页 / 智能工作台」三个主线互达。
const session = useSessionStore()

onMounted(async () => {
  try {
    await session.loadBootstrap()
  } catch (error) {
    // 后端 Facade 未接时 bootstrap 会失败；不让白屏，页面渲染空态即可。
    console.error('bootstrap 加载失败', error)
  }
})
</script>

<template>
  <AppShell>
    <RouterView />
  </AppShell>
</template>

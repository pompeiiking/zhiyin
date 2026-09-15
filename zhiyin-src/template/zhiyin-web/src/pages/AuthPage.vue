<script setup lang="ts">
import { onActivated, onMounted } from 'vue'
import { useSessionStore } from '@/stores/session'
const session = useSessionStore()
function open() { if (!session.isLoggedIn) session.openLogin() }
onMounted(open)
onActivated(open)
</script>

<template>
  <section class="auth-page container">
    <h1>{{ session.isLoggedIn ? '你已登录' : '继续你的职业探索' }}</h1>
    <p>{{ session.isLoggedIn ? '从首页选择你现在想解决的事。' : '登录后，将你的每一次探索连接起来。' }}</p>
    <button v-if="!session.isLoggedIn" @click="open">登录 / 注册</button>
    <RouterLink :to="{ name: 'home' }">返回首页</RouterLink>
  </section>
</template>

<style scoped>
.auth-page { padding-block: var(--space-16); text-align: center; }
p { color: var(--color-text-secondary); }
button { min-height: 44px; margin: var(--space-4); padding: var(--space-3) var(--space-6); border: 0; border-radius: var(--radius-pill); background: var(--color-action-bg); color: var(--color-text-inverse); }
</style>

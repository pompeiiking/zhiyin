<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'

import { useSessionStore } from '@/stores/session'

// 顶栏（§3.2）：常驻 [登录/注册] 或 [头像·昵称·身份徽章]；
// 主线导航只有三个（首页 / 核心对话页 / 智能工作台），菜单由 bootstrap 下发。
const session = useSessionStore()
const route = useRoute()
const { appName, identity, menus, isLoggedIn } = storeToRefs(session)

const navItems = computed(() =>
  menus.value
    .filter((m) => m.visible !== false)
    .slice()
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)),
)

const nickname = computed(() => identity.value.nickname ?? '')
const role = computed(() => identity.value.role ?? '')
const avatar = computed(() => identity.value.avatar ?? '')
</script>

<template>
  <header class="top-bar">
    <RouterLink class="brand" to="/">
      <span class="brand-mark" aria-hidden="true">职</span>
      <span class="brand-name">{{ appName || '职引' }}</span>
    </RouterLink>

    <nav class="main-nav" aria-label="主导航">
      <RouterLink
        v-for="item in navItems"
        :key="item.key"
        class="nav-link"
        :class="{ 'is-active': route.path === item.route }"
        :to="item.route"
      >
        {{ item.label }}
      </RouterLink>
    </nav>

    <div class="identity">
      <template v-if="isLoggedIn">
        <span v-if="avatar" class="avatar">{{ avatar }}</span>
        <span class="nickname">{{ nickname }}</span>
        <span v-if="role" class="role-badge">{{ role }}</span>
      </template>
      <RouterLink v-else class="login-link" to="/auth">登录 / 注册</RouterLink>
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  height: 60px;
  padding: 0 var(--page-gutter);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: var(--color-brand);
  color: #fff;
  font-size: var(--font-size-sm);
}

.main-nav {
  display: flex;
  gap: var(--space-4);
  flex: 1;
}

.nav-link {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-pill);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.nav-link:hover {
  color: var(--color-brand);
}

.nav-link.is-active {
  background: var(--color-brand-soft);
  color: var(--color-brand);
}

.identity {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-brand-soft);
  color: var(--color-brand);
}

.role-badge {
  padding: 2px var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--color-role-soft);
  color: var(--color-role);
  font-size: var(--font-size-xs);
}

.login-link {
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  color: var(--color-text-secondary);
}

.login-link:hover {
  border-color: var(--color-brand);
  color: var(--color-brand);
}
</style>

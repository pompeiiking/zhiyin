<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'

import type { MenuView } from '@/api/schema'
import { useSessionStore } from '@/stores/session'

// 顶栏（§3.2）：常驻 [登录/注册] 或 [头像·昵称·身份徽章]；
// 主线导航固定四条（首页 / 核心对话页 / 智能工作台 / 完整报告页），菜单由 bootstrap 下发。
// bootstrap 还没返回菜单时（后端未启动 / 首次加载中）用同一份清单兜底：顶栏在每个页面都完全一致，
// 不允许退化成「某一页没有导航」或指向原型锚点（#agents / #workbench）的死链。
const session = useSessionStore()
const route = useRoute()
const { appName, identity, menus, isLoggedIn } = storeToRefs(session)

/** 与 data/registry/menus.json 同值（守卫：菜单必须指向真实路由）；不一致时以 bootstrap 下发的为准。 */
const FALLBACK_NAV_ITEMS: MenuView[] = [
  { key: 'home', label: '首页', route: '/', visible: true, sort_order: 1 },
  { key: 'conversation', label: '核心对话页', route: '/conv', visible: true, sort_order: 2 },
  { key: 'workspace', label: '智能工作台', route: '/wb', visible: true, sort_order: 3 },
  { key: 'report', label: '完整报告页', route: '/report', visible: true, sort_order: 4 },
]

const navItems = computed(() => {
  const fromBootstrap = menus.value
    .filter((m) => m.visible !== false)
    .slice()
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
  return fromBootstrap.length ? fromBootstrap : FALLBACK_NAV_ITEMS
})

const nickname = computed(() => identity.value.nickname ?? '')
const role = computed(() => identity.value.role ?? '')
const avatar = computed(() => identity.value.avatar ?? '')
</script>

<template>
  <header class="top-bar">
    <RouterLink class="brand" to="/">
      <span class="brand-mark" aria-hidden="true">职</span>
      <span class="brand-copy"><span class="brand-name">{{ appName || '职引' }}</span></span>
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
      <!-- 站内消息中心已移除：后端尚未定义消息中心接口，此前那套消息与通知偏好
           全部是本地演示数据。等接口落地后再接回来，不用假数据占位。 -->
      <template v-if="isLoggedIn">
        <span v-if="avatar" class="avatar">{{ avatar }}</span>
        <span class="nickname">{{ nickname }}</span>
        <span v-if="role" class="role-badge">{{ role }}</span>
      </template>
      <button v-else class="login-link" type="button" @click="session.openLogin()">登录 / 注册</button>
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: var(--space-8);
  height: 72px;
  width: 100%;
  margin: 0;
  padding: 0 max(var(--page-gutter), calc((100% - 1120px) / 2));
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 800;
  font-size: 22px;
  letter-spacing: 0.02em;
  color: var(--color-text-primary);
  text-decoration: none;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--color-brand);
  color: #fff;
  font-size: var(--font-size-base);
}

.brand-copy { display: flex; align-items: baseline; }

.main-nav {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  flex: 1;
}

.nav-link {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-pill);
  color: var(--color-text-secondary);
  font-size: 15px;
  font-weight: 500;
  text-decoration: none;
}

.nav-link:hover {
  color: var(--color-brand);
}

.nav-link.is-active {
  background: var(--color-brand-soft);
  color: var(--color-brand);
}

.main-nav .nav-link:not(.is-active):hover { background: var(--color-brand-soft); }

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
  background: none;
  color: var(--color-text-secondary);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.login-link:hover {
  border-color: var(--color-brand);
  color: var(--color-brand);
}

@media (max-width: 640px) {
  .top-bar { gap: var(--space-3); }
  .main-nav { display: none; }
}
</style>

<script setup lang="ts">
import { useSessionStore } from '@/stores/session'

// 登录 / 注册（#screen-auth，OTH-002）。
//
// 形态按设计文档 §4.5「Modal 或独立页」：本页作为落地页承载品牌与入口，
// 实际表单由 common/LoginModal 统一渲染（手机号 + 验证码 + 协议勾选）。
// 落地页不自动弹窗——否则会与登录弹窗叠成两层卡片；点卡片里的按钮再拉起弹窗。
const session = useSessionStore()

function open() {
  if (!session.isLoggedIn) session.openLogin()
}
</script>

<template>
  <main data-anchor="screen-auth" class="auth-page">
    <div class="auth-card">
      <div class="auth-mark" aria-hidden="true">引</div>
      <p class="eyebrow">继续职业探索</p>
      <h1>{{ session.isLoggedIn ? '你已登录' : '让每一次探索，都有迹可循' }}</h1>
      <p class="auth-desc">
        {{ session.isLoggedIn ? '从首页选择你现在想解决的事，回到你的职业路径。' : '登录后，把散落的对话沉淀成一份持续更新的画像、报告与行动计划。' }}
      </p>

      <template v-if="session.isLoggedIn">
        <RouterLink class="btn btn-pri" :to="{ name: 'home' }">返回首页</RouterLink>
      </template>
      <template v-else>
        <button class="btn btn-pri" type="button" @click="open">登录 / 注册</button>
        <RouterLink class="back-link" :to="{ name: 'home' }">暂不登录，先逛逛</RouterLink>
      </template>

      <ul class="auth-points">
        <li>游客采集的内容登录后不丢失</li>
        <li>手机号 + 验证码，未注册自动建号</li>
      </ul>
    </div>
  </main>
</template>

<style scoped>
.auth-page {
  min-height: calc(100dvh - 72px);
  display: grid;
  place-items: center;
  padding: var(--space-8) var(--page-gutter);
  background:
    radial-gradient(circle at 16% 18%, rgba(55, 138, 221, 0.08), transparent 32%),
    radial-gradient(circle at 84% 82%, rgba(56, 185, 121, 0.08), transparent 32%),
    var(--paper);
}

.auth-card {
  width: min(460px, 100%);
  padding: var(--space-10) var(--space-8);
  text-align: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

.auth-mark {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  margin: 0 auto var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-action-bg);
  color: var(--color-text-inverse);
  font-size: var(--font-size-xl);
  font-weight: 800;
}

.eyebrow {
  margin: 0 0 var(--space-2);
  font-size: var(--font-size-xs);
  letter-spacing: 0.14em;
  color: var(--color-link);
}

h1 {
  margin: 0 0 var(--space-3);
  font-size: var(--font-size-xl);
  font-weight: 800;
  letter-spacing: -0.01em;
}

.auth-desc {
  margin: 0 0 var(--space-6);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.7;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 180px;
  min-height: 48px;
  padding: var(--space-3) var(--space-6);
  border: 0;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-sm);
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
}

.btn-pri {
  background: var(--color-action-bg);
  color: var(--color-text-inverse);
}

.btn-pri:hover {
  filter: brightness(1.04);
}

.back-link {
  display: inline-block;
  margin-top: var(--space-4);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.back-link:hover {
  color: var(--color-brand);
}

.auth-points {
  display: grid;
  gap: var(--space-2);
  margin: var(--space-8) 0 0;
  padding: var(--space-4) 0 0;
  border-top: 1px dashed var(--color-border);
  list-style: none;
  text-align: left;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.auth-points li {
  position: relative;
  padding-left: 18px;
}

.auth-points li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 6px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-brand);
}
</style>

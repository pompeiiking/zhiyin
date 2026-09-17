<template>
  <aside class="session-list" aria-label="任务会话">
    <header>
      <h2>我的任务</h2>
      <RouterLink :to="{ name: 'home' }" aria-label="新建任务">＋</RouterLink>
    </header>
    <p class="empty">当前暂无会话，从首页选择一件想解决的事。</p>
  </aside>
</template>

<style scoped>
.session-list {
  min-height: 0;
  overflow: auto;
  padding: var(--space-5);
  border-right: 1px solid var(--color-border);
  background: var(--color-bg);
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-5);
}

h2 {
  margin: 0;
  font-size: var(--font-size-lg);
}

header a {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: 50%;
  text-decoration: none;
}

.empty {
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}
</style>

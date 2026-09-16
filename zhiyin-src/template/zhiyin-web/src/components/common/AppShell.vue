<script setup lang="ts">
import TopBar from '@/components/common/TopBar.vue'
import LoginModal from '@/components/common/LoginModal.vue'
</script>

<template>
  <div class="app-shell">
    <TopBar />
    <main class="app-main">
      <slot />
    </main>
    <LoginModal />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-main {
  flex: 1;
}
</style>

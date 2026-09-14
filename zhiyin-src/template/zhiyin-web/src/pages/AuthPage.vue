<script setup lang="ts">
// 登录 / 注册 #screen-auth（P0，Modal 或独立页）
//
// 口径（前端设计文档 §4.5）：
//   - 手机号验证码表单 + 协议勾选
//   - 游客在第 3 问触发拦截（后端返回 code=1005 GUEST_LIMIT）
//   - 登录成功 → auth_login_success；游客合并完成 → auth_guest_merge
// TODO(骨架): 实现表单与登录拦截拉起逻辑
</script>

<template>
  <div data-anchor="screen-auth">
    <!-- TODO(骨架): 手机号验证码表单 / 协议勾选 -->
  </div>
</template>

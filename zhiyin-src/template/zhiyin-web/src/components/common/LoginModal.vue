<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const dialog = ref<HTMLDialogElement>()
const phone = ref('')
const code = ref('')
const agreed = ref(false)
const notice = ref('')
const validPhone = computed(() => /^1[3-9]\d{9}$/.test(phone.value.trim()))
const ready = computed(() => validPhone.value && /^\d{6}$/.test(code.value.trim()) && agreed.value)
let returnFocus: HTMLElement | null = null
let previousOverflow = ''
function close() { session.closeLogin() }
watch(() => session.loginOpen, async open => {
  await nextTick()
  if (open && !dialog.value?.open) {
    returnFocus = document.activeElement as HTMLElement
    previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    notice.value = ''
    dialog.value?.showModal()
  } else if (!open && dialog.value?.open) {
    dialog.value.close()
    document.body.style.overflow = previousOverflow
    returnFocus?.focus()
    phone.value = ''; code.value = ''; agreed.value = false
  }
}, { immediate: true })
onBeforeUnmount(() => { if (dialog.value?.open) document.body.style.overflow = previousOverflow })
function requestCode() { notice.value = '短信服务尚未接入，未发送验证码。请勿输入真实手机号。' }
function submit() { if (ready.value) notice.value = '登录服务尚未接入，未提交手机号或验证码。' }
async function refreshIdentity() {
  await session.loadBootstrap()
  if (!session.isLoggedIn) notice.value = session.error || '尚未检测到已登录身份，请等待登录服务接入。'
}
</script>

<template>
  <dialog ref="dialog" class="login-modal" data-anchor="screen-auth" aria-labelledby="login-title" aria-describedby="login-reason" @cancel.prevent="close" @click="event => { if (event.target === dialog) close() }">
    <div class="modal-body">
      <button class="close" type="button" aria-label="关闭登录弹窗" @click="close">×</button>
      <div class="modal-mark" aria-hidden="true">引</div>
      <p class="eyebrow">继续职业探索</p>
      <h2 id="login-title">让每一次探索，都有迹可循</h2>
      <p id="login-reason" class="description">{{ session.loginReason }}</p>
      <div class="service-note">当前为第一期界面预览，短信与登录服务尚未接入。请勿输入真实手机号。</div>
      <form @submit.prevent="submit">
        <label for="login-phone">手机号</label>
        <input id="login-phone" v-model="phone" type="tel" inputmode="numeric" autocomplete="off" maxlength="11" pattern="1[3-9][0-9]{9}" placeholder="输入 11 位测试手机号" required />
        <label for="login-code">验证码</label>
        <div class="code-row"><input id="login-code" v-model="code" inputmode="numeric" autocomplete="off" maxlength="6" pattern="[0-9]{6}" placeholder="输入 6 位验证码" required /><button type="button" :disabled="!validPhone" @click="requestCode">获取验证码</button></div>
        <div class="agreement"><input id="login-agreed" v-model="agreed" type="checkbox" /><label for="login-agreed">我已阅读并同意</label><button type="button" @click="notice = '用户协议正文尚未提供，当前无法完成正式注册。'">用户协议</button><span>与</span><button type="button" @click="notice = '隐私政策正文尚未提供，当前不会提交表单数据。'">隐私政策</button></div>
        <button class="submit" type="submit" :disabled="!ready">登录 / 注册</button>
        <p class="hint">未注册手机号将在正式服务接入后自动注册</p>
      </form>
      <p v-if="notice" class="notice" role="status">{{ notice }}</p>
      <button class="refresh" :disabled="session.loading" @click="refreshIdentity">{{ session.loading ? '正在检查…' : '已在其他入口登录？刷新身份' }}</button>
    </div>
  </dialog>
</template>

<style scoped>
.login-modal { width: min(460px, calc(100% - 32px)); max-height: calc(100dvh - 32px); padding: 0; border: 1px solid var(--color-border); border-radius: var(--radius-lg); background: var(--color-surface); color: var(--color-text-primary); box-shadow: var(--shadow-overlay); }
.login-modal::backdrop { background: var(--inkCard); opacity: 0.45; }
.modal-body { position: relative; padding: var(--space-8); }
.close { position: absolute; top: var(--space-2); right: var(--space-2); width: 44px; height: 44px; background: none; border: 0; font-size: var(--font-size-xl); }
.modal-mark { display: grid; place-items: center; width: 44px; height: 44px; background: var(--color-action-bg); color: var(--color-text-inverse); border-radius: var(--radius-md); font-size: var(--font-size-xl); }
.eyebrow { font-size: var(--font-size-xs); color: var(--color-link); letter-spacing: 0.12em; margin-top: var(--space-6); }
h2 { font-size: var(--font-size-xl); line-height: 1.5; margin-bottom: var(--space-2); }
.description, .hint { color: var(--color-text-secondary); }
.service-note { background: var(--color-warning-soft); border-radius: var(--radius-sm); padding: var(--space-3); font-size: var(--font-size-xs); margin-block: var(--space-5); }
form > label { display: block; margin-block: var(--space-4) var(--space-2); }
input:not([type='checkbox']) { width: 100%; min-width: 0; height: 48px; padding-inline: var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: var(--color-surface); }
.code-row { display: flex; gap: var(--space-2); }
.code-row button { flex-shrink: 0; padding-inline: var(--space-3); color: var(--color-link); background: var(--color-brand-soft); border: 1px solid var(--color-brand-border); border-radius: var(--radius-sm); }
.agreement { margin-block: var(--space-5); display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-1); font-size: var(--font-size-xs); }
.agreement input { width: 18px; height: 18px; }
.agreement button, .refresh { padding: var(--space-1); border: 0; background: none; color: var(--color-link); text-decoration: underline; }
.submit { width: 100%; min-height: 48px; border: 0; border-radius: var(--radius-pill); color: var(--color-text-inverse); background: var(--color-action-bg); }
button:disabled { opacity: 0.5; }
.hint { font-size: var(--font-size-xs); text-align: center; }
.notice { padding: var(--space-3); background: var(--color-brand-soft); border-radius: var(--radius-sm); }
.refresh { width: 100%; min-height: 44px; font-size: var(--font-size-xs); }
@media (max-width: 560px) { .login-modal { margin-bottom: 0; width: 100%; max-width: 100%; max-height: 90dvh; border-bottom-left-radius: 0; border-bottom-right-radius: 0; } .modal-body { padding: var(--space-6); } }
</style>

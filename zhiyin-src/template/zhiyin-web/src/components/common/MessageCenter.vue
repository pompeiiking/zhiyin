<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { trackEvent } from '@/api/endpoints'
import MockBadge from '@/components/common/MockBadge.vue'

// 站内消息中心（PSH-001 / PSH-006，静态演示版）。
//
// 顶栏铃铛入口 + 未读角标；抽屉内按类型分组（教练提醒 / 节点提醒 / 导师建议 / 系统通知），
// 支持单条已读、全部已读、点击跳转，并内置通知偏好设置。
// 后端「消息中心接口」尚未定义（设计文档 §七 · 第四波），此处用演示数据承载结构，
// 接入后把 messages / prefs 换成真实接口即可，交互口径不变。
type MsgType = 'coach' | 'milestone' | 'mentor' | 'system'

interface DemoMessage {
  id: string
  type: MsgType
  title: string
  body: string
  action: string
  time: string
  read: boolean
}

const TYPE_META: Record<MsgType, { label: string; className: string }> = {
  coach: { label: '教练提醒', className: 't-coach' },
  milestone: { label: '节点提醒', className: 't-milestone' },
  mentor: { label: '导师建议', className: 't-mentor' },
  system: { label: '系统通知', className: 't-system' },
}

const open = ref(false)
const showPrefs = ref(false)
const notice = ref('')

// 文案遵循 PSH-007：触发原因 + 一个最小行动 + 预期耗时，不施压、不夸大。
const messages = ref<DemoMessage[]>([
  { id: 'm1', type: 'coach', title: '你已经 3 天没更新行动计划了', body: '停滞信号触发。回到「行动」环节，勾掉一件今天能完成的小事。', action: '回到行动环节', time: '10:24', read: false },
  { id: 'm2', type: 'milestone', title: '秋招网申窗口临近', body: '目标公司网申多集中在 9 月，建议本周完成岗位清单。', action: '查看关键节点', time: '昨天', read: false },
  { id: 'm3', type: 'mentor', title: '导师给你留了一条建议', body: '针对「结构设计 vs 施工管理」的取舍，导师补充了行业观察。', action: '查看导师建议', time: '昨天', read: true },
  { id: 'm4', type: 'system', title: '画像缺口已更新', body: '补齐「职业兴趣」后，诊断置信度由 0.78 提升到 0.82。', action: '查看画像', time: '3 天前', read: true },
])

const unread = computed(() => messages.value.filter((m) => !m.read).length)
const grouped = computed(() => {
  const order: MsgType[] = ['coach', 'milestone', 'mentor', 'system']
  return order
    .map((type) => ({ type, meta: TYPE_META[type], items: messages.value.filter((m) => m.type === type) }))
    .filter((g) => g.items.length)
})

// 通知偏好（PSH-006）：逐类开关，免打扰时段为演示值，接真实接口后保留结构。
const prefs = ref([
  { key: 'milestone', label: '节点提醒', desc: '网申 / 报名 / 考试等关键截止日', enabled: true },
  { key: 'coach', label: '教练建议', desc: '停滞预警与复盘邀请', enabled: true },
  { key: 'mentor', label: '导师建议', desc: '导师查看后写入的建议', enabled: true },
  { key: 'promo', label: '推广', desc: '成长成果与活动通知', enabled: false },
])

function toggle() {
  open.value = !open.value
  if (open.value) {
    showPrefs.value = false
    void trackEvent('psh_center_open', { unread: unread.value }).catch(() => {})
  }
}

function markRead(id: string) {
  const message = messages.value.find((m) => m.id === id)
  if (!message) return
  message.read = true
  notice.value = `已跳转：${message.action}（演示，正式实现会切到对应环节）。`
  void trackEvent('psh_message_open', { type: message.type }).catch(() => {})
}

function markAllRead() {
  messages.value.forEach((m) => (m.read = true))
  void trackEvent('psh_mark_all_read', {}).catch(() => {})
}

function onEscape(event: KeyboardEvent) {
  if (event.key === 'Escape' && open.value) open.value = false
}

const rootRef = ref<HTMLElement | null>(null)

// 点击面板以外的任意位置即关闭，不必再点铃铛。
function onClickOutside(event: MouseEvent) {
  if (!open.value) return
  const target = event.target as Node | null
  if (target && rootRef.value && !rootRef.value.contains(target)) {
    open.value = false
  }
}

onMounted(() => {
  window.addEventListener('keydown', onEscape)
  document.addEventListener('click', onClickOutside)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onEscape)
  document.removeEventListener('click', onClickOutside)
})
</script>

<template>
  <div ref="rootRef" class="message-center">
    <button type="button" class="bell" :aria-expanded="open" aria-label="消息中心" @click="toggle">
      <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
        <path d="M12 3a6 6 0 0 0-6 6v3.2l-1.6 2.6A1 1 0 0 0 5.2 16h13.6a1 1 0 0 0 .8-1.2L18 12.2V9a6 6 0 0 0-6-6Z" fill="none" stroke="currentColor" stroke-width="1.6" />
        <path d="M9.6 19a2.5 2.5 0 0 0 4.8 0" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
      </svg>
      <span v-if="unread" class="unread">{{ unread }}</span>
    </button>

    <div v-if="open" class="mc-panel" role="dialog" aria-label="消息中心">
        <header class="mc-head">
          <div class="mc-title">
            <strong>消息中心</strong>
            <small>{{ unread ? `${unread} 条未读` : '已全部读完' }}</small>
          </div>
          <div class="mc-head-actions">
            <button type="button" class="text-btn" :disabled="!unread" @click="markAllRead">全部已读</button>
            <button type="button" class="text-btn" :class="{ on: showPrefs }" @click="showPrefs = !showPrefs">{{ showPrefs ? '返回消息' : '偏好设置' }}</button>
          </div>
        </header>

        <div v-if="notice" class="mc-notice" role="status">{{ notice }}</div>

        <!-- 偏好设置（PSH-006） -->
        <div v-if="showPrefs" class="mc-prefs">
          <div class="pref-item" v-for="pref in prefs" :key="pref.key">
            <div class="pref-copy">
              <strong>{{ pref.label }}</strong>
              <span>{{ pref.desc }}</span>
            </div>
            <button type="button" class="switch" :class="{ on: pref.enabled }" role="switch" :aria-checked="pref.enabled" @click="pref.enabled = !pref.enabled">
              <i aria-hidden="true"></i>
            </button>
          </div>
          <div class="pref-dnd">
            <span>免打扰时段</span>
            <b>22:00 – 08:00</b>
            <em>演示值 · 接真实接口后可调</em>
          </div>
          <MockBadge source="demo" />
        </div>

        <!-- 消息列表（PSH-001） -->
        <div v-else class="mc-body">
          <section v-for="group in grouped" :key="group.type" class="mc-group">
            <h3 class="group-title" :class="group.meta.className">{{ group.meta.label }}</h3>
            <button v-for="message in group.items" :key="message.id" type="button" class="msg-item" :class="{ unread: !message.read }" @click="markRead(message.id)">
              <span class="msg-dot" aria-hidden="true"></span>
              <span class="msg-main">
                <span class="msg-title">{{ message.title }}</span>
                <span class="msg-body">{{ message.body }}</span>
                <span class="msg-action">{{ message.action }} · 约 1 分钟</span>
              </span>
              <span class="msg-time">{{ message.time }}</span>
            </button>
          </section>
          <p v-if="!messages.length" class="mc-empty">暂无消息。教练提醒、节点提醒与导师建议会汇总到这里。</p>
        </div>
      </div>
  </div>
</template>

<style scoped>
.message-center {
  position: relative;
}

.bell {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.bell:hover {
  border-color: var(--color-brand);
  color: var(--color-brand);
}

.unread {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: var(--radius-pill);
  background: var(--color-danger);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 18px;
  text-align: center;
}

.mc-panel {
  position: absolute;
  top: 46px;
  right: 0;
  width: min(380px, calc(100vw - 32px));
  max-height: min(560px, calc(100dvh - 72px));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-overlay);
  z-index: 50;
}

.mc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.mc-title strong,
.mc-title small {
  display: block;
}

.mc-title strong {
  font-size: var(--font-size-md);
  font-weight: 800;
}

.mc-title small {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.mc-head-actions {
  display: flex;
  gap: var(--space-2);
}

.text-btn {
  padding: 4px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: 600;
  cursor: pointer;
}

.text-btn:hover,
.text-btn.on {
  border-color: var(--color-brand);
  color: var(--color-brand);
}

.text-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.mc-notice {
  padding: var(--space-2) var(--space-4);
  background: var(--color-brand-soft);
  color: var(--color-text-primary);
  font-size: var(--font-size-xs);
}

.mc-body {
  overflow: auto;
  padding: var(--space-2);
}

.mc-group + .mc-group {
  margin-top: var(--space-3);
}

.group-title {
  margin: 0 0 var(--space-1);
  padding: var(--space-2) var(--space-2) 0;
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.t-coach { color: var(--color-role); }
.t-milestone { color: var(--color-warning); }
.t-mentor { color: var(--color-brand-strong); }
.t-system { color: var(--color-text-muted); }

.msg-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-3) var(--space-2);
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.msg-item:hover {
  background: var(--color-bg);
}

.msg-item.unread .msg-title {
  font-weight: 700;
}

.msg-dot {
  flex: none;
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
  background: transparent;
}

.msg-item.unread .msg-dot {
  background: var(--color-danger);
}

.msg-main {
  flex: 1 1 auto;
  min-width: 0;
}

.msg-title {
  display: block;
  margin-bottom: 2px;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  line-height: 1.4;
}

.msg-body {
  display: block;
  margin-bottom: 2px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.msg-action {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-link);
}

.msg-time {
  flex: none;
  margin-left: auto;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.mc-empty {
  padding: var(--space-6);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  text-align: center;
}

.mc-prefs {
  overflow: auto;
  padding: var(--space-3);
}

.pref-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.pref-copy strong,
.pref-copy span {
  display: block;
}

.pref-copy strong {
  font-size: var(--font-size-sm);
}

.pref-copy span {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.switch {
  flex: none;
  position: relative;
  width: 40px;
  height: 22px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-bg);
  cursor: pointer;
}

.switch i {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--color-text-muted);
  transition: transform var(--duration-fast) var(--ease-standard), background var(--duration-fast) var(--ease-standard);
}

.switch.on {
  background: var(--color-brand);
  border-color: var(--color-brand);
}

.switch.on i {
  transform: translateX(18px);
  background: #fff;
}

.pref-dnd {
  display: grid;
  gap: 2px;
  margin: var(--space-4) 0;
  padding: var(--space-3);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  font-size: var(--font-size-xs);
}

.pref-dnd span {
  color: var(--color-text-secondary);
}

.pref-dnd b {
  font-size: var(--font-size-sm);
}

.pref-dnd em {
  font-style: normal;
  color: var(--color-text-muted);
}

@media (max-width: 640px) {
  .mc-panel {
    position: fixed;
    top: 72px;
    left: var(--space-3);
    right: var(--space-3);
    width: auto;
  }
}
</style>

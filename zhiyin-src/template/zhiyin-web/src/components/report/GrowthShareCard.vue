<script setup lang="ts">
import { computed, ref } from 'vue'
import { trackEvent } from '@/api/endpoints'
import MockBadge from '@/components/common/MockBadge.vue'

// 成长成果卡 + 分享（GRW-001 / GRW-002 / GRW-004 / GRW-007，静态演示版）。
//
// 完成一次诊断后，用户可在 2 次点击内生成一张**默认脱敏**的可分享卡片。
// 分享渠道与邀请机制均为界面预览，接真实分享/来源追踪能力后替换交互口径即可。
const expanded = ref(false)
const templateIndex = ref(0)
const anonymous = ref(true)
const copied = ref('')

const templates = [
  { id: 'soft', name: '简约', tone: 'soft' },
  { id: 'blue', name: '蓝色', tone: 'blue' },
  { id: 'dark', name: '深色', tone: 'dark' },
]

const channels = [
  { key: 'wechat', label: '微信' },
  { key: 'qq', label: 'QQ' },
  { key: 'link', label: '复制链接' },
  { key: 'image', label: '保存图片' },
]

// 脱敏口径（GRW-007）：不含真实姓名 / 学校 / 成绩 / 企业，只保留方向与匹配度。
const cardTitle = computed(() => (anonymous.value ? '我完成了一次职业诊断' : '我的职业诊断成果'))
const cardConclusion = computed(() => (anonymous.value ? '主攻方向：建筑类 · 结构设计（匹配度 82%）' : '主攻方向：土木工程 · 结构设计（匹配度 82%）'))

function toggle() {
  expanded.value = !expanded.value
  if (expanded.value) void trackEvent('grw_share_entry', {}).catch(() => {})
}

function pickTemplate(index: number) {
  templateIndex.value = index
  void trackEvent('grw_template_switch', { template: templates[index].id }).catch(() => {})
}

function share(key: string) {
  const label = channels.find((c) => c.key === key)?.label ?? key
  if (key === 'link') {
    copied.value = '已复制分享链接（演示）：https://zhiyin.demo/s/成长成果-脱敏'
  } else {
    copied.value = `${label}分享尚未接入服务，当前为界面预览。`
  }
  void trackEvent('grw_share_channel', { channel: key }).catch(() => {})
}

function copyInvite() {
  copied.value = '已复制邀请码：ZHIYIN-GROW-2026（演示，策略待定）'
  void trackEvent('grw_invite_copy', {}).catch(() => {})
}
</script>

<template>
  <section class="growth-share-card" aria-label="成长成果卡">
    <header class="gsc-head">
      <div>
        <small>推广 · 成长成果</small>
        <h3>分享我的成长成果</h3>
      </div>
      <MockBadge source="demo" />
    </header>

    <button type="button" class="gsc-toggle" :aria-expanded="expanded" @click="toggle">
      {{ expanded ? '收起成果卡' : '生成一张可分享卡片' }}
    </button>

    <div v-if="expanded" class="gsc-body">
      <!-- 成果卡预览（默认脱敏） -->
      <div class="result-card" :class="templates[templateIndex].tone">
        <div class="rc-brand"><span class="rc-dot" aria-hidden="true"></span>职引 ZHIYIN</div>
        <p class="rc-title">{{ cardTitle }}</p>
        <p class="rc-conclusion">{{ cardConclusion }}</p>
        <div class="rc-meta">
          <span>生成于今天 11:02</span>
          <span>{{ anonymous ? '已脱敏' : '含部分个人信息' }}</span>
        </div>
      </div>

      <!-- 模板切换 + 可见范围 -->
      <div class="gsc-controls">
        <div class="gsc-templates">
          <button v-for="(t, i) in templates" :key="t.id" type="button" class="tpl-btn" :class="{ on: i === templateIndex }" @click="pickTemplate(i)">{{ t.name }}</button>
        </div>
        <label class="gsc-scope">
          <input v-model="anonymous" type="checkbox" />
          <span>默认脱敏（不展示姓名 / 学校 / 成绩 / 企业）</span>
        </label>
      </div>

      <!-- 分享渠道（GRW-002） -->
      <div class="gsc-channels">
        <button v-for="channel in channels" :key="channel.key" type="button" class="channel-btn" @click="share(channel.key)">{{ channel.label }}</button>
      </div>

      <!-- 邀请机制（GRW-004，策略待定） -->
      <div class="gsc-invite">
        <span>邀请好友 · 邀请码</span>
        <b>ZHIYIN-GROW-2026</b>
        <button type="button" class="text-btn" @click="copyInvite">复制</button>
      </div>

      <p v-if="copied" class="gsc-notice" role="status">{{ copied }}</p>
    </div>
  </section>
</template>

<style scoped>
.growth-share-card {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.gsc-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.gsc-head small {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.gsc-head h3 {
  margin: 2px 0 0;
  font-size: var(--font-size-md);
  font-weight: 800;
}

.gsc-toggle {
  margin-top: var(--space-4);
  padding: 10px 20px;
  border: 1px solid var(--color-brand-border);
  border-radius: var(--radius-pill);
  background: var(--color-brand-soft);
  color: var(--color-brand-strong);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
}

.gsc-body {
  display: grid;
  gap: var(--space-4);
  margin-top: var(--space-4);
}

.result-card {
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  color: var(--color-text-primary);
}

.result-card.soft {
  background: linear-gradient(160deg, #fff, var(--color-brand-soft));
  border: 1px solid var(--color-brand-border);
}

.result-card.blue {
  background: linear-gradient(160deg, var(--color-brand), var(--color-brand-strong));
  color: #fff;
  border: 0;
}

.result-card.dark {
  background: linear-gradient(160deg, var(--inkCard), #14110f);
  color: #fff;
  border: 0;
}

.rc-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 800;
  font-size: var(--font-size-sm);
  letter-spacing: 0.02em;
}

.rc-dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  background: var(--color-brand);
  box-shadow: 0 0 0 3px var(--color-brand-soft);
}

.result-card.blue .rc-dot,
.result-card.dark .rc-dot {
  background: #fff;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.3);
}

.rc-title {
  margin: var(--space-5) 0 var(--space-2);
  font-size: var(--font-size-xl);
  font-weight: 800;
}

.rc-conclusion {
  margin: 0;
  font-size: var(--font-size-base);
  opacity: 0.92;
}

.rc-meta {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-5);
  font-size: var(--font-size-xs);
  opacity: 0.75;
}

.gsc-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.gsc-templates {
  display: flex;
  gap: var(--space-2);
}

.tpl-btn {
  padding: 5px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: 600;
  cursor: pointer;
}

.tpl-btn.on {
  border-color: var(--color-brand);
  background: var(--color-brand-soft);
  color: var(--color-brand-strong);
}

.gsc-scope {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.gsc-scope input {
  width: 16px;
  height: 16px;
}

.gsc-channels {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.channel-btn {
  flex: 1;
  min-width: 88px;
  padding: 9px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-primary);
  font-size: var(--font-size-xs);
  font-weight: 600;
  cursor: pointer;
}

.channel-btn:hover {
  border-color: var(--color-brand);
  color: var(--color-brand-strong);
}

.gsc-invite {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  font-size: var(--font-size-xs);
}

.gsc-invite span {
  color: var(--color-text-secondary);
}

.gsc-invite b {
  font-size: var(--font-size-sm);
  letter-spacing: 0.04em;
}

.text-btn {
  margin-left: auto;
  padding: 4px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--color-link);
  font-size: var(--font-size-xs);
  cursor: pointer;
}

.gsc-notice {
  margin: 0;
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-warning-soft);
  color: var(--color-text-primary);
  font-size: var(--font-size-xs);
}
</style>

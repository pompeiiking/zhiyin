<script setup lang="ts">
import TheoryTag from './TheoryTag.vue'

// 角色取值与冻结契约 `ConversationMessageView.role` 严格一致：agent / user / system。
// 前端曾自造 `coach` 角色，但只被两条错误提示用到，气泡还顶着"教练 · 主动提醒"的名头，
// 与"系统提示"的事实不符；错误提示已改回 system，这里同步收敛取值。
//
// 同时删掉两处从未生效的死控件：
//   - `long` 从未被任何调用方或后端下发 → "查看完整报告 →"永远不渲染（报告入口在
//     `AnalysisHandoff`，已实测可用）；
//   - `action` 从未下发 → 教练两颗按钮恒显示硬编码"立即行动/稍后"且没有任何点击行为。
// 拿不到真实数据就不放会误导用户的控件，与报告页"拿不到就显示空态"同一口径。
//
// 回落的说话人必须是中性称呼：此前写死"职业顾问"，于是任何非职业顾问说的气泡
// （例如交接前由建档分析师发出的回复）在后端没给名字时都会顶着"职业顾问"的名头。
// 名字缺失时只说明"这是智能体发的"，不假扮某位具体主理。
defineProps<{ role: 'agent' | 'user' | 'system'; content: string; author?: string; theory?: Record<string, unknown> }>()

const NEUTRAL_AUTHOR = '智能体'
</script>

<template>
  <article class="msg" :class="role">
    <span v-if="role !== 'user' && role !== 'system'" class="avatar" aria-hidden="true">{{ (author || NEUTRAL_AUTHOR).slice(0, 1) }}</span>
    <div class="bubble">
      <small v-if="role !== 'user'">{{ author || (role === 'system' ? '系统提示' : NEUTRAL_AUTHOR) }}</small>
      <p>{{ content }}</p>
      <TheoryTag v-if="theory && role === 'agent'" :theory="theory" />
    </div>
  </article>
</template>

<style scoped>
.msg { display: flex; gap: 9px; align-items: flex-end; }
.msg.user { justify-content: flex-end; }
.msg.system { justify-content: center; }

.avatar {
  flex: none;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  margin-bottom: 1px;
  background: linear-gradient(155deg, var(--blue), var(--greenD));
  color: #fff;
  box-shadow: 0 3px 8px rgba(55, 138, 221, 0.32);
}

.bubble {
  max-width: 78%;
  border-radius: 16px;
  padding: 12px 16px;
  font-size: 15px;
  line-height: 1.6;
  box-shadow: 0 1px 2px rgba(28, 24, 22, 0.03);
}

.msg.agent .bubble { background: #fff; border: 1px solid var(--line); border-top-left-radius: 5px; color: var(--ink); }
.msg.user .bubble { background: var(--blue); color: #fff; border-top-right-radius: 5px; box-shadow: 0 4px 12px rgba(55, 138, 221, 0.22); }
.msg.system .bubble { max-width: 100%; border: 0; background: transparent; color: var(--muted); text-align: center; box-shadow: none; }

small { display: block; margin-bottom: 2px; color: var(--gray); font-size: 12px; }
.msg.user small { color: inherit; opacity: 0.85; }
p { margin: 0; }
</style>

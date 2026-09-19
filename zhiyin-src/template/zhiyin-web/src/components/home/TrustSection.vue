<script setup lang="ts">
import { computed } from 'vue'

import { useSessionStore } from '@/stores/session'

// 首页信任区（《前端页面设计》§4.1「主区 → 任务卡组 → 信任区 → 页脚」）。
//
// ⚠️ 这一区此前**根本没有**：bootstrap 下发的 `trust_blocks`（1 条主线）、
//    `banners`（1 条已上线）、`faqs`（4 条）在前端零消费，`stores/session.ts`
//    把它们读进来后就再没有任何组件引用——`README.md` §二 却已经写着首页
//    数据来源包含「信任块 / 横幅 / FAQ」。这正是「接口有数据、页面没有」的
//    典型缺口：三个区块动态资源改 JSON 就能上线，但用户从来没见过。
//
// 现在：三块内容**全部来自 bootstrap**（信任块 / 横幅 / FAQ 属动态资源，
// 《AGENTS.md》§8），前端不写死任何标题、正文或问答；下发的条目为空时整块不渲染，
// 也不放占位——与工作台/报告「拿不到就显示空态」同一口径。
const session = useSessionStore()

const hasContent = computed(
  () => session.trustBlocks.length > 0 || session.banners.length > 0 || session.faqs.length > 0,
)
</script>

<template>
  <section v-if="hasContent" id="trust" class="trust">
    <div class="container">
      <!-- 横幅 / 运营位：上下线与排序由动态资源控制，前端只负责渲染已启用项 -->
      <div v-for="banner in session.banners" :key="banner.code" class="banner" role="status">
        <b class="banner-title">{{ banner.title }}</b>
        <span v-if="banner.body" class="banner-body">{{ banner.body }}</span>
        <RouterLink
          v-if="banner.action_label && banner.action_route"
          class="banner-action"
          :to="banner.action_route"
        >
          {{ banner.action_label }}
        </RouterLink>
      </div>

      <!-- 信任背书：第一条为讲主线的那一句，其余为可展开示例（当前只有主线一条） -->
      <ul v-if="session.trustBlocks.length" class="trust-list">
        <li v-for="block in session.trustBlocks" :key="block.code" class="trust-item">
          <b class="trust-title">{{ block.title }}</b>
          <span v-if="block.body" class="trust-body">{{ block.body }}</span>
        </li>
      </ul>

      <!-- 常见问题：问答原文来自动态资源；用原生 details 展开，不额外造文案 -->
      <div v-if="session.faqs.length" class="faq">
        <details v-for="faq in session.faqs" :key="faq.code" class="faq-item">
          <summary>{{ faq.question }}</summary>
          <p>{{ faq.answer }}</p>
        </details>
      </div>
    </div>
  </section>
</template>

<style scoped>
.trust {
  padding: 56px 0;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
}

.container { max-width: var(--content-max-width); margin: 0 auto; padding: 0 var(--page-gutter); }

.banner {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px;
  padding: 14px 18px;
  margin-bottom: var(--space-4);
  border: 1px solid var(--blueLine);
  border-radius: var(--radius-md);
  background: var(--blueSoft);
}

.banner-title { font-size: var(--font-size-sm); font-weight: 800; color: var(--color-text-primary); }
.banner-body { flex: 1; min-width: 220px; font-size: var(--font-size-sm); color: var(--color-text-secondary); line-height: 1.6; }
.banner-action { color: var(--blueD); font-size: var(--font-size-sm); font-weight: 700; }

.trust-list {
  display: grid;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.trust-item {
  display: grid;
  gap: 6px;
  padding: 18px;
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--blue);
  border-radius: var(--radius-lg);
  background: var(--color-bg);
}

.trust-title { font-size: var(--font-size-base); font-weight: 800; color: var(--color-text-primary); }
.trust-body { color: var(--color-text-secondary); font-size: var(--font-size-sm); line-height: 1.7; }

.faq { margin-top: var(--space-4); }

.faq-item {
  padding: 14px 18px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.faq-item + .faq-item { margin-top: 10px; }

.faq-item summary {
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text-primary);
}

.faq-item p {
  margin: 10px 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.7;
}

@media (max-width: 640px) {
  .trust { padding: 40px 0; }
}
</style>

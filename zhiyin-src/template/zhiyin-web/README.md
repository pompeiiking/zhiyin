# 职引 · 前端（Vue 3 + Vite + TypeScript）

第一期前端是**骨架**：文件、路由、状态、接口清单、组件落脚点已就位，模板与逻辑待实现。
本文只回答一件事：**一个页面要改哪几个文件**——避免多人并行时互相新建同名组件。

对齐文档：《职引-前端页面设计-v1.0》（页面与交互口径）、
《第一期技术架构文档》（接口与依赖方向）。

## 一、目录职责

| 目录 | 职责 | 不允许 |
| --- | --- | --- |
| `src/pages/` | 页面级编排（按页面锚点一一对应） | 直接写业务判断、直接 fetch |
| `src/components/<域>/` | 页面内组件，按页面对齐（common / home / conversation / agents / workspace / report） | 跨页面复用前先确认它真的通用 |
| `src/stores/` | Pinia 状态（session / conversation / workspace / agents） | 在这里发请求之外做业务规则 |
| `src/api/` | `client.ts`（唯一处理统一信封与错误码）· `endpoints.ts`（接口清单，全站唯一）· `schema.ts`（生成类型的取值别名，**唯一取用处**）· `types.ts`（`npm run gen:api` 的**生成物**） | 在组件里直接 axios；手改 `types.ts` |
| `src/router/` | 路由与页面锚点（`PAGE_ANCHORS` 是全站唯一口径） | 别处再拼路径字符串 |
| `src/styles/` | `tokens.css`（设计令牌）+ `main.css` | 在组件里写死颜色值 |
| `src/composables/` | 组合式函数（游客拦截 `useGuestGuard`、画像覆盖口径 `useProfileCoverage` 等） | 放业务规则；在这里发请求而不经 `api/` |

## 二、页面 → 组件 → 接口（并行开发落位表）

| 页面 | 锚点 | 页面文件 | 主要组件 | 数据来源 |
| --- | --- | --- | --- | --- |
| 首页 | `#screen-home` | `pages/HomePage.vue` | `home/TaskCardGroup`、`home/TrustSection`、`home/ShowcaseStage`、`home/AgentsShowcase`、`common/TopBar` | `bootstrap`（任务入口 / 信任块 / 文案包 / 横幅 / FAQ） |
| 登录 / 注册 | `#screen-auth` | `pages/AuthPage.vue` | `common/LoginModal` | `bootstrap`（身份区）+ 登录接口（第一期默认演示用户） |
| 核心对话页 | `#screen-conv` | `pages/ConversationPage.vue` | `conversation/{SessionList,ChatStream,PipelinePanel,AnalysisHandoff,ProfileFields}`、`MessageBubble`、`DisclosureRow`、`AgentBadge`、`TheoryTag`、`PipelineCard`、`BehaviorGuide`、`QuickActions` | `sessions` / `task/enter` / `conversation/message` |
| 智能体小队 | `#screen-agents` | `pages/AgentsPage.vue` | `agents/AgentTeamGrid` | `workspace` 聚合（画像覆盖 / 置信度）+ 能力池（`stores/agents.ts`） |
| 单智能体页 | `#screen-subagent` | `pages/AgentDetailPage.vue` | `agents/{AgentScopePanel,AgentContextRail}` | 能力池（`stores/agents.ts`）+ 真实资产状态；**不做对话**（对话回 `/app/conversation/message`） |
| 智能工作台 | `#screen-wb` | `pages/WorkspacePage.vue` | `workspace/CoachMessageStream` | `workspace` 聚合接口 |
| 完整报告页 | `#screen-report` | `pages/ReportPage.vue` | `report/{ReportToc,ReportSection}` | `report/full-text`（导出走 `assets/export`） |
| 全局 | — | `App.vue` / `components/common/AppShell.vue` | `TopBar` | `bootstrap`（身份 / 菜单 / 路由 / 功能开关） |

> `MockBadge`、`MessageCenter`、`GrowthShareCard` 已删除：前两者随"不允许保留 Mock"一并移除
> （Mock 产出已归零，站内消息中心后端至今没有接口），后者依赖不存在的分享/邀请码后端能力。

## 三、四条全局约束（前端必须成立）

1. **长内容不进对话流**：中栏只说最短结论，报告 / 方案 / 计划全文进右栏管线卡与工作台资产。
2. **换主理必须显式告知**：`ConversationTurnView.disclosure` 非空时，中栏顶部必须出现告知行。
   为 `null` 时**不渲染**——它是"本次没有换主理"，不是"文案待补"。
3. **每轮以行为引导收尾**：`BehaviorGuide` 必须渲染出可点元素，禁止无下一步的总结。
4. **智能体只换主理、不换结论**：`#screen-agents` / `#screen-subagent` 是能力池的可见化与召唤入口（功能块，不进顶层导航）；**单智能体页不做实时对话**，实时交互只在核心对话页发生（§2.1）；回答仍写回同一份画像与资产，不产生平行报告。

## 四、接口与后端对齐

```bash
npm ci               # 按 package-lock.json 安装（首次或新增依赖时用 npm install）
npm run dev          # http://localhost:5173，/api 已代理到 http://localhost:8000
npm run typecheck    # vue-tsc
npm run gen:api      # 从 ../contracts/openapi.json 生成 src/api/types.ts（不需要后端在跑）
npm run check:api    # 重新生成后若无 diff，说明前端类型没有漂移（CI 用）
                     # 注意：它比对的是 git diff，本地有未提交改动时会"必然红"，
                     # 因此本地自检请在提交后跑，或直接看 git status 里 types.ts 是否变化
```

**类型怎么来的（三段链路，任一段漂移都会在 CI 失败）**：

```text
后端 Controller / DTO ──(python scripts/export_openapi.py)──▶ contracts/openapi.json
                                                                    │
                                                          (npm run gen:api)
                                                                    ▼
                                                      src/api/types.ts（生成物）

tests/test_api_contract.py  守「代码 == 快照」
CI 的 npm run check:api     守「快照 == 前端类型」
tests/test_frontend_alignment.py 守「错误码 / 路由锚点 / url 清单 / 落位表」
```

因此**后端改了字段而前端没跟上**会在 CI 红，而不是在联调时才发现；
前端同学也不需要为了拿类型先在本机起后端。

- **baseURL 只配 `/api/v1`**（`VITE_API_BASE_URL`），请求写业务段
  （`url: '/app/bootstrap'`）。任何地方再拼一次 `/v1` 都会 404，
  而 OpenAPI 里看起来"有这条路由"（守卫：后端 `tests/test_api_prefix.py`）。
- 统一信封只在 `api/client.ts` 拆一次：成功返回 `data`，失败抛 `ApiError`。
  UI 只按 `ErrorCode` 分支，**不解析后端文案**。
- 错误码只有一个来源：`client.ts` 的 `ErrorCode` 由后端 OpenAPI 生成物做编译期校验
  （`satisfies`），数值本身再由 `tests/test_frontend_alignment.py` 逐个比对。
- 字段口径以 `src/api/types.ts` 为准（由后端 OpenAPI 生成，不手写）；
  后端 DTO 在 `zhiyin-api/zhiyin_api/dto/`，转换在 `dto/mappers.py`。

## 五、当前骨架清单（实现方按此认领，不要另建文件）

| 类别 | 已就位 | 待实现 |
| --- | --- | --- |
| 路由 | 7 条路由 + 页面锚点（含智能体小队 / 单智能体页两个功能块） | 登录守卫（未登录拉起 Modal，不跳走） |
| 状态 | session / conversation / workspace / agents 四个 store 及字段 | 各自的 `load*` / `send` / 交互 action（`agents` 的演示能力池与解析分数待换成 bootstrap 下发能力池 + `/app/conversation/message`） |
| 接口 | `client.ts` 信封处理 + `endpoints.ts` 全部接口函数 + **生成类型已就位**（`types.ts` / `schema.ts`） | 无（后端 DTO 变更时跑 `npm run gen:api`） |
| 组件 | 32 个组件（见 §二 表；本次新增 `home/TaskCardGroup`，此前新增 `agents/{AgentTeamGrid,AgentScopePanel,AgentContextRail}` 与 `conversation/AnalysisHandoff`） | 接入真实接口后把能力池改为 bootstrap 下发 |
| 样式 | `tokens.css` / `main.css` 空位 | 令牌取值（出处：`prototype/原型设计说明.md` §2） |

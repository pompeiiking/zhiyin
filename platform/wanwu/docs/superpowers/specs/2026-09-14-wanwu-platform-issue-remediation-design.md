# Wanwu 平台遗留问题修复设计

## 目标

在不改动既有 P01–P04、P06、P07 修复、不处理 P12 与 P15 的前提下，修复 P05、P08–P11、P13、P14，以及智能体删除和文件分片检查两个路径漂移问题。

## 范围

### 本轮包含

- P05：Action HTTP/SSE 响应始终合法，首片段不丢失，异常以终止事件返回。
- P08：智能体前端对所有终止事件停止加载，并展示非零业务码的错误。
- P09：Record 中间件读取 JSON 请求体后，下游 handler 仍可再次绑定。
- P10：子组织启停不存在 nil-pointer；无效组织 ID 返回明确业务错误。
- P11：内部知识库名称查询正确绑定 `orgId` query 参数。
- P13：工作流静态 Token 选择流程使用当前可用的应用与 API Key 接口。
- P14：保留当前用户详情语义，并提供受管理员权限保护的按 ID 查询接口。
- 路径兼容：补充 `DELETE /user/api/v1/assistant`。
- 路径迁移：前端不再调用 `/service/api/v1/file/check/chunk/list`，改用 `/service/api/v1/file/check/list`。

### 本轮不包含

- P01–P04、P06、P07 的重构、加固或新增测试。
- P12 Python 单节点调试。
- P15 工作流重复发布幂等性。
- 与上述问题无直接关系的权限、共享、外部智能体或 UI 改造。

## 总体策略

采用兼容优先的定点修复。现有可用接口保持不变；需要明确新语义时新增窄接口；跨 Python Action、Go BFF 和 Vue 前端的 SSE 链路使用同一个终止事件契约。每个问题先建立能复现原缺陷的测试，再实施最小修改。

## 设计

### 1. Action 与智能体 SSE 错误契约

Action 服务的 `/agent/action` 无论正常、空输出还是异常，都返回 `text/event-stream`。每条事件使用 `data:<json>\n\n`，JSON 保持现有 OpenAI 兼容字段；最后一条必须包含非空 `finish_reason`。异常事件必须包含非零 `code`、可展示的 `msg`，以及结构完整的 `data.choices` 和 `data.usage`，使 `server_open.py` 不需要访问缺失字段。

`server_open.py` 对 Action 响应执行防御性解析：忽略空行；只解析 `data:` 事件；无法解析或收到非零 `code` 时，向上游输出 Wanwu 智能体终止事件：

```json
{
  "code": 1,
  "message": "具体错误信息",
  "response": "",
  "finish": 1
}
```

BFF 的 `buildAgentChatRespLineProcessor` 保证内部 `error:` 行也转换为数值型非零 `code`、`message`、`msg` 和 `finish:1`。

Vue 的 SSE mixin 先判断 `finish` 再判断业务码：任何 `finish === 1` 都结束 loading；任何 `code !== 0` 都以 `message || msg || 默认错误文案` 替换当前空响应。`code === 7` 的既有展示效果保留，但不再是唯一被处理的错误码。

### 2. JSON 请求体可重用

`Record` 的 `requestBody` 在读取字节并写入 `gin.BodyBytesKey` 后，同时将 `ctx.Request.Body` 重建为相同字节的 reader。这样既兼容使用 `ShouldBindBodyWith` 的旧 handler，也兼容 P09 当前使用 `ShouldBindJSON` 的 handler。

测试必须使用真实 Gin 中间件顺序执行 `Record -> SetResourcePermissions` 的绑定等价流程，并断言 handler 能读到 `resourceType`、`resourceId`、`memberIds` 和 `revision`，不再返回 EOF。

### 3. 子组织状态更新

IAM 的 `ChangeOrgStatus` 不再对 `error` 返回值直接调用 `.Error()`。事务内首先查询目标组织：不存在时返回 IAM 组织业务错误；存在时再执行启用或递归停用。

启用组织时验证父组织存在且已启用；停用组织时递归停用子组织。每次 update 检查数据库错误与 `RowsAffected`，避免无效 ID 被当作成功。顶级组织仍禁止改变状态。

### 4. 内部知识库名称查询

`SearchKnowledgeInfoReq.OrgId` 同时声明 `json:"orgId" form:"orgId"`。handler 继续使用 `BindQuery`，并由请求结构的校验规则明确 `categoryName`、`userId`、`orgId` 是否必填。按照该内部接口现有用途，本轮将三者均设为必填，缺少字段返回 BFF 参数错误而不是权限或资源不存在。

### 5. 工作流静态 Token 的应用选择

不恢复遗留 `/bffservice/v2/app/list`。在当前 BFF 下新增只服务于应用/API Key 选择的聚合接口：

```text
GET /user/api/v1/appspace/app/key/options
```

返回结构：

```json
{
  "list": [
    {
      "appId": "...",
      "appType": "agent|rag|workflow",
      "appName": "...",
      "apiId": "...",
      "apiKey": "..."
    }
  ]
}
```

服务层复用当前应用列表和 API Key 查询能力，只返回当前用户、当前组织可见且已经拥有 API Key 的应用。一个应用有多个 Key 时返回多个选项；没有 Key 的应用不返回。前端 `workflow/components/common/app.vue` 改用该接口，不再依赖不存在的 `status` 字段；选项 value 改为对象或仅保存索引，禁止继续用 `apiKey + "|" + appId` 拼接，以免 key 内容破坏解析。

### 6. 用户详情接口语义

`GET /user/api/v1/user/info` 保持“获取当前 JWT 用户”不变，并在 Swagger 描述中明确该语义。

新增：

```text
GET /user/api/v1/user/detail?userId=<ID>
```

新接口注册在 `permission.user` 子路由下，复用其管理员权限校验。handler 绑定必填 `userId`，service 使用目标 userId 和当前 `X-Org-Id` 调用 IAM；普通用户不能借此查询其他用户。

### 7. 路径兼容与迁移

新增 `DELETE /user/api/v1/assistant`，请求体为：

```json
{"assistantId":"..."}
```

handler 转调现有 `DeleteAppSpaceApp(..., appType="agent")`，保留 `/appspace/app` 通用删除接口。

前端 `chunkFile.js` 中遗留的 `/file/check/chunk/list` 改为 `/file/check/list`，参数继续使用后端定义的 `chunkName`。本轮不注册旧路径别名，因为该调用仅存在于仓库内前端且可以同步发布；对外文档改为只声明新路径。

## 测试与验收

### 自动化测试

- Python：Action 正常输出不丢首块；空生成器仍返回终止事件；生成中异常返回合法 SSE；`server_open.py` 能处理错误事件和畸形行。
- Go BFF：SSE `error:` 转换；Record 后 JSON 再绑定；`orgId` query 绑定；管理员用户详情路由；智能体删除兼容路由；API Key 选项聚合和权限过滤。
- Go IAM：目标组织不存在、启用、停用、父组织停用、顶级组织五类状态测试，且不得 panic。
- Vue：所有 `finish:1` 结束加载；非零 code 展示错误；静态 Token 选择使用聚合接口；分片检查使用新路径。

### 接口验收

- `POST /user/api/v1/assistant/stream`：模拟 Action 异常时页面停止加载并显示原因。
- `PUT /user/api/v1/resource/permissions`：合法 body 返回成功，不再出现 `auth错误: EOF`。
- `PUT /user/api/v1/org/status`：有效子组织成功；无效 ID 返回明确业务码且服务无 panic。
- `GET /user/api/v1/api/category/info`：携带三个 query 参数时能正确进入知识库查询。
- `GET /user/api/v1/appspace/app/key/options`：只返回可见且有 Key 的应用，静态 Token 生成流程可完成。
- `GET /user/api/v1/user/info?userId=other`：仍返回当前用户；`GET /user/api/v1/user/detail?userId=other` 仅管理员可用。
- `DELETE /user/api/v1/assistant`：删除指定智能体；通用删除接口行为不变。
- `GET /service/api/v1/file/check/list?chunkName=...`：前端请求无 404。

## 兼容性与回滚

- 不改变现有成功响应结构和现有通用路由。
- SSE 只扩展统一的错误处理，成功流保持现有字段。
- 新用户详情和 API Key 选项均为新增接口，可独立回滚。
- 路径迁移与对应前端修改必须同批发布。
- 每个修复组独立提交，回滚不依赖 P12、P15 或既有修复加固。

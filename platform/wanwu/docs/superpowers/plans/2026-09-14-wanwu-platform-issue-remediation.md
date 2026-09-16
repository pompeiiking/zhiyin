# Wanwu Platform Issue Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 P05、P08–P11、P13、P14，以及智能体删除和文件分片检查路径问题，同时保持现有成功接口兼容。

**Architecture:** Python Action、Go BFF 和 Vue 前端共享“非零 code + message + finish:1”的终止语义；BFF/IAM 的独立缺陷采用窄函数与窄路由修复。新能力通过兼容接口增加，现有当前用户、通用删除和成功 SSE 结构保持不变。

**Tech Stack:** Python 3/Flask/Gunicorn、Go/Gin/gRPC/GORM、Vue 2/Element UI、Node.js CommonJS 测试。

**Spec:** `docs/superpowers/specs/2026-09-14-wanwu-platform-issue-remediation-design.md`

## Global Constraints

- 不修改或加固 P01–P04、P06、P07。
- 不处理 P12、P15。
- 保留 `/user/api/v1/user/info`、`/user/api/v1/appspace/app` 和现有成功 SSE 的兼容行为。
- 当前工作树已有用户修改；禁止 reset、checkout 或覆盖，提交前必须用 `git diff --cached` 确认只包含本任务文件/代码块。
- `agent/agent_open_source/agent_plugin/http_action_server.py`、`agent/agent_open_source/server_open.py`、`internal/bff-service/service/assistant_chat.go` 已有未提交修改；使用 `git add -p` 分块暂存，不能把无关修改带入提交。
- 新增错误文案必须同时提供中文默认文本；不得把内部栈信息直接展示给浏览器。

---

### Task 1: P05 Action SSE 协议与异常终止

**Files:**
- Create: `agent/agent_open_source/agent_plugin/sse_protocol.py`
- Create: `agent/agent_open_source/agent_plugin/tests/test_sse_protocol.py`
- Modify: `agent/agent_open_source/agent_plugin/http_action_server.py:180-314`
- Modify: `agent/agent_open_source/server_open.py:336-388`

**Interfaces:**
- Produces: `make_action_event(content: str, model: str, code: int = 0, message: str = "ok", finish_reason: str = "", usage: dict | None = None) -> str`，返回完整 `data:<json>\n\n`。
- Produces: `parse_action_event(line: str) -> dict | None`，仅接受 `data:` 事件，空行返回 `None`，畸形 JSON 抛出 `ValueError`。
- Consumes: Action 现有 OpenAI-compatible `data.choices[0].message.content` 与 `finish_reason` 结构。

- [ ] **Step 1: 写协议函数失败测试**

```python
import json
import unittest

from agent_plugin.sse_protocol import make_action_event, parse_action_event


class ActionSSEProtocolTest(unittest.TestCase):
    def test_success_event_is_framed_and_parseable(self):
        raw = make_action_event("首片", "model-a")
        self.assertTrue(raw.startswith("data:"))
        self.assertTrue(raw.endswith("\n\n"))
        event = parse_action_event(raw.strip())
        self.assertEqual(event["data"]["choices"][0]["message"]["content"], "首片")

    def test_error_event_is_terminal_and_structurally_complete(self):
        raw = make_action_event("", "model-a", code=1, message="模型失败", finish_reason="stop")
        event = parse_action_event(raw.strip())
        self.assertEqual(event["code"], 1)
        self.assertEqual(event["msg"], "模型失败")
        self.assertEqual(event["data"]["choices"][0]["finish_reason"], "stop")
        self.assertEqual(event["data"]["usage"]["total_tokens"], 0)

    def test_empty_line_is_ignored_and_bad_json_fails(self):
        self.assertIsNone(parse_action_event(""))
        with self.assertRaises(ValueError):
            parse_action_event("data:{bad")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `docker exec agent-wanwu bash -lc 'cd /agent/agent_open_source && python -m unittest agent_plugin.tests.test_sse_protocol -v'`

Expected: FAIL，错误为 `No module named 'agent_plugin.sse_protocol'`。

- [ ] **Step 3: 实现纯协议模块**

```python
import json


def make_action_event(content, model, code=0, message="ok", finish_reason="", usage=None):
    usage = usage or {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0}
    payload = {
        "code": code,
        "data": {
            "choices": [{"finish_reason": finish_reason, "index": 0,
                         "message": {"content": content, "role": "assistant"}}],
            "model": model,
            "object": "chat.completion",
            "usage": usage,
        },
        "msg": message,
    }
    return "data:" + json.dumps(payload, ensure_ascii=False) + "\n\n"


def parse_action_event(line):
    line = line.strip()
    if not line:
        return None
    if not line.startswith("data:"):
        raise ValueError("Action response is not an SSE data event")
    return json.loads(line[5:])
```

- [ ] **Step 4: 用 helper 替换 Action 手写事件并修复异常分支**

在 `http_action_server.py` 中导入 `make_action_event`，正常分片、正常结束和 `except` 都调用它。异常分支必须：

```python
except Exception as exc:
    logger.exception("action execution failed")
    yield make_action_event(
        content="",
        model=model,
        code=1,
        message=str(exc) or "Action 执行失败",
        finish_reason="stop",
    )
```

保持 `action_infer()` 直接返回 `Response(stream_with_context(action_result), content_type="text/event-stream; charset=utf-8")`，不得调用 `next(action_result)`。

- [ ] **Step 5: 让 Agent 服务防御性消费 Action SSE**

在 `server_open.py` 中导入 `parse_action_event`，将循环改为：忽略空行；捕获 `ValueError/KeyError/TypeError` 后输出 `code:1, finish:1`；收到 Action 非零 code 时立即输出同样的 Wanwu 终止事件并停止；只有结构完整的成功事件才读取 content/usage。

错误输出必须使用：

```python
def agent_error_event(message):
    return {
        "code": 1,
        "message": message or "Action 执行失败",
        "response": "",
        "finish": 1,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "search_list": [],
        "gen_file_url_list": [],
    }
```

- [ ] **Step 6: 运行 Python 测试和语法检查**

Run: `docker exec agent-wanwu bash -lc 'cd /agent/agent_open_source && python -m unittest agent_plugin.tests.test_sse_protocol -v && python -m py_compile agent_plugin/sse_protocol.py agent_plugin/http_action_server.py server_open.py'`

Expected: 3 tests PASS，`py_compile` 退出码 0。

- [ ] **Step 7: 提交 P05**

```bash
git add agent/agent_open_source/agent_plugin/sse_protocol.py agent/agent_open_source/agent_plugin/tests/test_sse_protocol.py
git add -p agent/agent_open_source/agent_plugin/http_action_server.py agent/agent_open_source/server_open.py
git diff --cached
git commit -m "fix(agent): return terminal SSE events on action errors"
```

---

### Task 2: P08 BFF 与 Vue 统一结束错误状态

**Files:**
- Modify: `internal/bff-service/service/assistant_chat.go:84-98`
- Modify: `internal/bff-service/service/assistant_chat_test.go`
- Create: `web/src/utils/agentSse.js`
- Create: `web/tests/agent-sse.test.cjs`
- Modify: `web/src/mixins/sseMethod.js:362-435`
- Modify: `web/package.json`

**Interfaces:**
- Produces: Go `buildAgentChatRespLineProcessor()` 对 `error:` 返回 `data: {"code":1,"message":"...","msg":"...","finish":1}\n\n`。
- Produces: JS `normalizeAgentTerminalEvent(data) -> {terminal:boolean,errorMessage:string}`。
- Consumes: Task 1 输出的 Wanwu 智能体错误事件。

- [ ] **Step 1: 扩展 Go 失败测试**

在 `assistant_chat_test.go` 的解析结构中加入 `Msg string` 与 `Finish int`，断言：

```go
if result.Code != 1 || result.Message != message || result.Msg != message || result.Finish != 1 {
    t.Fatalf("invalid terminal error response: %+v", result)
}
```

- [ ] **Step 2: 运行 Go 测试确认失败**

Run: `go test ./internal/bff-service/service -run TestAgentStreamErrorIsValidJSON -count=1`

Expected: FAIL，因为当前 code 是 `-1` 或断言字段不完整。

- [ ] **Step 3: 修改 BFF 错误映射**

将 map 固定为：

```go
map[string]interface{}{
    "code": 1, "message": message, "msg": message, "finish": 1,
}
```

保留 `json.Marshal`，不得使用字符串插值生成 JSON。

- [ ] **Step 4: 写前端纯函数失败测试**

```javascript
const assert = require('assert')
const fs = require('fs')
const vm = require('vm')
const source = fs.readFileSync('src/utils/agentSse.js', 'utf8').replace(/^export /gm, '')
const context = {}
vm.runInNewContext(source, context)

assert.deepStrictEqual(
  JSON.parse(JSON.stringify(context.normalizeAgentTerminalEvent({ code: 1, message: '失败', finish: 1 }))),
  { terminal: true, errorMessage: '失败' }
)
assert.strictEqual(context.normalizeAgentTerminalEvent({ code: 0, finish: 0 }).terminal, false)
assert.strictEqual(context.normalizeAgentTerminalEvent({ code: 7, msg: '敏感', finish: 1 }).errorMessage, '敏感')
```

- [ ] **Step 5: 运行前端测试确认失败**

Run: `node web/tests/agent-sse.test.cjs`

Expected: FAIL，文件不存在或函数未定义。

- [ ] **Step 6: 实现并接入终止事件归一化**

```javascript
export function normalizeAgentTerminalEvent(data = {}) {
  const terminal = Number(data.finish) === 1
  const errorMessage = Number(data.code) === 0 ? '' :
    (data.message || data.msg || '服务处理失败，请稍后重试')
  return { terminal, errorMessage }
}
```

在 `sseMethod.js` 的 `onmessage` 中先调用该函数。若 `errorMessage` 非空，用现有 `replaceLastData` 写入错误；若 `terminal` 为真，无条件 `setStoreSessionStatus(-1)`。成功 code 继续走现有打印逻辑，`code === 7` 不再单独承担结束职责。

- [ ] **Step 7: 注册并运行前端测试**

在 `web/package.json` 增加：

```json
"test:agent-sse": "node tests/agent-sse.test.cjs"
```

Run: `cd web && npm run test:agent-sse`

Expected: PASS。

- [ ] **Step 8: 运行本任务全部测试并提交**

```bash
go test ./internal/bff-service/service -run TestAgentStreamErrorIsValidJSON -count=1
cd web && npm run test:agent-sse
git add -p internal/bff-service/service/assistant_chat.go
git add internal/bff-service/service/assistant_chat_test.go web/src/utils/agentSse.js web/tests/agent-sse.test.cjs web/src/mixins/sseMethod.js web/package.json
git diff --cached
git commit -m "fix(agent): finish and display all SSE errors"
```

---

### Task 3: P09 Record 后请求体可重复绑定

**Files:**
- Modify: `internal/bff-service/server/http/middleware/record.go:43-72`
- Create: `internal/bff-service/server/http/middleware/record_test.go`

**Interfaces:**
- Produces: `requestBody(ctx) (string, error)` 在返回前保证 `ctx.Request.Body` 仍包含原始 JSON。
- Consumes: Gin `BodyBytesKey` 缓存约定。

- [ ] **Step 1: 写真实中间件顺序失败测试**

```go
func TestRecordRestoresJSONBodyForShouldBindJSON(t *testing.T) {
    gin.SetMode(gin.TestMode)
    router := gin.New()
    router.Use(Record)
    router.PUT("/resource/permissions", func(ctx *gin.Context) {
        var req struct {
            ResourceType string   `json:"resourceType" binding:"required"`
            ResourceID   string   `json:"resourceId" binding:"required"`
            MemberIDs    []string `json:"memberIds"`
            Revision     *uint64  `json:"revision" binding:"required"`
        }
        if err := ctx.ShouldBindJSON(&req); err != nil {
            ctx.String(http.StatusBadRequest, err.Error())
            return
        }
        ctx.Status(http.StatusNoContent)
    })
    body := `{"resourceType":"agent","resourceId":"12","memberIds":["2"],"revision":0}`
    request := httptest.NewRequest(http.MethodPut, "/resource/permissions", strings.NewReader(body))
    request.Header.Set("Content-Type", "application/json")
    recorder := httptest.NewRecorder()
    router.ServeHTTP(recorder, request)
    if recorder.Code != http.StatusNoContent {
        t.Fatalf("status=%d body=%s", recorder.Code, recorder.Body.String())
    }
}
```

- [ ] **Step 2: 运行测试确认 EOF 失败**

Run: `go test ./internal/bff-service/server/http/middleware -run TestRecordRestoresJSONBodyForShouldBindJSON -count=1`

Expected: FAIL，HTTP 400 且响应包含 `EOF`。

- [ ] **Step 3: 在读取后恢复 Body**

为 `record.go` 增加 `bytes` 导入，并在取得 `body` 后、任何 return 前执行：

```go
ctx.Set(gin.BodyBytesKey, body)
ctx.Request.Body = io.NopCloser(bytes.NewReader(body))
```

从缓存读取到 body 时也执行恢复，确保多次调用一致。

- [ ] **Step 4: 运行中间件测试**

Run: `go test ./internal/bff-service/server/http/middleware -count=1`

Expected: PASS。

- [ ] **Step 5: 提交 P09**

```bash
git add internal/bff-service/server/http/middleware/record.go internal/bff-service/server/http/middleware/record_test.go
git diff --cached
git commit -m "fix(bff): restore JSON body after request logging"
```

---

### Task 4: P10 子组织状态更新不 panic 且校验无效 ID

**Files:**
- Modify: `internal/iam-service/client/orm/org.go:246-290`
- Create: `internal/iam-service/client/orm/org_status_test.go`

**Interfaces:**
- Produces: `changeOrgStatus(tx *gorm.DB, orgID uint32, status bool) error` 对不存在组织返回错误，对成功返回 nil。
- Consumes: `Client.transaction` 将非 nil `err_code.Status` 回滚事务。

- [ ] **Step 1: 建立 SQLite 测试数据库与失败用例**

使用仓库已有 `github.com/glebarez/sqlite`：

```go
func openOrgStatusDB(t *testing.T) *gorm.DB {
    dsn := fmt.Sprintf("file:%s?mode=memory&cache=shared", t.Name())
    db, err := gorm.Open(sqlite.Open(dsn), &gorm.Config{})
    if err != nil { t.Fatal(err) }
    if err := db.AutoMigrate(&model.Org{}); err != nil { t.Fatal(err) }
    return db
}

func TestChangeOrgStatusRejectsMissingOrgWithoutPanic(t *testing.T) {
    db := openOrgStatusDB(t)
    if err := changeOrgStatus(db, 999, false); err == nil {
        t.Fatal("missing organization accepted")
    }
}
```

再增加：父组织停用时启用子组织失败；停用父组织会停用两级子组织；有效启用/停用成功。

- [ ] **Step 2: 运行测试确认失败**

Run: `go test ./internal/iam-service/client/orm -run 'TestChangeOrgStatus' -count=1`

Expected: 至少缺失组织用例 FAIL，或出现原 nil-pointer panic。

- [ ] **Step 3: 重写状态更新流程**

先查询目标组织：

```go
org := &model.Org{}
if err := sqlopt.WithID(orgID).Apply(tx).First(org).Error; err != nil {
    return fmt.Errorf("change org %v status %v get org err: %w", orgID, status, err)
}
```

启用时查询并校验 `org.ParentID`；停用时递归处理子组织。最终更新保存 result 并检查：

```go
result := sqlopt.WithID(orgID).Apply(tx).Model(&model.Org{}).Update("status", status)
if result.Error != nil {
    return fmt.Errorf("change org %v status %v err: %w", orgID, status, result.Error)
}
if result.RowsAffected != 1 {
    return fmt.Errorf("change org %v status %v: organization not found", orgID, status)
}
return nil
```

调用处改为：

```go
if err := changeOrgStatus(tx, orgID, status); err != nil {
    return toErrStatus("iam_org_change_status", err.Error())
}
return nil
```

- [ ] **Step 4: 运行 IAM 测试**

Run: `go test ./internal/iam-service/client/orm -count=1`

Expected: PASS，无 panic。

- [ ] **Step 5: 提交 P10**

```bash
git add internal/iam-service/client/orm/org.go internal/iam-service/client/orm/org_status_test.go
git diff --cached
git commit -m "fix(iam): validate organizations during status changes"
```

---

### Task 5: P11 知识库名称查询绑定完整 query

**Files:**
- Modify: `internal/bff-service/model/request/knowledge.go:43-48`
- Create: `internal/bff-service/model/request/knowledge_test.go`

**Interfaces:**
- Produces: `SearchKnowledgeInfoReq` 从 query 绑定 `categoryName`、`userId`、`orgId`，三者均必填。

- [ ] **Step 1: 写绑定失败测试**

```go
func TestSearchKnowledgeInfoReqBindsOrgIDFromQuery(t *testing.T) {
    ctx, _ := gin.CreateTestContext(httptest.NewRecorder())
    ctx.Request = httptest.NewRequest(http.MethodGet,
        "/api/category/info?categoryName=docs&userId=2&orgId=3", nil)
    var req SearchKnowledgeInfoReq
    if err := ctx.ShouldBindQuery(&req); err != nil { t.Fatal(err) }
    if req.KnowledgeName != "docs" || req.UserId != "2" || req.OrgId != "3" {
        t.Fatalf("bad binding: %+v", req)
    }
}
```

增加缺少 `orgId` 时校验失败的用例。先调用 `internal/bff-service/pkg/util.InitValidator()`，再对请求执行 `util.Validate(&req)`，断言返回 required 校验错误；`CommonCheck.Check()` 本身不负责字段标签校验。

- [ ] **Step 2: 运行测试确认失败**

Run: `go test ./internal/bff-service/model/request -run TestSearchKnowledgeInfoReq -count=1`

Expected: FAIL，`OrgId` 为空或校验未失败。

- [ ] **Step 3: 修正标签和校验**

```go
type SearchKnowledgeInfoReq struct {
    KnowledgeName string `json:"categoryName" form:"categoryName" validate:"required"`
    UserId        string `json:"userId" form:"userId" validate:"required"`
    OrgId         string `json:"orgId" form:"orgId" validate:"required"`
    CommonCheck
}
```

- [ ] **Step 4: 运行请求模型测试并提交**

```bash
go test ./internal/bff-service/model/request -count=1
git add internal/bff-service/model/request/knowledge.go internal/bff-service/model/request/knowledge_test.go
git diff --cached
git commit -m "fix(bff): bind organization in knowledge lookup"
```

---

### Task 6: P13 当前 BFF 提供应用/API Key 选项

**Files:**
- Modify: `internal/bff-service/model/response/api_key.go`
- Modify: `internal/bff-service/service/api_key.go`
- Create: `internal/bff-service/service/api_key_options_test.go`
- Modify: `internal/bff-service/server/http/handler/v1/api_key.go`
- Modify: `internal/bff-service/server/http/handler/router/v1/common.go`
- Modify: `web/src/api/workflow.js:113-119`
- Modify: `web/src/views/workflow/components/common/app.vue:56-120`
- Create: `web/tests/workflow-app-options.test.cjs`
- Modify: `web/package.json`

**Interfaces:**
- Produces: `response.AppKeyOption {AppID, AppType, AppName, APIID, APIKey}`。
- Produces: `GetAppKeyOptions(ctx, userID, orgID string) ([]response.AppKeyOption, error)`。
- Produces: `GET /user/api/v1/appspace/app/key/options`。
- Consumes: `GetAppSpaceAppList` 的权限过滤结果与 `app.GetApiKeyList`。

- [ ] **Step 1: 写选项组装失败测试**

将纯组装逻辑定义为：

```go
func buildAppKeyOptions(apps []response.AppBriefInfo,
    getKeys func(appID, appType string) ([]*response.ApiResponse, error),
) ([]response.AppKeyOption, error)
```

测试输入两个可见应用：第一个有两个 key，第二个无 key；断言只得到两个选项且 `AppName/AppType/APIKey` 正确。再让 `getKeys` 返回错误并断言函数原样返回错误。

- [ ] **Step 2: 运行测试确认失败**

Run: `go test ./internal/bff-service/service -run TestBuildAppKeyOptions -count=1`

Expected: FAIL，函数或类型未定义。

- [ ] **Step 3: 增加响应类型与服务函数**

```go
type AppKeyOption struct {
    AppID   string `json:"appId"`
    AppType string `json:"appType"`
    AppName string `json:"appName"`
    APIID   string `json:"apiId"`
    APIKey  string `json:"apiKey"`
}
```

`GetAppKeyOptions` 调用 `GetAppSpaceAppList(ctx, userID, orgID, "", "")`；对每个 `AppBriefInfo` 调用现有 `GetApiKeyList` 等价 gRPC 请求，并交给 `buildAppKeyOptions`。不得重新查询或绕过资源可见性。

- [ ] **Step 4: 注册 handler 和路由**

handler：

```go
func GetAppKeyOptions(ctx *gin.Context) {
    resp, err := service.GetAppKeyOptions(ctx, getUserID(ctx), getOrgID(ctx))
    gin_util.Response(ctx, map[string]interface{}{"list": resp}, err)
}
```

在 common 路由注册：

```go
mid.Sub("common").Reg(apiV1, "/appspace/app/key/options", http.MethodGet,
    v1.GetAppKeyOptions, "获取应用API Key选项", middleware.CheckResourceOrg)
```

- [ ] **Step 5: 写前端映射失败测试**

将组件映射抽成 `toAppKeyOptions(list)` 并测试：

```javascript
assert.deepStrictEqual(
  JSON.parse(JSON.stringify(toAppKeyOptions([{appId:'1', appType:'agent', appName:'A', apiId:'k1', apiKey:'a|b'}]))),
  [{label:'A', value:{appId:'1', apiKey:'a|b'}}]
)
```

该断言确保不再用 `|` 拆分 key。

- [ ] **Step 6: 修改工作流 API 与组件**

`getAppList` 改为请求 `/user/api/v1/appspace/app/key/options`。组件 `value` 保存 `{appId, apiKey}`；`doSubmit` 直接传：

```javascript
getStaticToken({ appid: this.value.appId, apiKey: this.value.apiKey })
```

删除 `status === true`、`appName/apiKey/appId` 的旧列表假设和调试 `console.log`。

- [ ] **Step 7: 运行后端和前端测试**

```bash
go test ./internal/bff-service/service -run TestBuildAppKeyOptions -count=1
cd web && node tests/workflow-app-options.test.cjs
```

Expected: PASS。

- [ ] **Step 8: 提交 P13**

```bash
git add internal/bff-service/model/response/api_key.go internal/bff-service/service/api_key.go internal/bff-service/service/api_key_options_test.go internal/bff-service/server/http/handler/v1/api_key.go internal/bff-service/server/http/handler/router/v1/common.go web/src/api/workflow.js web/src/views/workflow/components/common/app.vue web/tests/workflow-app-options.test.cjs web/package.json
git diff --cached
git commit -m "fix(workflow): source static-token apps from current BFF"
```

---

### Task 7: P14 分离当前用户与管理员用户详情

**Files:**
- Modify: `internal/bff-service/model/request/permission_user.go`
- Modify: `internal/bff-service/server/http/handler/v1/common.go:26-38`
- Modify: `internal/bff-service/server/http/handler/v1/permission_user.go`
- Modify: `internal/bff-service/server/http/handler/router/v1/permission.go`
- Create: `internal/bff-service/server/http/handler/v1/permission_user_detail_test.go`

**Interfaces:**
- Preserves: `GET /user/info` 始终使用 JWT user ID。
- Produces: `GET /user/detail?userId=<ID>`，仅位于 `permission.user` 权限组。
- Consumes: 现有 `service.GetUserInfo(ctx, targetUserID, orgID)`。

- [ ] **Step 1: 写 handler 绑定失败测试**

新增可注入的小函数：

```go
func getUserDetail(ctx *gin.Context, fetch func(*gin.Context, string, string) (*response.UserInfo, error))
```

测试传入 `/user/detail?userId=42` 和上下文 org ID，stub 记录参数，断言目标 ID 为 `42`；缺失 userId 时断言 BFF 参数错误且 stub 未调用。

- [ ] **Step 2: 运行测试确认失败**

Run: `go test ./internal/bff-service/server/http/handler/v1 -run TestGetUserDetail -count=1`

Expected: FAIL，handler/请求类型尚不存在。

- [ ] **Step 3: 增加请求类型、handler 和权限路由**

请求类型：

```go
type UserDetailQuery struct {
    UserID string `form:"userId" validate:"required"`
    CommonCheck
}
```

handler 使用 `gin_util.BindQuery`，调用 `service.GetUserInfo(ctx, req.UserID, getOrgID(ctx))`。路由注册：

```go
mid.Sub("permission.user").Reg(apiV1, "/user/detail", http.MethodGet,
    v1.GetUserDetail, "管理员获取用户详情")
```

仅更新当前 `/user/info` Swagger Summary/Description 为“获取当前登录用户信息”，不得读取 query userId。

- [ ] **Step 4: 运行 handler 和路由包测试**

Run: `go test ./internal/bff-service/server/http/handler/v1 ./internal/bff-service/server/http/handler/router/v1 -count=1`

Expected: PASS。

- [ ] **Step 5: 提交 P14**

```bash
git add internal/bff-service/model/request/permission_user.go internal/bff-service/server/http/handler/v1/common.go internal/bff-service/server/http/handler/v1/permission_user.go internal/bff-service/server/http/handler/router/v1/permission.go internal/bff-service/server/http/handler/v1/permission_user_detail_test.go
git diff --cached
git commit -m "feat(bff): add admin user detail endpoint"
```

---

### Task 8: 智能体删除兼容路由与分片检查路径迁移

**Files:**
- Modify: `internal/bff-service/model/request/assistant.go`
- Modify: `internal/bff-service/server/http/handler/v1/assistant.go`
- Modify: `internal/bff-service/server/http/handler/router/v1/assistant.go`
- Create: `internal/bff-service/server/http/handler/v1/assistant_delete_test.go`
- Modify: `web/src/api/chunkFile.js:38-46`
- Create: `web/tests/api-paths.test.cjs`
- Modify: `web/package.json`

**Interfaces:**
- Produces: `DELETE /assistant` body `{"assistantId":"..."}`，内部固定 `appType="agent"`。
- Preserves: `DELETE /appspace/app`。
- Produces: `continueChunks(data)` 请求 `/service/api/v1/file/check/list`。

- [ ] **Step 1: 写智能体删除 handler 失败测试**

新增可注入内部函数：

```go
func deleteAssistant(ctx *gin.Context,
    remove func(*gin.Context, string, string, string, string) error)
```

测试发送 `{"assistantId":"99"}`，设置 user/org 上下文，断言 remove 参数依次为 user、org、`99`、`constant.AppTypeAgent`；空 assistantId 时断言 remove 未调用。

- [ ] **Step 2: 运行 Go 测试确认失败**

Run: `go test ./internal/bff-service/server/http/handler/v1 -run TestDeleteAssistant -count=1`

Expected: FAIL，handler/请求类型不存在。

- [ ] **Step 3: 实现请求、handler 与路由**

请求类型：

```go
type AssistantDeleteRequest struct {
    AssistantId string `json:"assistantId" validate:"required"`
    CommonCheck
}
```

handler 使用 `gin_util.Bind`，调用 `service.DeleteAppSpaceApp(ctx, getUserID(ctx), getOrgID(ctx), req.AssistantId, constant.AppTypeAgent)`。在 `registerAssistant` 中注册 `http.MethodDelete` 的 `/assistant`。

- [ ] **Step 4: 写前端路径失败测试**

`api-paths.test.cjs` 读取 `src/api/chunkFile.js`，断言包含 ``/v1/file/check/list`` 且不包含 ``/v1/file/check/chunk/list``。

- [ ] **Step 5: 运行路径测试确认失败并修改 URL**

Run: `node web/tests/api-paths.test.cjs`

Expected: FAIL。随后把 `continueChunks` URL 改为：

```javascript
url: `${BASE_URL}/v1/file/check/list`,
```

- [ ] **Step 6: 运行本任务测试**

```bash
go test ./internal/bff-service/server/http/handler/v1 ./internal/bff-service/server/http/handler/router/v1 -count=1
cd web && node tests/api-paths.test.cjs
```

Expected: PASS。

- [ ] **Step 7: 提交路径修复**

```bash
git add internal/bff-service/model/request/assistant.go internal/bff-service/server/http/handler/v1/assistant.go internal/bff-service/server/http/handler/router/v1/assistant.go internal/bff-service/server/http/handler/v1/assistant_delete_test.go web/src/api/chunkFile.js web/tests/api-paths.test.cjs web/package.json
git diff --cached
git commit -m "fix(api): restore assistant delete and chunk-check paths"
```

---

### Task 9: 全量验证与接口回归

**Files:**
- Modify only if generated by the repository's documented commands: `docs/v1/swagger.json`, `docs/v1/swagger.yaml`, `docs/v1/docs.go`
- Modify: `docs/wanwu-errors-and-unavailable-interfaces-summary.md`

**Interfaces:**
- Consumes: Tasks 1–8 的全部接口和测试。
- Produces: 当前源码状态与问题文档一致的验收记录。

- [ ] **Step 1: 运行 Go 目标测试**

```bash
go test ./internal/bff-service/model/request ./internal/bff-service/server/http/middleware ./internal/bff-service/server/http/handler/v1 ./internal/bff-service/server/http/handler/router/v1 ./internal/bff-service/service ./internal/iam-service/client/orm -count=1
```

Expected: 全部 PASS，0 panic。

- [ ] **Step 2: 运行 Python 目标测试与编译检查**

```bash
docker exec agent-wanwu bash -lc 'cd /agent/agent_open_source && python -m unittest agent_plugin.tests.test_sse_protocol -v && python -m py_compile agent_plugin/sse_protocol.py agent_plugin/http_action_server.py server_open.py'
```

Expected: 全部 PASS，退出码 0。

- [ ] **Step 3: 安装现有前端依赖并运行目标测试/构建**

```bash
cd web
npm ci
npm run test:agent-sse
node tests/workflow-app-options.test.cjs
node tests/api-paths.test.cjs
npm run build
```

Expected: 三组测试 PASS，Vue production build 成功。若 `npm ci` 因仓库没有 lockfile 失败，停止并报告依赖管理问题，不改用 `npm install` 生成新锁文件。

- [ ] **Step 4: 重新生成并检查 OpenAPI（仅在仓库已有生成命令可用时）**

先运行 `rg -n "swag init|swagger" Makefile README.md scripts` 定位唯一官方命令；执行该命令后检查只更新 `/assistant` DELETE、`/user/detail` 和 `/appspace/app/key/options`。若不存在生成命令，不手工改生成文件，只更新 Markdown 接口文档。

- [ ] **Step 5: 执行真实接口验收**

使用现有 `scripts/wanwu-api-test` 的 session/JWT 配置，逐项请求：

```text
POST   /user/api/v1/assistant/stream          Action 异常 => code 1, finish 1
PUT    /user/api/v1/resource/permissions      合法 JSON => 不出现 EOF
PUT    /user/api/v1/org/status                有效 ID 成功；无效 ID 明确错误且无 panic
GET    /user/api/v1/api/category/info         三个 query 参数正确绑定
GET    /user/api/v1/appspace/app/key/options  只返回可见且有 Key 的应用
GET    /user/api/v1/user/info                 仍返回当前用户
GET    /user/api/v1/user/detail?userId=...    管理员成功、普通用户拒绝
DELETE /user/api/v1/assistant                 指定智能体删除成功
GET    /service/api/v1/file/check/list        不返回 404
```

每个请求记录 HTTP 状态、业务 code、响应摘要和服务端错误日志；测试数据使用新建资源并在测试结束后通过对应非破坏性删除接口清理。

- [ ] **Step 6: 更新问题状态文档**

在 `docs/wanwu-errors-and-unavailable-interfaces-summary.md` 中：P05、P08–P11、P13、P14 标为已通过的具体日期和证据；P12、P15 明确保留未修；删除路径与分片路径写入新的可用接口。不得把未执行端到端验收的项目标为“已修复”。

- [ ] **Step 7: 检查范围和最终差异**

```bash
git status --short
git diff --check
git diff --stat HEAD~8..HEAD
git log --oneline -10
```

Expected: 无空白错误；没有 P12/P15 或 P01–P04/P06/P07 加固改动；现有用户修改未丢失。

- [ ] **Step 8: 提交文档/生成物**

```bash
git add docs/wanwu-errors-and-unavailable-interfaces-summary.md
git add docs/v1/swagger.json docs/v1/swagger.yaml docs/v1/docs.go
git diff --cached
git commit -m "docs: record wanwu remediation verification"
```

若 Step 4 未生成 OpenAPI 文件，则只暂存并提交 Markdown 状态文档。

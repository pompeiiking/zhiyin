package v1

import (
	"net/http"

	mid "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util/mid-wrap"
	v1 "github.com/UnicomAI/wanwu/internal/bff-service/server/http/handler/v1"
	"github.com/UnicomAI/wanwu/internal/bff-service/server/http/middleware"
	"github.com/UnicomAI/wanwu/pkg/constant"
	"github.com/gin-gonic/gin"
)

func registerCommon(apiV1 *gin.RouterGroup) {
	mid.Sub("common").Reg(apiV1, "/user/permission", http.MethodGet, v1.GetUserPermission, "获取用户权限")
	mid.Sub("common").Reg(apiV1, "/user/info", http.MethodGet, v1.GetUserInfo, "获取用户信息")
	mid.Sub("common").Reg(apiV1, "/org/select", http.MethodGet, v1.GetOrgSelect, "获取用户组织列表")
	mid.Sub("common").Reg(apiV1, "/user/password", http.MethodPut, v1.ChangeUserPassword, "修改用户密码（by 个人）")
	mid.Sub("common").Reg(apiV1, "/avatar", http.MethodPost, v1.UploadAvatar, "上传自定义图标")

	// 通用文件上传
	mid.Sub("common").Reg(apiV1, "/file/check", http.MethodGet, v1.CheckFile, "校验文件")
	mid.Sub("common").Reg(apiV1, "/file/check/list", http.MethodGet, v1.CheckFileList, "校验文件列表")
	mid.Sub("common").Reg(apiV1, "/file/upload", http.MethodPost, v1.UploadFile, "上传文件")
	mid.Sub("common").Reg(apiV1, "/file/merge", http.MethodPost, v1.MergeFile, "合并文件")
	mid.Sub("common").Reg(apiV1, "/file/clean", http.MethodPost, v1.CleanFile, "清除文件")
	mid.Sub("common").Reg(apiV1, "/file/delete", http.MethodDelete, v1.DeleteFile, "刪除文件")
	mid.Sub("common").Reg(apiV1, "/proxy/file/upload", http.MethodPost, v1.ProxyUploadFile, "代理上传文件")

	// 文档中心
	mid.Sub("common").Reg(apiV1, "/doc_center", http.MethodGet, v1.GetDocCenter, "获取文档中心路径")

	// 模型通用
	mid.Sub("common").Reg(apiV1, "/model/select/llm", http.MethodGet, v1.ListLlmModels, "llm模型列表展示")
	mid.Sub("common").Reg(apiV1, "/model/select/rerank", http.MethodGet, v1.ListRerankModels, "rerank模型列表展示")
	mid.Sub("common").Reg(apiV1, "/model/select/embedding", http.MethodGet, v1.ListEmbeddingModels, "embedding模型列表展示")

	// 知识库通用
	mid.Sub("common").Reg(apiV1, "/knowledge/select", http.MethodGet, v1.GetKnowledgeSelect, "查询用户知识库列表")

	// rag/agent/workflow通用
	mid.Sub("common").Reg(apiV1, "/appspace/app", http.MethodDelete, v1.DeleteAppSapceApp, "刪除应用")
	mid.Sub("common").Reg(apiV1, "/appspace/app/list", http.MethodGet, v1.GetAppSpaceAppList, "获取应用列表")
	mid.Sub("common").Reg(apiV1, "/appspace/app/publish", http.MethodPost, v1.PublishApp, "发布应用")
	mid.Sub("common").Reg(apiV1, "/appspace/app/url", http.MethodGet, v1.GetApiBaseUrl, "获取Api根地址")
	mid.Sub("common").Reg(apiV1, "/appspace/app/key", http.MethodPost, v1.GenApiKey, "生成ApiKey")
	mid.Sub("common").Reg(apiV1, "/appspace/app/key", http.MethodDelete, v1.DelApiKey, "删除ApiKey")
	mid.Sub("common").Reg(apiV1, "/appspace/app/key/list", http.MethodGet, v1.GetApiKeyList, "获取ApiKey列表")

	// MCP通用
	mid.Sub("common").Reg(apiV1, "/mcp/select", http.MethodGet, v1.GetMCPSelect, "获取MCP自定义列表")

	// 流式对话通用
	mid.Sub("common").Reg(apiV1, "/rag/chat", http.MethodPost, v1.ChatRag, "rag流式接口", middleware.AppHistoryRecord("ragId", constant.AppTypeRag))
	mid.Sub("common").Reg(apiV1, "/assistant/stream", http.MethodPost, v1.AssistantConversionStream, "智能体流式问答", middleware.AppHistoryRecord("assistantId", constant.AppTypeAgent))
}

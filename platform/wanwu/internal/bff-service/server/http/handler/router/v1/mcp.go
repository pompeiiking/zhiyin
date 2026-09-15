package v1

import (
	"net/http"

	mid "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util/mid-wrap"
	v1 "github.com/UnicomAI/wanwu/internal/bff-service/server/http/handler/v1"
	"github.com/gin-gonic/gin"
)

func registerMCP(apiV1 *gin.RouterGroup) {
	// MCP广场
	mid.Sub("mcp").Reg(apiV1, "/mcp/square", http.MethodGet, v1.GetMCPSquareDetail, "获取广场MCP详情")
	mid.Sub("mcp").Reg(apiV1, "/mcp/square/list", http.MethodGet, v1.GetMCPSquareList, "获取广场MCP列表")
	mid.Sub("mcp").Reg(apiV1, "/mcp/square/recommend", http.MethodGet, v1.GetMCPSquareRecommends, "获取广场MCP推荐列表")
	// MCP
	mid.Sub("mcp").Reg(apiV1, "/mcp", http.MethodPost, v1.CreateMCP, "创建自定义MCP")
	mid.Sub("mcp").Reg(apiV1, "/mcp", http.MethodGet, v1.GetMCP, "获取自定义MCP详情")
	mid.Sub("mcp").Reg(apiV1, "/mcp", http.MethodDelete, v1.DeleteMCP, "删除自定义MCP")
	mid.Sub("mcp").Reg(apiV1, "/mcp/list", http.MethodGet, v1.GetMCPList, "获取MCP自定义列表")
	mid.Sub("mcp").Reg(apiV1, "/mcp/tool/list", http.MethodGet, v1.GetMCPTools, "获取MCP Tool列表")
}

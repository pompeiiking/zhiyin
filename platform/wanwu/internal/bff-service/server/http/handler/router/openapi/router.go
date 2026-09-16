package openapi

import (
	"net/http"

	mid "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util/mid-wrap"
	"github.com/UnicomAI/wanwu/internal/bff-service/server/http/handler/openapi"
	"github.com/UnicomAI/wanwu/internal/bff-service/server/http/middleware"
	"github.com/UnicomAI/wanwu/pkg/constant"
	"github.com/gin-gonic/gin"
)

func Register(openAPI *gin.RouterGroup) {
	// openapi
	mid.Sub("openapi").Reg(openAPI, "/agent/conversation", http.MethodPost, openapi.CreateAgentConversation, "智能体创建对话OpenAPI", middleware.AuthOpenAPI(constant.AppTypeAgent))
	mid.Sub("openapi").Reg(openAPI, "/agent/chat", http.MethodPost, openapi.ChatAgent, "智能体问答OpenAPI", middleware.AuthOpenAPI(constant.AppTypeAgent))
	mid.Sub("openapi").Reg(openAPI, "/rag/chat", http.MethodPost, openapi.ChatRag, "文本问答OpenAPI", middleware.AuthOpenAPI(constant.AppTypeRag))
}

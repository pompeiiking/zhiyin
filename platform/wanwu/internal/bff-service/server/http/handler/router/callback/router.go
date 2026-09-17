package callback

import (
	"net/http"

	mid "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util/mid-wrap"
	"github.com/UnicomAI/wanwu/internal/bff-service/server/http/handler/callback"
	"github.com/gin-gonic/gin"
)

func Register(openAPI *gin.RouterGroup) {
	// callback
	mid.Sub("callback").Reg(openAPI, "/model/:modelId", http.MethodGet, callback.GetModelById, "根据modelId获取模型")
	mid.Sub("callback").Reg(openAPI, "/model/:modelId/chat/completions", http.MethodPost, callback.ModelChatCompletions, "Model Chat Completions")
	mid.Sub("callback").Reg(openAPI, "/model/:modelId/embeddings", http.MethodPost, callback.ModelEmbeddings, "Model Embeddings")
	mid.Sub("callback").Reg(openAPI, "/model/:modelId/rerank", http.MethodPost, callback.ModelRerank, "Model Embeddings")
}

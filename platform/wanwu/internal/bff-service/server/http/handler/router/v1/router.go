package v1

import (
	"github.com/gin-gonic/gin"
)

func Register(apiV1 *gin.RouterGroup) {
	// guest
	registerGuest(apiV1)

	// common
	registerCommon(apiV1)

	// callback
	registerV1Callback(apiV1)

	// model
	registerModel(apiV1)

	// knowledge
	registerKnowledge(apiV1)

	// mcp
	registerMCP(apiV1)

	// rag
	registerRag(apiV1)

	// assistant
	registerAssistant(apiV1)

	// exploration
	registerExploration(apiV1)

	// permission
	registerPermission(apiV1)
}

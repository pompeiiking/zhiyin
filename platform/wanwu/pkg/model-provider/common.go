package mp

// model type
const (
	ModelTypeLLM       = "llm"
	ModelTypeEmbedding = "embedding"
	ModelTypeRerank    = "rerank"
)

// model provider
const (
	ProviderOpenAICompatible = "OpenAI-API-compatible"
	ProviderYuanJing         = "YuanJing"
)

var (
	_callbackUrl string
)

func Init(callbackUrl string) {
	if _callbackUrl != "" {
		panic("model provider already init")
	}
	_callbackUrl = callbackUrl
}

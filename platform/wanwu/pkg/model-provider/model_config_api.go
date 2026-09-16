package mp

import (
	"context"
	"encoding/json"
	"fmt"

	mp_common "github.com/UnicomAI/wanwu/pkg/model-provider/mp-common"
	mp_openai_compatible "github.com/UnicomAI/wanwu/pkg/model-provider/mp-openai-compatible"
	mp_yuanjing "github.com/UnicomAI/wanwu/pkg/model-provider/mp-yuanjing"
)

type ILLM interface {
	ChatCompletions(ctx context.Context, req mp_common.ILLMReq, headers ...mp_common.Header) (mp_common.ILLMResp, <-chan mp_common.ILLMResp, error)
}

type IEmbedding interface {
	Embeddings(ctx context.Context, req mp_common.IEmbeddingReq, headers ...mp_common.Header) (mp_common.IEmbeddingResp, error)
}

type IRerank interface {
	Rerank(ctx context.Context, req mp_common.IRerankReq, headers ...mp_common.Header) (mp_common.IRerankResp, error)
}

// ToModelConfig 返回ILLM、IEmbedding或IRerank
func ToModelConfig(provider, modelType, cfg string) (interface{}, error) {
	if cfg == "" {
		return nil, nil
	}
	var ret interface{} // 前端需要的结构体
	switch provider {
	case ProviderOpenAICompatible:
		switch modelType {
		case ModelTypeLLM:
			ret = &mp_openai_compatible.LLM{}
		case ModelTypeRerank:
			ret = &mp_openai_compatible.Rerank{}
		case ModelTypeEmbedding:
			ret = &mp_openai_compatible.Embedding{}
		default:
			return nil, fmt.Errorf("invalid model type: %v", modelType)
		}
	case ProviderYuanJing:
		switch modelType {
		case ModelTypeLLM:
			ret = &mp_yuanjing.LLM{}
		case ModelTypeRerank:
			ret = &mp_yuanjing.Rerank{}
		case ModelTypeEmbedding:
			ret = &mp_yuanjing.Embedding{}
		default:
			return nil, fmt.Errorf("invalid model type: %v", modelType)
		}
	default:
		return nil, fmt.Errorf("invalid provider: %v", modelType)
	}

	if err := json.Unmarshal([]byte(cfg), ret); err != nil {
		return nil, fmt.Errorf("unmarshal model config err: %v", err)
	}
	return ret, nil
}

type ProviderModelConfig struct {
	ProviderYuanJing         ProviderModelByYuanjing         `json:"providerYuanJing"`
	ProviderOpenAICompatible ProviderModelByOpenAICompatible `json:"providerOpenAICompatible"`
}

type ProviderModelByOpenAICompatible struct {
	Llm       mp_openai_compatible.LLM       `json:"llm"`
	Rerank    mp_openai_compatible.Rerank    `json:"rerank"`
	Embedding mp_openai_compatible.Embedding `json:"embedding"`
}

type ProviderModelByYuanjing struct {
	Llm       mp_yuanjing.LLM       `json:"llm"`
	Rerank    mp_yuanjing.Rerank    `json:"rerank"`
	Embedding mp_yuanjing.Embedding `json:"embedding"`
}

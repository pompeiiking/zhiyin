package service

import (
	"fmt"
	"net/http"

	err_code "github.com/UnicomAI/wanwu/api/proto/err-code"
	model_service "github.com/UnicomAI/wanwu/api/proto/model-service"
	"github.com/UnicomAI/wanwu/internal/bff-service/config"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	grpc_util "github.com/UnicomAI/wanwu/pkg/grpc-util"
	"github.com/UnicomAI/wanwu/pkg/log"
	mp "github.com/UnicomAI/wanwu/pkg/model-provider"
	mp_common "github.com/UnicomAI/wanwu/pkg/model-provider/mp-common"
	"github.com/gin-gonic/gin"
)

func ModelChatCompletions(ctx *gin.Context, modelID string, req map[string]interface{}) {
	// modelInfo by modelID
	modelInfo, err := model.GetModelById(ctx.Request.Context(), &model_service.GetModelByIdReq{ModelId: modelID})
	if err != nil {
		gin_util.Response(ctx, nil, err)
		return
	}
	// llm config
	llm, err := mp.ToModelConfig(modelInfo.Provider, modelInfo.ModelType, modelInfo.ProviderConfig)
	if err != nil {
		gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFGeneral, fmt.Sprintf("model %v chat completions err: %v", modelInfo.ModelId, err)))
		return
	}
	iLLM, ok := llm.(mp.ILLM)
	if !ok {
		gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFGeneral, fmt.Sprintf("model %v chat completions err: invalid provider", modelInfo.ModelId)))
		return
	}
	// chat completions
	llmReq := mp_common.NewLLMReq(req)
	resp, sseCh, err := iLLM.ChatCompletions(ctx.Request.Context(), llmReq)
	if err != nil {
		gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFGeneral, fmt.Sprintf("model %v chat completions err: %v", modelInfo.ModelId, err)))
		return
	}
	// unary
	if !llmReq.Stream() {
		if data, ok := resp.Data(); ok {
			status := http.StatusOK
			ctx.Set(config.STATUS, status)
			ctx.Set(config.RESULT, resp.String())
			ctx.JSON(status, data)
			return
		}
		gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFGeneral, fmt.Sprintf("model %v chat completions err: invalid resp", modelInfo.ModelId)))
		return
	}
	// stream
	var answer string
	ctx.Header("Cache-Control", "no-cache")
	ctx.Header("Connection", "keep-alive")
	ctx.Header("Content-Type", "text/event-stream; charset=utf-8")
	for sseResp := range sseCh {
		if data, ok := sseResp.OpenAIResp(); ok {
			if len(data.Choices) > 0 && data.Choices[0].Delta != nil {
				answer = answer + data.Choices[0].Delta.Content
			}
		}
		if _, err = ctx.Writer.Write([]byte(fmt.Sprintf("%v\n", sseResp.String()))); err != nil {
			log.Errorf("model %v chat completions sse err: %v", modelInfo.ModelId, err)
		}
		ctx.Writer.Flush()
	}
	ctx.Set(config.STATUS, http.StatusOK)
	ctx.Set(config.RESULT, answer)
}

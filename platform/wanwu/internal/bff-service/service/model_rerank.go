package service

import (
	"fmt"
	"net/http"

	err_code "github.com/UnicomAI/wanwu/api/proto/err-code"
	model_service "github.com/UnicomAI/wanwu/api/proto/model-service"
	"github.com/UnicomAI/wanwu/internal/bff-service/config"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	grpc_util "github.com/UnicomAI/wanwu/pkg/grpc-util"
	mp "github.com/UnicomAI/wanwu/pkg/model-provider"
	mp_common "github.com/UnicomAI/wanwu/pkg/model-provider/mp-common"
	"github.com/gin-gonic/gin"
)

func ModelRerank(ctx *gin.Context, modelID string, req map[string]interface{}) {
	// modelInfo by modelID
	modelInfo, err := model.GetModelById(ctx.Request.Context(), &model_service.GetModelByIdReq{ModelId: modelID})
	if err != nil {
		gin_util.Response(ctx, nil, err)
		return
	}
	// rerank config
	rerank, err := mp.ToModelConfig(modelInfo.Provider, modelInfo.ModelType, modelInfo.ProviderConfig)
	if err != nil {
		gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFGeneral, fmt.Sprintf("model %v rerank err: %v", modelInfo.ModelId, err)))
		return
	}
	iRerank, ok := rerank.(mp.IRerank)
	if !ok {
		gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFGeneral, fmt.Sprintf("model %v rerank err: invalid provider", modelInfo.ModelId)))
		return
	}
	// rerank
	rerankReq := mp_common.NewRerankReq(req)
	resp, err := iRerank.Rerank(ctx.Request.Context(), rerankReq)
	if err != nil {
		gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFGeneral, fmt.Sprintf("model %v rerank err: %v", modelInfo.ModelId, err)))
		return
	}
	if data, ok := resp.Data(); ok {
		status := http.StatusOK
		ctx.Set(config.STATUS, status)
		//ctx.Set(config.RESULT, resp.String())
		ctx.JSON(status, data)
		return
	}
	gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFGeneral, fmt.Sprintf("model %v rerank err: invalid resp", modelInfo.ModelId)))
}

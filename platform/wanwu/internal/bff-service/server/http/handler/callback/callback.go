package callback

import (
	"encoding/json"
	"fmt"

	err_code "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	"github.com/UnicomAI/wanwu/internal/bff-service/service"
	grpc_util "github.com/UnicomAI/wanwu/pkg/grpc-util"
	mp "github.com/UnicomAI/wanwu/pkg/model-provider"
	"github.com/gin-gonic/gin"
)

//	@title		AI Agent Productivity Platform - Callback
//	@version	v0.0.1

//	@BasePath	/callback/v1

// GetModelById
//
//	@Tags		callback
//	@Summary	根据ModelId获取模型
//	@Accept		json
//	@Produce	json
//	@Param		modelId	path		string	true	"模型ID"
//	@Success	200		{object}	response.Response{data=response.ModelInfo}
//	@Router		/model/{modelId} [get]
func GetModelById(ctx *gin.Context) {
	modelId := ctx.Param("modelId")
	resp, err := service.GetModelById(ctx, &request.GetModelByIdRequest{ModelId: modelId})
	// 替换callback返回的模型中的apiKey/endpointUrl信息
	if resp != nil && resp.Config != nil {
		cfg := make(map[string]interface{})
		b, err := json.Marshal(resp.Config)
		if err != nil {
			gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFGeneral, fmt.Sprintf("model %v marshal config err: %v", modelId, err)))
			return
		}
		if err = json.Unmarshal(b, &cfg); err != nil {
			gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFGeneral, fmt.Sprintf("model %v unmarshal config err: %v", modelId, err)))
			return
		}
		// 替换apiKey, endpointUrl
		cfg["apiKey"] = "useless-api-key"
		endpoint := mp.ToModelEndpoint(resp.ModelId, resp.Model)
		for k, v := range endpoint {
			if k == "model_url" {
				cfg["endpointUrl"] = v
				break
			}
		}
		// 替换Config
		resp.Config = cfg
	}
	gin_util.Response(ctx, resp, err)
}

// ModelChatCompletions
//
//	@Tags		callback
//	@Summary	Model Chat Completions
//	@Accept		json
//	@Produce	json
//	@Param		modelId	path		string					true	"模型ID"
//	@Param		data	body		map[string]interface{}	true	"请求参数"
//	@Success	200		{object}	response.Response{}
//	@Router		/model/{modelId}/chat/completions [post]
func ModelChatCompletions(ctx *gin.Context) {
	body, ok := ctx.Get(gin.BodyBytesKey)
	if !ok {
		gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFInvalidArg, "invalid body"))
		return
	}
	data := make(map[string]interface{})
	if err := json.Unmarshal(body.([]byte), &data); err != nil {
		gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFInvalidArg, err.Error()))
		return
	}
	service.ModelChatCompletions(ctx, ctx.Param("modelId"), data)
}

// ModelEmbeddings
//
//	@Tags		callback
//	@Summary	Model Embeddings
//	@Accept		json
//	@Produce	json
//	@Param		modelId	path		string					true	"模型ID"
//	@Param		data	body		map[string]interface{}	true	"请求参数"
//	@Success	200		{object}	response.Response{}
//	@Router		/model/{modelId}/embeddings [post]
func ModelEmbeddings(ctx *gin.Context) {
	body, ok := ctx.Get(gin.BodyBytesKey)
	if !ok {
		gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFInvalidArg, "invalid body"))
		return
	}
	data := make(map[string]interface{})
	if err := json.Unmarshal(body.([]byte), &data); err != nil {
		gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFInvalidArg, err.Error()))
		return
	}
	service.ModelEmbeddings(ctx, ctx.Param("modelId"), data)
}

// ModelRerank
//
//	@Tags		callback
//	@Summary	Model Rerank
//	@Accept		json
//	@Produce	json
//	@Param		modelId	path		string					true	"模型ID"
//	@Param		data	body		map[string]interface{}	true	"请求参数"
//	@Success	200		{object}	response.Response{}
//	@Router		/model/{modelId}/rerank [post]
func ModelRerank(ctx *gin.Context) {
	body, ok := ctx.Get(gin.BodyBytesKey)
	if !ok {
		gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFInvalidArg, "invalid body"))
		return
	}
	data := make(map[string]interface{})
	if err := json.Unmarshal(body.([]byte), &data); err != nil {
		gin_util.Response(ctx, nil, grpc_util.ErrorStatus(err_code.Code_BFFInvalidArg, err.Error()))
		return
	}
	service.ModelRerank(ctx, ctx.Param("modelId"), data)
}

// UpdateDocStatus
//
//	@Tags			callback
//	@Summary		更新文档状态（模型扩展调用）
//	@Description	更新文档状态（模型扩展调用）
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.CallbackUpdateDocStatusReq	true	"更新文档状态请求参数"
//	@Success		200		{object}	response.Response
//	@Router			/api/docstatus [post]
func UpdateDocStatus(ctx *gin.Context) {
	var req request.CallbackUpdateDocStatusReq
	if !gin_util.Bind(ctx, &req) {
		return
	}
	err := service.UpdateDocStatus(ctx, &req)
	gin_util.Response(ctx, nil, err)
}

// DocStatusInit
//
//	@Tags			callback
//	@Summary		将正在解析的文档设置为解析失败
//	@Description	将正在解析的文档设置为解析失败
//	@Accept			json
//	@Produce		json
//	@Success		200	{object}	response.Response{}
//	@Router			/api/doc_status_init [get]
func DocStatusInit(ctx *gin.Context) {
	resp, err := service.DocStatusInit(ctx, "", "")
	gin_util.Response(ctx, resp, err)
}

// GetDeployInfo
//
//	@Tags			callback
//	@Summary		获取Maas平台部署信息（模型扩展调用）
//	@Description	获取Maas平台部署信息（模型扩展调用）
//	@Accept			json
//	@Produce		json
//	@Success		200	{object}	response.Response{}
//	@Router			/api/deploy/info [get]
func GetDeployInfo(ctx *gin.Context) {
	resp, err := service.GetDeployInfo(ctx)
	gin_util.Response(ctx, resp, err)
}

// SelectKnowledgeInfoByName
//
//	@Tags			callback
//	@Summary		获取Maas平台知识库信息（模型扩展调用）
//	@Description	获取Maas平台知识库信息（模型扩展调用）
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.SearchKnowledgeInfoReq	true	"根据知识库名称请求参数"
//	@Success		200		{object}	response.Response{}
//	@Router			/api/category/info [get]
func SelectKnowledgeInfoByName(ctx *gin.Context) {
	var req request.SearchKnowledgeInfoReq
	if !gin_util.BindQuery(ctx, &req) {
		return
	}
	resp, err := service.SelectKnowledgeInfoByName(ctx, req.UserId, req.OrgId, &req)
	gin_util.Response(ctx, resp, err)
}

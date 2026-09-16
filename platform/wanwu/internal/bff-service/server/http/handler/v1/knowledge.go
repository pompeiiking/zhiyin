package v1

import (
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	"github.com/UnicomAI/wanwu/internal/bff-service/service"
	"github.com/gin-gonic/gin"
)

// GetKnowledgeSelect
//
//	@Tags			knowledge
//	@Summary		查询知识库列表
//	@Description	查询知识库列表
//	@Security		JWT
//	@Accept			json
//	@Param			data	body	request.KnowledgeSelectReq	true	"查询知识库列表"
//	@Produce		json
//	@Success		200	{object}	response.Response{data=response.KnowledgeListResp}
//	@Router			/knowledge/select [get]
func GetKnowledgeSelect(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.KnowledgeSelectReq
	if !gin_util.BindQuery(ctx, &req) {
		return
	}
	resp, err := service.SelectKnowledgeList(ctx, userId, orgId, &req)
	gin_util.Response(ctx, resp, err)
}

// CreateKnowledge
//
//	@Tags			knowledge
//	@Summary		创建知识库
//	@Description	创建知识库
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.CreateKnowledgeReq	true	"创建知识库请求参数"
//	@Success		200		{object}	response.Response{data=[]response.CreateKnowledgeResp}
//	@Router			/knowledge [post]
func CreateKnowledge(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.CreateKnowledgeReq
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.CreateKnowledge(ctx, userId, orgId, &req)
	gin_util.Response(ctx, resp, err)
}

// UpdateKnowledge
//
//	@Tags			knowledge
//	@Summary		修改知识库（文档分类）
//	@Description	修改知识库（文档分类）
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.UpdateKnowledgeReq	true	"修改知识库请求参数"
//	@Success		200		{object}	response.Response
//	@Router			/knowledge [put]
func UpdateKnowledge(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.UpdateKnowledgeReq
	if !gin_util.Bind(ctx, &req) {
		return
	}
	err := service.UpdateKnowledge(ctx, userId, orgId, &req)
	gin_util.Response(ctx, nil, err)
}

// DeleteKnowledge
//
//	@Tags			knowledge
//	@Summary		删除知识库
//	@Description	删除知识库
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.DeleteKnowledge	true	"删除知识库请求参数"
//	@Success		200		{object}	response.Response
//	@Router			/knowledge [delete]
func DeleteKnowledge(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.DeleteKnowledge
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.DeleteKnowledge(ctx, userId, orgId, &req)
	gin_util.Response(ctx, resp, err)
}

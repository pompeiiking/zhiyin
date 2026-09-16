package v1

import (
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	"github.com/UnicomAI/wanwu/internal/bff-service/service"
	"github.com/gin-gonic/gin"
)

// GetDocList
//
//	@Tags			knowledge
//	@Summary		获取文档列表
//	@Description	获取知识库文档列表，不展示状态为无效（-1）的文档数据
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.DocListReq	true	"文档列表查询请求参数"
//	@Success		200		{object}	response.PageResult{list=[]response.ListDocResp}
//	@Router			/knowledge/doc/list [get]
func GetDocList(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.DocListReq
	if !gin_util.BindQuery(ctx, &req) {
		return
	}
	resp, err := service.GetDocList(ctx, userId, orgId, &req)
	gin_util.Response(ctx, resp, err)
}

// ImportDoc
//
//	@Tags			knowledge
//	@Summary		上传文档
//	@Description	上传文档
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.DocImportReq	true	"文档上传请求参数"
//	@Success		200		{object}	response.Response
//	@Router			/knowledge/doc/import [post]
func ImportDoc(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.DocImportReq
	if !gin_util.Bind(ctx, &req) {
		return
	}
	err := service.ImportDoc(ctx, userId, orgId, &req)
	gin_util.Response(ctx, nil, err)
}

// DeleteDoc
//
//	@Tags			knowledge
//	@Summary		删除文档
//	@Description	删除文档
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.DeleteDocReq	true	"删除文档请求参数"
//	@Success		200		{object}	response.Response
//	@Router			/knowledge/doc [delete]
func DeleteDoc(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.DeleteDocReq
	if !gin_util.Bind(ctx, &req) {
		return
	}
	err := service.DeleteDoc(ctx, userId, orgId, &req)
	gin_util.Response(ctx, nil, err)
}

// GetDocImportTip
//
//	@Tags			knowledge
//	@Summary		获取知识库异步上传任务提示
//	@Description	获取知识库异步上传任务提示：有正在执行的异步上传任务/最近一次上传任务的失败信息
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.QueryKnowledgeReq	true	"获取知识库异步上传任务提示请求参数"
//	@Success		200		{object}	response.Response(data=response.DocImportTipResp)
//	@Router			/knowledge/doc/import/tip [get]
func GetDocImportTip(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.QueryKnowledgeReq
	if !gin_util.BindQuery(ctx, &req) {
		return
	}
	resp, err := service.GetDocImportTip(ctx, userId, orgId, &req)
	gin_util.Response(ctx, resp, err)
}

// GetDocSegmentList
//
//	@Tags			knowledge
//	@Summary		获取文档切分结果
//	@Description	获取文档切分结果
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.DocSegmentListReq	true	"获取文档切分结果请求参数"
//	@Success		200		{object}	response.Response{data=response.DocSegmentResp}
//	@Router			/knowledge/doc/segment/list [get]
func GetDocSegmentList(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.DocSegmentListReq
	if !gin_util.BindQuery(ctx, &req) {
		return
	}
	resp, err := service.GetDocSegmentList(ctx, userId, orgId, &req)
	gin_util.Response(ctx, resp, err)
}

// UpdateDocSegmentStatus
//
//	@Tags			knowledge
//	@Summary		更新文档切片启用状态
//	@Description	更新文档切片启用状态
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.UpdateDocSegmentStatusReq	true	"更新文档切片启用状态请求参数"
//	@Success		200		{object}	response.Response
//	@Router			/knowledge/doc/segment/status/update [post]
func UpdateDocSegmentStatus(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.UpdateDocSegmentStatusReq
	if !gin_util.Bind(ctx, &req) {
		return
	}
	err := service.UpdateDocSegmentStatus(ctx, userId, orgId, &req)
	gin_util.Response(ctx, nil, err)
}

// AnalysisDocUrl
//
//	@Tags			knowledge
//	@Summary		解析url
//	@Description	解析url
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.AnalysisUrlDocReq	true	"解析url请求参数"
//	@Success		200		{object}	response.Response{data=response.AnalysisDocUrlResp}
//	@Router			/knowledge/doc/url/analysis [post]
func AnalysisDocUrl(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.AnalysisUrlDocReq
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.AnalysisDocUrl(ctx, userId, orgId, &req)
	gin_util.Response(ctx, resp, err)
}

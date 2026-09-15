package v1

import (
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	"github.com/UnicomAI/wanwu/internal/bff-service/service"
	"github.com/UnicomAI/wanwu/pkg/constant"
	"github.com/gin-gonic/gin"
)

// AssistantCreate
//
//	@Tags			agent
//	@Summary		创建智能体
//	@Description	创建智能体，填写基本信息，创建完成为草稿状态
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.AppBriefConfig	true	"智能体基本信息"
//	@Success		200		{object}	response.Response
//	@Router			/assistant [post]
func AssistantCreate(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.AppBriefConfig
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.AssistantCreate(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// AssistantUpdate
//
//	@Tags			agent
//	@Summary		修改智能体基本信息
//	@Description	修改智能体基本信息，名称，头像，简介
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.AssistantBrief	true	"智能体基本信息参数"
//	@Success		200		{object}	response.Response
//	@Router			/assistant [put]
func AssistantUpdate(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.AssistantBrief
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.AssistantUpdate(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// AssistantDelete
//
//	@Tags			agent
//	@Summary		删除智能体
//	@Description	删除智能体
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.AssistantDeleteRequest	true	"智能体删除参数"
//	@Success		200		{object}	response.Response
//	@Router			/assistant [delete]
func AssistantDelete(ctx *gin.Context) {
	deleteAssistant(ctx, service.DeleteAppSpaceApp)
}

func deleteAssistant(ctx *gin.Context, remove func(*gin.Context, string, string, string, string) error) {
	var req request.AssistantDeleteRequest
	if !gin_util.Bind(ctx, &req) {
		return
	}
	err := remove(ctx, getUserID(ctx), getOrgID(ctx), req.AssistantId, constant.AppTypeAgent)
	gin_util.Response(ctx, nil, err)
}

// AssistantConfigUpdate
//
//	@Tags			agent
//	@Summary		修改智能体配置信息
//	@Description	修改智能体配置信息，模型配置，知识库配置等等
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.AssistantConfig	true	"智能体配置信息参数"
//	@Success		200		{object}	response.Response
//	@Router			/assistant/config [put]
func AssistantConfigUpdate(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.AssistantConfig
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.AssistantConfigUpdate(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// GetAssistantInfo
//
//	@Tags			agent
//	@Summary		查看智能体详情
//	@Description	查看智能体详情
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			assistantId	query		string	true	"智能体id"
//	@Success		200			{object}	response.Response{data=response.Assistant}
//	@Router			/assistant [get]
func GetAssistantInfo(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.AssistantIdRequest
	if !gin_util.BindQuery(ctx, &req) {
		return
	}
	resp, err := service.GetAssistantInfo(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// AssistantWorkFlowCreate
//
//	@Tags			agent
//	@Summary		添加工作流
//	@Description	为智能体绑定已发布的工作流
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.WorkFlowAddRequest	true	"工作流新增参数"
//	@Success		200		{object}	response.Response
//	@Router			/assistant/workflow [post]
func AssistantWorkFlowCreate(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.WorkFlowAddRequest
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.AssistantWorkFlowCreate(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// AssistantWorkFlowDelete
//
//	@Tags			agent
//	@Summary		删除工作流
//	@Description	为智能体解绑工作流
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.WorkFlowIdRequest	true	"工作流id"
//	@Success		200		{object}	response.Response
//	@Router			/assistant/workflow [delete]
func AssistantWorkFlowDelete(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.WorkFlowIdRequest
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.AssistantWorkFlowDelete(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// AssistantWorkFlowEnableSwitch
//
//	@Tags			agent
//	@Summary		启用/停用工作流
//	@Description	修改智能体绑定的工作流的启用状态
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.WorkFlowIdRequest	true	"工作流id"
//	@Success		200		{object}	response.Response
//	@Router			/assistant/workflow/enable [put]
func AssistantWorkFlowEnableSwitch(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.WorkFlowIdRequest
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.AssistantWorkFlowEnableSwitch(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// AssistantActionCreate
//
//	@Tags			agent
//	@Summary		添加action
//	@Description	为智能体绑定action
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.ActionAddRequest	true	"action新增参数"
//	@Success		200		{object}	response.Response
//	@Router			/assistant/action [post]
func AssistantActionCreate(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.ActionAddRequest
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.AssistantActionCreate(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// AssistantActionDelete
//
//	@Tags			agent
//	@Summary		删除action
//	@Description	为智能体解绑action
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.ActionIdRequest	true	"action的id"
//	@Success		200		{object}	response.Response
//	@Router			/assistant/action [delete]
func AssistantActionDelete(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.ActionIdRequest
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.AssistantActionDelete(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// AssistantActionUpdate
//
//	@Tags			agent
//	@Summary		编辑action
//	@Description	为智能体修改action参数
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.ActionUpdateRequest	true	"action编辑参数"
//	@Success		200		{object}	response.Response
//	@Router			/assistant/action [put]
func AssistantActionUpdate(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.ActionUpdateRequest
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.AssistantActionUpdate(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// GetAssistantActionInfo
//
//	@Tags			agent
//	@Summary		查看智能体action详情
//	@Description	查看智能体action详情
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			actionId	query		string	true	"action的id"
//	@Success		200			{object}	response.Response{data=response.Action}
//	@Router			/assistant/action [get]
func GetAssistantActionInfo(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.ActionIdRequest
	if !gin_util.BindQuery(ctx, &req) {
		return
	}
	resp, err := service.GetAssistantActionInfo(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// AssistantActionEnableSwitch
//
//	@Tags			agent
//	@Summary		启用/停用action
//	@Description	修改智能体绑定的action的启用状态
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.ActionIdRequest	true	"action的id"
//	@Success		200		{object}	response.Response
//	@Router			/assistant/action/enable [put]
func AssistantActionEnableSwitch(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.ActionIdRequest
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.AssistantActionEnableSwitch(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// ConversationCreate
//
//	@Tags			agent
//	@Summary		创建智能体对话
//	@Description	创建智能体对话
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.ConversationCreateRequest	true	"智能体对话创建参数"
//	@Success		200		{object}	response.Response{data=response.ConversationCreateResp}
//	@Router			/assistant/conversation [post]
func ConversationCreate(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.ConversationCreateRequest
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.ConversationCreate(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// ConversationDelete
//
//	@Tags			agent
//	@Summary		删除智能体对话
//	@Description	删除智能体对话
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.ConversationIdRequest	true	"智能体对话的id"
//	@Success		200		{object}	response.Response
//	@Router			/assistant/conversation [delete]
func ConversationDelete(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.ConversationIdRequest
	if !gin_util.Bind(ctx, &req) {
		return
	}
	resp, err := service.ConversationDelete(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// GetConversationList
//
//	@Tags			agent
//	@Summary		智能体对话列表
//	@Description	智能体对话列表
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			assistantId	query		string	true	"智能体id"
//	@Param			pageNo		query		int		true	"页面编号，从1开始"
//	@Param			pageSize	query		int		true	"单页数量，从1开始"
//	@Success		200			{object}	response.Response{data=response.PageResult{list=[]response.ConversationInfo}}
//	@Router			/assistant/conversation/list [get]
func GetConversationList(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.ConversationGetListRequest
	if !gin_util.BindQuery(ctx, &req) {
		return
	}
	resp, err := service.GetConversationList(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// GetConversationDetailList
//
//	@Tags			agent
//	@Summary		智能体对话详情历史列表
//	@Description	智能体对话详情历史列表
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			conversationId	query		string	true	"智能体对话id"
//	@Param			pageNo			query		int		true	"页面编号，从1开始"
//	@Param			pageSize		query		int		true	"单页数量，从1开始"
//	@Success		200				{object}	response.Response{data=response.PageResult{list=[]response.ConversationDetailInfo}}
//	@Router			/assistant/conversation/detail [get]
func GetConversationDetailList(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.ConversationGetDetailListRequest
	if !gin_util.BindQuery(ctx, &req) {
		return
	}
	resp, err := service.GetConversationDetailList(ctx, userId, orgId, req)
	gin_util.Response(ctx, resp, err)
}

// AssistantConversionStream
//
//	@Tags			agent
//	@Summary		智能体流式问答
//	@Description	智能体流式问答
//	@Security		JWT
//	@Accept			json
//	@Produce		json
//	@Param			data	body		request.ConversionStreamRequest	true	"智能体流式问答参数"
//	@Success		200		{object}	response.Response
//	@Router			/assistant/stream [post]
func AssistantConversionStream(ctx *gin.Context) {
	userId, orgId := getUserID(ctx), getOrgID(ctx)
	var req request.ConversionStreamRequest
	if !gin_util.Bind(ctx, &req) {
		return
	}
	if err := service.AssistantConversionStream(ctx, userId, orgId, req); err != nil {
		gin_util.Response(ctx, nil, err)
	}
}

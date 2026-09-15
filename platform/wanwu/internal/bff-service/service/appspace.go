package service

import (
	"sort"

	app_service "github.com/UnicomAI/wanwu/api/proto/app-service"
	assistant_service "github.com/UnicomAI/wanwu/api/proto/assistant-service"
	rag_service "github.com/UnicomAI/wanwu/api/proto/rag-service"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/response"
	"github.com/UnicomAI/wanwu/pkg/constant"
	"github.com/gin-gonic/gin"
)

const (
	successCode = 0
)

func DeleteAppSpaceApp(ctx *gin.Context, userId, orgId, appId, appType string) error {
	// delete publish app
	_, err := app.DeleteApp(ctx.Request.Context(), &app_service.DeleteAppReq{
		AppId:   appId,
		AppType: appType,
	})
	if err != nil {
		return err
	}
	// delete app
	switch appType {
	case constant.AppTypeRag:
		_, err = rag.DeleteRag(ctx.Request.Context(), &rag_service.RagDeleteReq{
			RagId: appId,
		})
	case constant.AppTypeAgent:
		_, err = assistant.AssistantDelete(ctx.Request.Context(), &assistant_service.AssistantDeleteReq{
			AssistantId: appId,
		})
	case constant.AppTypeWorkflow:
		err = DeleteWorkFlow(ctx, userId, orgId, appId)
	}
	return err
}

func GetAppSpaceAppList(ctx *gin.Context, userId, orgId, name, appType string) (*response.ListResult, error) {
	var ret []response.AppBriefInfo
	if appType == "" || appType == constant.AppTypeRag {
		resp, err := rag.ListRag(ctx.Request.Context(), &rag_service.RagListReq{
			Name: name,
			Identity: &rag_service.Identity{
				UserId: userId,
				OrgId:  orgId,
			},
		})
		if err != nil {
			return nil, err
		}
		for _, ragInfo := range resp.RagInfos {
			ret = append(ret, appBriefProto2Model(ctx, ragInfo))
		}
	}
	if appType == "" || appType == constant.AppTypeAgent {
		resp, err := assistant.GetAssistantListMyAll(ctx.Request.Context(), &assistant_service.GetAssistantListMyAllReq{
			Name: name,
			Identity: &assistant_service.Identity{
				UserId: userId,
				OrgId:  orgId,
			},
		})
		if err != nil {
			return nil, err
		}
		for _, assistantInfo := range resp.AssistantInfos {
			ret = append(ret, appBriefProto2Model(ctx, assistantInfo))
		}
	}
	var appIds []string
	for _, appInfo := range ret {
		appIds = append(appIds, appInfo.AppId)
	}
	AppInfos, err := app.GetAppListByIds(ctx, &app_service.GetAppListByIdsReq{
		AppIdsList: appIds,
	})
	if err != nil {
		return nil, err
	}
	publishTypeMap := make(map[string]string, len(AppInfos.Infos))
	for _, appInfo := range AppInfos.Infos {
		publishTypeMap[appInfo.AppId] = appInfo.PublishType
	}
	for idx, appInfo := range ret {
		if publishType, ok := publishTypeMap[appInfo.AppId]; ok {
			ret[idx].PublishType = publishType
		}
	}

	if appType == "" || appType == constant.AppTypeWorkflow {
		resp, err := ListWorkFlow(ctx, userId, orgId, name)
		if err != nil {
			return nil, err
		}
		for _, workflowInfo := range resp.List {
			ret = append(ret, workflowInfo2Model(workflowInfo))
		}
	}
	sort.SliceStable(ret, func(i, j int) bool {
		return ret[i].UpdatedAt > ret[j].UpdatedAt
	})

	return &response.ListResult{
		List:  ret,
		Total: int64(len(ret)),
	}, nil
}

func PublishApp(ctx *gin.Context, userId, orgId string, req request.PublishAppRequest) error {
	_, err := app.PublishApp(ctx.Request.Context(), &app_service.PublishAppReq{
		AppId:       req.AppId,
		AppType:     req.AppType,
		PublishType: req.PublishType,
		UserId:      userId,
		OrgId:       orgId,
	})
	return err
}

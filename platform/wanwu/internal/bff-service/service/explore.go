package service

import (
	"sort"

	app_service "github.com/UnicomAI/wanwu/api/proto/app-service"
	assistant_service "github.com/UnicomAI/wanwu/api/proto/assistant-service"
	"github.com/UnicomAI/wanwu/api/proto/common"
	rag_service "github.com/UnicomAI/wanwu/api/proto/rag-service"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/response"
	"github.com/UnicomAI/wanwu/pkg/constant"
	"github.com/UnicomAI/wanwu/pkg/util"
	"github.com/gin-gonic/gin"
)

func GetExplorationAppList(ctx *gin.Context, userId string, req request.GetExplorationAppListRequest) (*response.ListResult, error) {
	explorationApp, err := app.GetExplorationAppList(ctx.Request.Context(), &app_service.GetExplorationAppListReq{
		Name:       req.Name,
		AppType:    req.AppType,
		SearchType: req.SearchType,
		UserId:     userId,
	})
	if err != nil {
		return nil, err
	}
	rags, err := explorerationFilterRag(ctx, explorationApp.Infos)
	if err != nil {
		return nil, err
	}
	agents, err := explorerationFilterAgent(ctx, explorationApp.Infos)
	if err != nil {
		return nil, err
	}
	apps := append(rags, agents...)
	sort.SliceStable(apps, func(i, j int) bool {
		return apps[i].CreatedAt > apps[j].CreatedAt
	})
	return &response.ListResult{
		List:  apps,
		Total: explorationApp.Total,
	}, nil
}

func ChangeExplorationAppFavorite(ctx *gin.Context, userId, orgId string, req request.ChangeExplorationAppFavoriteRequest) error {
	_, err := app.ChangeExplorationAppFavorite(ctx.Request.Context(), &app_service.ChangeExplorationAppFavoriteReq{
		AppId:      req.AppId,
		AppType:    req.AppType,
		UserId:     userId,
		OrgId:      orgId,
		IsFavorite: req.IsFavorite,
	})
	return err
}

func AddAppHistoryRecord(ctx *gin.Context, userId, appId, appType string) error {
	if _, err := app.RecordAppHistory(ctx, &app_service.RecordAppHistoryReq{
		UserId:  userId,
		AppId:   appId,
		AppType: appType,
	}); err != nil {
		return err
	}
	return nil

}

// --- internal ---

func explorerationFilterRag(ctx *gin.Context, explorationApp []*app_service.ExplorationAppInfo) ([]*response.ExplorationAppInfo, error) {
	// 首先收集所有rag类型的appId
	var ids []string
	for _, info := range explorationApp {
		if info.AppType == constant.AppTypeRag {
			ids = append(ids, info.AppId)
		}
	}
	if len(ids) == 0 {
		return nil, nil
	}
	// 获取rag详情
	ragList, err := rag.GetRagByIds(ctx.Request.Context(), &rag_service.GetRagByIdsReq{RagIdList: ids})
	if err != nil {
		return nil, err
	}
	var retAppList []*response.ExplorationAppInfo
	for _, id := range ids {
		var foundRag *common.AppBrief
		for _, ragInfo := range ragList.RagInfos {
			if ragInfo.AppId == id {
				foundRag = ragInfo
				break
			}
		}
		if foundRag == nil {
			continue
		}
		for _, expApp := range explorationApp {
			if expApp.AppId == id {
				appInfo := &response.ExplorationAppInfo{
					AppBriefInfo: appBriefProto2Model(ctx, foundRag),
				}
				appInfo.CreatedAt = util.Time2Str(expApp.CreatedAt)
				appInfo.UpdatedAt = util.Time2Str(expApp.UpdatedAt)
				appInfo.PublishType = expApp.PublishType
				appInfo.IsFavorite = expApp.IsFavorite
				retAppList = append(retAppList, appInfo)
				break
			}
		}
	}
	return retAppList, nil
}

func explorerationFilterAgent(ctx *gin.Context, apps []*app_service.ExplorationAppInfo) ([]*response.ExplorationAppInfo, error) {
	// 首先收集所有agent类型的appId
	var ids []string
	for _, info := range apps {
		if info.AppType == constant.AppTypeAgent {
			ids = append(ids, info.AppId)
		}
	}
	if len(ids) == 0 {
		return nil, nil
	}
	// 获取agent详情
	agentList, err := assistant.GetAssistantByIds(ctx.Request.Context(), &assistant_service.GetAssistantByIdsReq{AssistantIdList: ids})
	if err != nil {
		return nil, err
	}
	var retAppList []*response.ExplorationAppInfo
	for _, id := range ids {
		var foundAgent *common.AppBrief
		for _, ragInfo := range agentList.AssistantInfos {
			if ragInfo.AppId == id {
				foundAgent = ragInfo
				break
			}
		}
		if foundAgent == nil {
			continue
		}
		for _, expApp := range apps {
			if expApp.AppId == id {
				appInfo := &response.ExplorationAppInfo{
					AppBriefInfo: appBriefProto2Model(ctx, foundAgent),
				}
				appInfo.CreatedAt = util.Time2Str(expApp.CreatedAt)
				appInfo.UpdatedAt = util.Time2Str(expApp.UpdatedAt)
				appInfo.PublishType = expApp.PublishType
				appInfo.IsFavorite = expApp.IsFavorite
				retAppList = append(retAppList, appInfo)
				break
			}
		}
	}
	return retAppList, nil
}

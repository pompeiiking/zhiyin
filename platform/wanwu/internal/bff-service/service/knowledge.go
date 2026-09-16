package service

import (
	"strconv"

	knowledgebase_service "github.com/UnicomAI/wanwu/api/proto/knowledgebase-service"
	"github.com/UnicomAI/wanwu/internal/bff-service/config"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/response"
	"github.com/gin-gonic/gin"
)

// SelectKnowledgeList 查询知识库列表，主要根据userId 查询用户所有知识库
func SelectKnowledgeList(ctx *gin.Context, userId, orgId string, req *request.KnowledgeSelectReq) (*response.KnowledgeListResp, error) {
	resp, err := knowledgeBase.SelectKnowledgeList(ctx.Request.Context(), &knowledgebase_service.KnowledgeSelectReq{
		UserId: userId,
		OrgId:  orgId,
		Name:   req.Name,
	})
	if err != nil {
		return nil, err
	}
	return buildKnowledgeInfoList(resp), nil
}

// SelectKnowledgeInfoByName 根据知识库名称查询知识库信息
func SelectKnowledgeInfoByName(ctx *gin.Context, userId, orgId string, r *request.SearchKnowledgeInfoReq) (interface{}, error) {
	resp, err := knowledgeBase.SelectKnowledgeDetailByName(ctx.Request.Context(), &knowledgebase_service.KnowledgeDetailSelectReq{
		UserId:        userId,
		OrgId:         orgId,
		KnowledgeName: r.KnowledgeName,
	})
	if err != nil {
		return nil, err
	}
	return map[string]string{
		"categoryId": resp.KnowledgeId,
	}, nil
}

// GetDeployInfo 查询部署信息
func GetDeployInfo(ctx *gin.Context) (interface{}, error) {
	cfgServer := config.Cfg().Server
	return map[string]string{
		"massAccessIp":   cfgServer.ExternalIP,
		"massAccessPort": strconv.Itoa(cfgServer.ExternalPort),
		"webBaseUrl":     cfgServer.WebBaseUrl + "/minio/download/api/",
	}, nil
}

// CreateKnowledge 创建知识库
func CreateKnowledge(ctx *gin.Context, userId, orgId string, r *request.CreateKnowledgeReq) (*response.CreateKnowledgeResp, error) {
	resp, err := knowledgeBase.CreateKnowledge(ctx.Request.Context(), &knowledgebase_service.CreateKnowledgeReq{
		Name:        r.Name,
		Description: r.Description,
		UserId:      userId,
		OrgId:       orgId,
		EmbeddingModelInfo: &knowledgebase_service.EmbeddingModelInfo{
			ModelId: r.EmbeddingModel.ModelId,
		},
	})
	if err != nil {
		return nil, err
	}
	return &response.CreateKnowledgeResp{KnowledgeId: resp.KnowledgeId}, nil
}

// UpdateKnowledge 更新知识库
func UpdateKnowledge(ctx *gin.Context, userId, orgId string, r *request.UpdateKnowledgeReq) error {
	_, err := knowledgeBase.UpdateKnowledge(ctx.Request.Context(), &knowledgebase_service.UpdateKnowledgeReq{
		KnowledgeId: r.KnowledgeId,
		Name:        r.Name,
		Description: r.Description,
		UserId:      userId,
		OrgId:       orgId,
	})
	return err
}

// DeleteKnowledge 删除知识库
func DeleteKnowledge(ctx *gin.Context, userId, orgId string, r *request.DeleteKnowledge) (interface{}, error) {
	resp, err := knowledgeBase.DeleteKnowledge(ctx.Request.Context(), &knowledgebase_service.DeleteKnowledgeReq{
		KnowledgeId: r.KnowledgeId,
		UserId:      userId,
		OrgId:       orgId,
	})
	if err != nil {
		return nil, err
	}
	return resp, nil
}

// buildKnowledgeInfoList 构造知识库列表结果
func buildKnowledgeInfoList(knowledgeListResp *knowledgebase_service.KnowledgeSelectListResp) *response.KnowledgeListResp {
	if knowledgeListResp == nil || len(knowledgeListResp.KnowledgeList) == 0 {
		return &response.KnowledgeListResp{}
	}
	var list []*response.KnowledgeInfo
	for _, knowledge := range knowledgeListResp.KnowledgeList {
		list = append(list, &response.KnowledgeInfo{
			KnowledgeId: knowledge.KnowledgeId,
			Name:        knowledge.Name,
			Description: knowledge.Description,
			DocCount:    int(knowledge.DocCount),
			EmbeddingModelInfo: &response.EmbeddingModelInfo{
				ModelId: knowledge.EmbeddingModelInfo.ModelId,
			},
		})
	}
	return &response.KnowledgeListResp{
		KnowledgeList: list,
	}
}

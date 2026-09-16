package service

import (
	"fmt"
	err_code "github.com/UnicomAI/wanwu/api/proto/err-code"
	model_service "github.com/UnicomAI/wanwu/api/proto/model-service"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/response"
	grpc_util "github.com/UnicomAI/wanwu/pkg/grpc-util"
	mp "github.com/UnicomAI/wanwu/pkg/model-provider"
	"github.com/UnicomAI/wanwu/pkg/util"
	"github.com/gin-gonic/gin"
)

func ImportModel(ctx *gin.Context, userId, orgId string, req *request.ImportOrUpdateModelRequest) error {
	clientReq, err := parseImportAndUpdateClientReq(userId, orgId, req)
	if err != nil {
		return err
	}
	_, err = model.ImportModel(ctx, clientReq)
	if err != nil {
		return err
	}
	return nil
}

func UpdateModel(ctx *gin.Context, userId, orgId string, req *request.ImportOrUpdateModelRequest) error {
	if req.ModelId == "" {
		return grpc_util.ErrorStatus(err_code.Code_BFFInvalidArg, "modelId cannot be empty")
	}
	clientReq, err := parseImportAndUpdateClientReq(userId, orgId, req)
	if err != nil {
		return err
	}
	_, err = model.UpdateModel(ctx, clientReq)
	if err != nil {
		return err
	}
	return nil
}

func DeleteModel(ctx *gin.Context, userId, orgId string, req *request.DeleteModelRequest) error {
	_, err := model.DeleteModel(ctx, &model_service.DeleteModelReq{
		Provider:  req.Provider,
		ModelType: req.ModelType,
		Model:     req.Model,
		UserId:    userId,
		OrgId:     orgId,
	})
	if err != nil {
		return err
	}
	return nil
}

func GetModel(ctx *gin.Context, userId, orgId string, req *request.GetModelRequest) (*response.ModelInfo, error) {
	resp, err := model.GetModel(ctx, &model_service.GetModelReq{
		Provider:  req.Provider,
		ModelType: req.ModelType,
		Model:     req.Model,
		UserId:    userId,
		OrgId:     orgId,
	})
	if err != nil {
		return nil, err
	}
	return toModelInfo(ctx, resp)
}

func ListModels(ctx *gin.Context, userId, orgId string, req *request.ListModelsRequest) (*response.ListResult, error) {
	resp, err := model.ListModels(ctx, &model_service.ListModelsReq{
		Provider:    req.Provider,
		ModelType:   req.ModelType,
		DisplayName: req.DisplayName,
		IsActive:    req.IsActive,
		UserId:      userId,
		OrgId:       orgId,
	})
	if err != nil {
		return nil, err
	}
	return &response.ListResult{
		List:  toModelBriefs(ctx, resp.Models),
		Total: resp.Total,
	}, nil
}

func ChangeModelStatus(ctx *gin.Context, userId, orgId string, req *request.ModelStatusRequest) error {
	_, err := model.ChangeModelStatus(ctx, &model_service.ModelStatusReq{
		Provider:  req.Provider,
		ModelType: req.ModelType,
		IsActive:  req.IsActive,
		Model:     req.Model,
		UserId:    userId,
		OrgId:     orgId,
	})
	if err != nil {
		return err
	}
	return nil
}

func GetModelById(ctx *gin.Context, req *request.GetModelByIdRequest) (*response.ModelInfo, error) {
	resp, err := model.GetModelById(ctx, &model_service.GetModelByIdReq{
		ModelId: req.ModelId,
	})
	if err != nil {
		return nil, err
	}
	return toModelInfo(ctx, resp)
}

func ListTypeModels(ctx *gin.Context, userId, orgId string, req *request.ListTypeModelsRequest) (*response.ListResult, error) {
	resp, err := model.ListTypeModels(ctx, &model_service.ListTypeModelsReq{
		ModelType: req.ModelType,
		UserId:    userId,
		OrgId:     orgId,
	})
	if err != nil {
		return nil, err
	}
	return &response.ListResult{
		List:  toModelBriefs(ctx, resp.Models),
		Total: resp.Total,
	}, nil
}

func parseImportAndUpdateClientReq(userId, orgId string, req *request.ImportOrUpdateModelRequest) (*model_service.ModelInfo, error) {
	clientReq := &model_service.ModelInfo{
		Provider:      req.Provider,
		ModelId:       req.ModelId,
		ModelType:     req.ModelType,
		Model:         req.Model,
		DisplayName:   req.DisplayName,
		ModelIconPath: req.Avatar.Key,
		PublishDate:   req.PublishDate,
		UserId:        userId,
		OrgId:         orgId,
		IsActive:      true,
	}
	configStr, err := req.ConfigString()
	if err != nil {
		return nil, grpc_util.ErrorStatus(err_code.Code_BFFInvalidArg, err.Error())
	}
	clientReq.ProviderConfig = configStr
	return clientReq, nil
}

func toModelInfo(ctx *gin.Context, modelInfo *model_service.ModelInfo) (*response.ModelInfo, error) {
	modelConfig, err := mp.ToModelConfig(modelInfo.Provider, modelInfo.ModelType, modelInfo.ProviderConfig)
	if err != nil {
		return nil, grpc_util.ErrorStatus(err_code.Code_BFFGeneral, fmt.Sprintf("model %v get model config err: %v", modelInfo.ModelId, err))
	}
	return &response.ModelInfo{
		ModelBrief: response.ModelBrief{
			ModelId:     modelInfo.ModelId,
			Provider:    modelInfo.Provider,
			Model:       modelInfo.Model,
			ModelType:   modelInfo.ModelType,
			DisplayName: modelInfo.DisplayName,
			Avatar:      CacheAvatar(ctx, modelInfo.ModelIconPath),
			PublishDate: modelInfo.PublishDate,
			IsActive:    modelInfo.IsActive,
			UserId:      modelInfo.UserId,
			OrgId:       modelInfo.OrgId,
			CreatedAt:   util.Time2Str(modelInfo.CreatedAt),
			UpdatedAt:   util.Time2Str(modelInfo.UpdatedAt),
		},
		Config: modelConfig,
	}, nil
}

func toModelBriefs(ctx *gin.Context, models []*model_service.ModelBrief) []*response.ModelBrief {
	result := make([]*response.ModelBrief, 0, len(models))
	for _, m := range models {
		modelBrief := &response.ModelBrief{
			ModelId:     m.ModelId,
			Provider:    m.Provider,
			Model:       m.Model,
			ModelType:   m.ModelType,
			DisplayName: m.DisplayName,
			Avatar:      CacheAvatar(ctx, m.ModelIconPath),
			PublishDate: m.PublishDate,
			IsActive:    m.IsActive,
			UserId:      m.UserId,
			OrgId:       m.OrgId,
		}
		if modelBrief.DisplayName == "" {
			modelBrief.DisplayName = modelBrief.Model
		}
		result = append(result, modelBrief)
	}
	return result
}

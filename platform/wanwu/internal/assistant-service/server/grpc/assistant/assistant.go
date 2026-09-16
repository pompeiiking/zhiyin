package assistant

import (
	"context"
	"encoding/json"
	"strconv"
	"strings"

	assistant_service "github.com/UnicomAI/wanwu/api/proto/assistant-service"
	"github.com/UnicomAI/wanwu/api/proto/common"
	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/assistant-service/client/model"
	"google.golang.org/protobuf/types/known/emptypb"
)

// GetAssistantByIds 根据智能体id集合获取智能体列表
func (s *Service) GetAssistantByIds(ctx context.Context, req *assistant_service.GetAssistantByIdsReq) (*assistant_service.AppBriefList, error) {
	// 转换字符串ID为uint32
	var assistantIDs []uint32
	for _, idStr := range req.AssistantIdList {
		if id, err := strconv.ParseUint(idStr, 10, 32); err == nil {
			assistantIDs = append(assistantIDs, uint32(id))
		}
	}

	// 调用client方法获取智能体列表
	assistants, status := s.cli.GetAssistantsByIDs(ctx, assistantIDs)
	if status != nil {
		return nil, errStatus(errs.Code_AssistantErr, status)
	}

	// 转换为响应格式
	var appBriefs []*common.AppBrief
	for _, assistant := range assistants {
		appBriefs = append(appBriefs, &common.AppBrief{
			OrgId:      assistant.OrgId,
			UserId:     assistant.UserId,
			AppId:      strconv.FormatUint(uint64(assistant.ID), 10),
			AppType:    "agent",
			Name:       assistant.Name,
			AvatarPath: assistant.AvatarPath,
			Desc:       assistant.Desc,
			CreatedAt:  assistant.CreatedAt,
			UpdatedAt:  assistant.UpdatedAt,
		})
	}

	return &assistant_service.AppBriefList{
		AssistantInfos: appBriefs,
	}, nil
}

// AssistantCreate 创建智能体
func (s *Service) AssistantCreate(ctx context.Context, req *assistant_service.AssistantCreateReq) (*emptypb.Empty, error) {
	// 组装model参数
	assistant := &model.Assistant{
		AvatarPath: req.AssistantBrief.AvatarPath,
		Name:       req.AssistantBrief.Name,
		Desc:       req.AssistantBrief.Desc,
		Scope:      1,
		UserId:     req.Identity.UserId,
		OrgId:      req.Identity.OrgId,
	}
	// 查找否存在相同名称智能体
	if err := s.cli.CheckSameAssistantName(ctx, req.Identity.UserId, req.Identity.OrgId, req.AssistantBrief.Name); err != nil {
		return nil, errStatus(errs.Code_AssistantErr, err)
	}
	// 调用client方法创建智能体
	if status := s.cli.CreateAssistant(ctx, assistant); status != nil {
		return nil, errStatus(errs.Code_AssistantErr, status)
	}

	return &emptypb.Empty{}, nil
}

// AssistantUpdate 修改智能体
func (s *Service) AssistantUpdate(ctx context.Context, req *assistant_service.AssistantUpdateReq) (*emptypb.Empty, error) {
	// 转换ID
	assistantID, err := strconv.ParseUint(req.AssistantId, 10, 32)
	if err != nil {
		return nil, err
	}

	// 组装model参数
	assistant := &model.Assistant{
		ID:         uint32(assistantID),
		AvatarPath: req.AssistantBrief.AvatarPath,
		Name:       req.AssistantBrief.Name,
		Desc:       req.AssistantBrief.Desc,
	}

	// 调用client方法更新智能体
	if status := s.cli.UpdateAssistant(ctx, assistant); status != nil {
		return nil, errStatus(errs.Code_AssistantErr, status)
	}

	return &emptypb.Empty{}, nil
}

// AssistantDelete 删除智能体
func (s *Service) AssistantDelete(ctx context.Context, req *assistant_service.AssistantDeleteReq) (*emptypb.Empty, error) {
	// 转换ID
	assistantID, err := strconv.ParseUint(req.AssistantId, 10, 32)
	if err != nil {
		return nil, err
	}

	// 调用client方法删除智能体
	if status := s.cli.DeleteAssistant(ctx, uint32(assistantID)); status != nil {
		return nil, errStatus(errs.Code_AssistantErr, status)
	}

	return &emptypb.Empty{}, nil
}

// AssistantConfigUpdate 修改智能体配置
func (s *Service) AssistantConfigUpdate(ctx context.Context, req *assistant_service.AssistantConfigUpdateReq) (*emptypb.Empty, error) {
	// 转换ID
	assistantID, err := strconv.ParseUint(req.AssistantId, 10, 32)
	if err != nil {
		return nil, err
	}

	// 先获取现有智能体信息
	existingAssistant, status := s.cli.GetAssistant(ctx, uint32(assistantID))
	if status != nil {
		return nil, errStatus(errs.Code_AssistantErr, status)
	}

	// 更新配置字段
	existingAssistant.Instructions = req.Instructions
	existingAssistant.Prologue = req.Prologue
	existingAssistant.RecommendQuestion = strings.Join(req.RecommendQuestion, "@#@")

	// 处理modelConfig，转换成json字符串之后再更新
	if req.ModelConfig != nil {
		modelConfigBytes, err := json.Marshal(req.ModelConfig)
		if err != nil {
			return nil, errStatus(errs.Code_AssistantErr, &errs.Status{
				TextKey: "assistant_modelConfig_marshal",
				Args:    []string{err.Error()},
			})
		}
		existingAssistant.ModelConfig = string(modelConfigBytes)
	}

	// 处理rerankConfig，转换成json字符串之后再更新
	if req.RerankConfig != nil {
		rerankConfigBytes, err := json.Marshal(req.RerankConfig)
		if err != nil {
			return nil, errStatus(errs.Code_AssistantErr, &errs.Status{
				TextKey: "assistant_rerankConfig_marshal",
				Args:    []string{err.Error()},
			})
		}
		existingAssistant.RerankConfig = string(rerankConfigBytes)
	}

	// 处理knowledgeBaseConfig，转换成json字符串之后再更新
	if req.KnowledgeBaseConfig != nil {
		knowledgeBaseConfigBytes, err := json.Marshal(req.KnowledgeBaseConfig)
		if err != nil {
			return nil, errStatus(errs.Code_AssistantErr, &errs.Status{
				TextKey: "assistant_knowledgeBaseConfig_marshal",
				Args:    []string{err.Error()},
			})
		}
		existingAssistant.KnowledgebaseConfig = string(knowledgeBaseConfigBytes)
	}

	// 处理onlineSearchConfig，转换成json字符串之后再更新
	if req.OnlineSearchConfig != nil {
		onlineSearchConfigBytes, err := json.Marshal(req.OnlineSearchConfig)
		if err != nil {
			return nil, errStatus(errs.Code_AssistantErr, &errs.Status{
				TextKey: "assistant_onlineSearchConfig_marshal",
				Args:    []string{err.Error()},
			})
		}
		existingAssistant.OnlineSearchConfig = string(onlineSearchConfigBytes)
	}

	// 调用client方法更新智能体
	if status := s.cli.UpdateAssistant(ctx, existingAssistant); status != nil {
		return nil, errStatus(errs.Code_AssistantErr, status)
	}

	return &emptypb.Empty{}, nil
}

// GetAssistantListMyAll 智能体列表
func (s *Service) GetAssistantListMyAll(ctx context.Context, req *assistant_service.GetAssistantListMyAllReq) (*assistant_service.AppBriefList, error) {
	// 调用client方法获取智能体列表
	assistants, _, status := s.cli.GetAssistantList(ctx, req.Identity.UserId, req.Identity.OrgId, req.Name)
	if status != nil {
		return nil, errStatus(errs.Code_AssistantErr, status)
	}

	// 转换为响应格式
	var appBriefs []*common.AppBrief
	for _, assistant := range assistants {
		appBriefs = append(appBriefs, &common.AppBrief{
			OrgId:      assistant.OrgId,
			UserId:     assistant.UserId,
			AppId:      strconv.FormatUint(uint64(assistant.ID), 10),
			AppType:    "agent",
			Name:       assistant.Name,
			AvatarPath: assistant.AvatarPath,
			Desc:       assistant.Desc,
			CreatedAt:  assistant.CreatedAt,
			UpdatedAt:  assistant.UpdatedAt,
		})
	}

	return &assistant_service.AppBriefList{
		AssistantInfos: appBriefs,
	}, nil
}

// GetAssistantInfo 查看智能体详情
func (s *Service) GetAssistantInfo(ctx context.Context, req *assistant_service.GetAssistantInfoReq) (*assistant_service.AssistantInfo, error) {
	// 转换ID
	assistantID, err := strconv.ParseUint(req.AssistantId, 10, 32)
	if err != nil {
		return nil, err
	}

	// 调用client方法获取智能体详情
	assistant, status := s.cli.GetAssistant(ctx, uint32(assistantID))
	if status != nil {
		return nil, errStatus(errs.Code_AssistantErr, status)
	}

	// 获取关联的Actions和WorkFlows
	actions, _ := s.cli.GetAssistantActionsByAssistantID(ctx, req.AssistantId)
	workflows, _ := s.cli.GetAssistantWorkflowsByAssistantID(ctx, req.AssistantId)

	// 转换Actions
	var actionInfos []*assistant_service.ActionInfos
	for _, action := range actions {
		actionInfos = append(actionInfos, &assistant_service.ActionInfos{
			ActionId: strconv.FormatUint(uint64(action.ID), 10),
			ApiName:  action.ActionName,
			Enable:   action.Enable,
		})
	}

	// 转换WorkFlows
	var workFlowInfos []*assistant_service.WorkFlowInfos
	for _, workflow := range workflows {
		workFlowInfos = append(workFlowInfos, &assistant_service.WorkFlowInfos{
			Id:         strconv.FormatUint(uint64(workflow.ID), 10),
			WorkFlowId: workflow.WorkflowId,
			ApiName:    workflow.Name,
			Enable:     workflow.Enable,
		})
	}

	// 处理assistant.ModelConfig，转换成common.AppModelConfig
	var modelConfig *common.AppModelConfig
	if assistant.ModelConfig != "" {
		modelConfig = &common.AppModelConfig{}
		if err := json.Unmarshal([]byte(assistant.ModelConfig), modelConfig); err != nil {
			return nil, errStatus(errs.Code_AssistantErr, &errs.Status{
				TextKey: "assistant_modelConfig_unmarshal",
				Args:    []string{err.Error()},
			})
		}
	}

	// 处理assistant.RerankConfig，转换成common.AppModelConfig
	var rerankConfig *common.AppModelConfig
	if assistant.RerankConfig != "" {
		rerankConfig = &common.AppModelConfig{}
		if err := json.Unmarshal([]byte(assistant.RerankConfig), rerankConfig); err != nil {
			return nil, errStatus(errs.Code_AssistantErr, &errs.Status{
				TextKey: "assistant_rerankConfig_unmarshal",
				Args:    []string{err.Error()},
			})
		}
	}

	// 处理assistant.KnowledgebaseConfig，转换成AssistantKnowledgeBaseConfig
	var knowledgeBaseConfig *assistant_service.AssistantKnowledgeBaseConfig
	if assistant.KnowledgebaseConfig != "" {
		knowledgeBaseConfig = &assistant_service.AssistantKnowledgeBaseConfig{}
		if err := json.Unmarshal([]byte(assistant.KnowledgebaseConfig), knowledgeBaseConfig); err != nil {
			return nil, errStatus(errs.Code_AssistantErr, &errs.Status{
				TextKey: "assistant_knowledgeBaseConfig_unmarshal",
				Args:    []string{err.Error()},
			})
		}
	}

	// 处理assistant.OnlineSearchConfig，转换成AssistantOnlineSearchConfig
	var onlineSearchConfig *assistant_service.AssistantOnlineSearchConfig
	if assistant.OnlineSearchConfig != "" {
		onlineSearchConfig = &assistant_service.AssistantOnlineSearchConfig{}
		if err := json.Unmarshal([]byte(assistant.OnlineSearchConfig), onlineSearchConfig); err != nil {
			return nil, errStatus(errs.Code_AssistantErr, &errs.Status{
				TextKey: "assistant_onlineSearchConfig_unmarshal",
				Args:    []string{err.Error()},
			})
		}
	}

	return &assistant_service.AssistantInfo{
		AssistantId: strconv.FormatUint(uint64(assistant.ID), 10),
		AssistantBrief: &common.AppBriefConfig{
			Name:       assistant.Name,
			AvatarPath: assistant.AvatarPath,
			Desc:       assistant.Desc,
		},
		Prologue:            assistant.Prologue,
		Instructions:        assistant.Instructions,
		RecommendQuestion:   strings.Split(assistant.RecommendQuestion, "@#@"),
		ModelConfig:         modelConfig,
		KnowledgeBaseConfig: knowledgeBaseConfig,
		RerankConfig:        rerankConfig,
		OnlineSearchConfig:  onlineSearchConfig,
		Scope:               int32(assistant.Scope),
		WorkFlowInfos:       workFlowInfos,
		ActionInfos:         actionInfos,
		CreatTime:           assistant.CreatedAt,
		UpdateTime:          assistant.UpdatedAt,
	}, nil
}

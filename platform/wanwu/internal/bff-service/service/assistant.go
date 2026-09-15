package service

import (
	"encoding/json"
	"sort"

	assistant_service "github.com/UnicomAI/wanwu/api/proto/assistant-service"
	model_service "github.com/UnicomAI/wanwu/api/proto/model-service"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/response"
	"github.com/UnicomAI/wanwu/pkg/log"
	"github.com/UnicomAI/wanwu/pkg/util"
	"github.com/gin-gonic/gin"
)

func AssistantCreate(ctx *gin.Context, userId, orgId string, req request.AppBriefConfig) (interface{}, error) {
	_, err := assistant.AssistantCreate(ctx, &assistant_service.AssistantCreateReq{
		AssistantBrief: appBriefConfigModel2Proto(req),
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return nil, err
	}
	return nil, nil
}

func AssistantUpdate(ctx *gin.Context, userId, orgId string, req request.AssistantBrief) (interface{}, error) {
	_, err := assistant.AssistantUpdate(ctx, &assistant_service.AssistantUpdateReq{
		AssistantId:    req.AssistantId,
		AssistantBrief: appBriefConfigModel2Proto(req.AppBriefConfig),
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return nil, err
	}
	return nil, nil
}

func AssistantConfigUpdate(ctx *gin.Context, userId, orgId string, req request.AssistantConfig) (interface{}, error) {
	modelConfig, err := appModelConfigModel2Proto(req.ModelConfig)
	if err != nil {
		return nil, err
	}
	rerankConfig, err := appModelConfigModel2Proto(req.RerankConfig)
	if err != nil {
		return nil, err
	}
	_, err = assistant.AssistantConfigUpdate(ctx, &assistant_service.AssistantConfigUpdateReq{
		AssistantId:       req.AssistantId,
		Prologue:          req.Prologue,
		Instructions:      req.Instructions,
		RecommendQuestion: req.RecommendQuestion,
		ModelConfig:       modelConfig,
		KnowledgeBaseConfig: &assistant_service.AssistantKnowledgeBaseConfig{
			KnowledgeBases:   transKnowledgebases2Proto(req.KnowledgeBaseConfig.Knowledgebases),
			MaxHistoryEnable: req.KnowledgeBaseConfig.Config.MaxHistoryEnable,
			Threshold:        req.KnowledgeBaseConfig.Config.Threshold,
			ThresholdEnable:  req.KnowledgeBaseConfig.Config.ThresholdEnable,
			TopK:             req.KnowledgeBaseConfig.Config.TopK,
			TopKEnable:       req.KnowledgeBaseConfig.Config.TopKEnable,
		},
		RerankConfig: rerankConfig,
		OnlineSearchConfig: &assistant_service.AssistantOnlineSearchConfig{
			SearchUrl:      req.OnlineSearchConfig.SearchUrl,
			SearchKey:      req.OnlineSearchConfig.SearchKey,
			Enable:         req.OnlineSearchConfig.Enable,
			SearchRerankId: req.OnlineSearchConfig.SearchRerankId,
		},
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})

	if err != nil {
		return nil, err
	}
	return nil, nil
}

func GetAssistantInfo(ctx *gin.Context, userId, orgId string, req request.AssistantIdRequest) (response.Assistant, error) {
	resp, err := assistant.GetAssistantInfo(ctx, &assistant_service.GetAssistantInfoReq{
		AssistantId: req.AssistantId,
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return response.Assistant{}, err
	}
	assistant, err := transAssistantResp2Model(ctx, resp)
	if err != nil {
		return response.Assistant{}, err
	}
	return assistant, nil
}

func AssistantWorkFlowCreate(ctx *gin.Context, userId, orgId string, req request.WorkFlowAddRequest) (interface{}, error) {
	_, err := assistant.AssistantWorkFlowCreate(ctx, &assistant_service.AssistantWorkFlowCreateReq{
		AssistantId: req.AssistantId,
		Schema:      req.Schema,
		WorkFlowId:  req.WorkFlowId,
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return nil, err
	}
	return nil, nil
}

func AssistantWorkFlowDelete(ctx *gin.Context, userId, orgId string, req request.WorkFlowIdRequest) (interface{}, error) {
	_, err := assistant.AssistantWorkFlowDelete(ctx, &assistant_service.AssistantWorkFlowDeleteReq{
		WorkFlowId: req.WorkFlowId,
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return nil, err
	}
	return nil, nil
}

func AssistantWorkFlowEnableSwitch(ctx *gin.Context, userId, orgId string, req request.WorkFlowIdRequest) (interface{}, error) {
	_, err := assistant.AssistantWorkFlowEnableSwitch(ctx, &assistant_service.AssistantWorkFlowEnableSwitchReq{
		WorkFlowId: req.WorkFlowId,
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return nil, err
	}
	return nil, nil
}

func AssistantActionCreate(ctx *gin.Context, userId, orgId string, req request.ActionAddRequest) (response.ActionAddResponse, error) {
	resp, err := assistant.AssistantActionCreate(ctx, &assistant_service.AssistantActionCreateReq{
		AssistantId: req.AssistantId,
		Schema:      req.Schema,
		ApiAuth: &assistant_service.ApiAuthWebRequest{
			Type:             req.ApiAuth.Type,
			ApiKey:           req.ApiAuth.APIKey,
			CustomHeaderName: req.ApiAuth.CustomHeaderName,
			AuthType:         req.ApiAuth.AuthType,
		},
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return response.ActionAddResponse{}, err
	}
	return response.ActionAddResponse{
		ActionId: resp.ActionId,
		ApiList:  transActionApiResponseList(resp.List),
	}, nil
}

func transActionApiResponseList(list []*assistant_service.ActionApi) []response.ActionApiResponse {
	var responseList []response.ActionApiResponse
	for _, api := range list {
		responseList = append(responseList, response.ActionApiResponse{
			Name:   api.Name,
			Method: api.Method,
			Path:   api.Path,
		})
	}
	return responseList
}

func AssistantActionDelete(ctx *gin.Context, userId, orgId string, req request.ActionIdRequest) (interface{}, error) {
	_, err := assistant.AssistantActionDelete(ctx, &assistant_service.AssistantActionDeleteReq{
		ActionId: req.ActionId,
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return nil, err
	}
	return nil, nil
}

func AssistantActionUpdate(ctx *gin.Context, userId, orgId string, req request.ActionUpdateRequest) (interface{}, error) {
	_, err := assistant.AssistantActionUpdate(ctx, &assistant_service.AssistantActionUpdateReq{
		ActionId: req.ActionId,
		Schema:   req.Schema,
		ApiAuth: &assistant_service.ApiAuthWebRequest{
			Type:             req.ApiAuth.Type,
			ApiKey:           req.ApiAuth.APIKey,
			CustomHeaderName: req.ApiAuth.CustomHeaderName,
			AuthType:         req.ApiAuth.AuthType,
		},
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return nil, err
	}
	return nil, nil
}

func GetAssistantActionInfo(ctx *gin.Context, userId, orgId string, req request.ActionIdRequest) (response.Action, error) {
	resp, err := assistant.GetAssistantActionInfo(ctx, &assistant_service.GetAssistantActionInfoReq{
		ActionId: req.ActionId,
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return response.Action{}, err
	}
	return transActionResp2Model(resp), nil
}

func AssistantActionEnableSwitch(ctx *gin.Context, userId, orgId string, req request.ActionIdRequest) (interface{}, error) {
	_, err := assistant.AssistantActionEnableSwitch(ctx, &assistant_service.AssistantActionEnableSwitchReq{
		ActionId: req.ActionId,
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return nil, err
	}
	return nil, nil
}

func ConversationCreate(ctx *gin.Context, userId, orgId string, req request.ConversationCreateRequest) (response.ConversationCreateResp, error) {
	resp, err := assistant.ConversationCreate(ctx, &assistant_service.ConversationCreateReq{
		AssistantId: req.AssistantId,
		Prompt:      req.Prompt,
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return response.ConversationCreateResp{}, err
	}
	return response.ConversationCreateResp{
		ConversationId: resp.ConversationId,
	}, nil
}

func ConversationDelete(ctx *gin.Context, userId, orgId string, req request.ConversationIdRequest) (interface{}, error) {
	_, err := assistant.ConversationDelete(ctx, &assistant_service.ConversationDeleteReq{
		ConversationId: req.ConversationId,
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return nil, err
	}
	return nil, nil
}

func GetConversationList(ctx *gin.Context, userId, orgId string, req request.ConversationGetListRequest) (response.PageResult, error) {
	resp, err := assistant.GetConversationList(ctx, &assistant_service.GetConversationListReq{
		AssistantId: req.AssistantId,
		PageSize:    int32(req.PageSize),
		PageNo:      int32(req.PageNo),
		Identity: &assistant_service.Identity{
			UserId: userId,
		},
	})
	if err != nil {
		return response.PageResult{}, err
	}
	return response.PageResult{Total: resp.Total, List: resp.Data}, nil
}

func GetConversationDetailList(ctx *gin.Context, userId, orgId string, req request.ConversationGetDetailListRequest) (response.PageResult, error) {
	resp, err := assistant.GetConversationDetailList(ctx, &assistant_service.GetConversationDetailListReq{
		ConversationId: req.ConversationId,
		PageSize:       int32(req.PageSize),
		PageNo:         int32(req.PageNo),
		Identity: &assistant_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return response.PageResult{}, err
	}

	// 转换resp.Data为自定义的ConversionDetailInfo结构体数组
	var convertedList []response.ConversationDetailInfo
	for _, item := range resp.Data {
		convertedItem := response.ConversationDetailInfo{
			Id:              item.Id,
			AssistantId:     item.AssistantId,
			ConversationId:  item.ConversationId,
			Prompt:          item.Prompt,
			SysPrompt:       item.SysPrompt,
			Response:        item.Response,
			QaType:          item.QaType,
			CreatedBy:       item.CreatedBy,
			CreatedAt:       item.CreatedAt,
			UpdatedAt:       item.UpdatedAt,
			RequestFileUrls: item.RequestFileUrls,
			FileSize:        item.FileSize,
			FileName:        item.FileName,
		}

		// 将SearchList从string转换为interface{}
		if item.SearchList != "" {
			var searchList interface{}
			if err := json.Unmarshal([]byte(item.SearchList), &searchList); err != nil {
				log.Warnf("解析SearchList失败，使用原始字符串，error: %v, searchList: %s", err, item.SearchList)
				convertedItem.SearchList = item.SearchList
			} else {
				convertedItem.SearchList = searchList
			}
		} else {
			convertedItem.SearchList = nil
		}

		convertedList = append(convertedList, convertedItem)

		// 对切片进行排序
		sort.Slice(convertedList, func(i, j int) bool {
			// CreatedAt值小的时间更早，排在前面
			return convertedList[i].CreatedAt < convertedList[j].CreatedAt
		})
	}

	return response.PageResult{Total: resp.Total, List: convertedList, PageNo: req.PageNo, PageSize: req.PageSize}, nil
}

func transKnowledgebases2Proto(kbs []request.AppKnowledgeBase) []*assistant_service.AssistantKnowledgeBase {
	if kbs == nil {
		return nil
	}
	result := make([]*assistant_service.AssistantKnowledgeBase, 0, len(kbs))
	for _, kb := range kbs {
		result = append(result, &assistant_service.AssistantKnowledgeBase{
			Id:   kb.ID,
			Name: kb.Name,
		})
	}
	return result
}

func transAssistantResp2Model(ctx *gin.Context, resp *assistant_service.AssistantInfo) (response.Assistant, error) {
	log.Debugf("开始转换Assistant响应到模型，响应内容: %+v", resp)
	if resp == nil {
		log.Debugf("Assistant响应为空，返回空Assistant模型")
		return response.Assistant{}, nil
	}
	var modelConfig request.AppModelConfig
	if resp.ModelConfig != nil && resp.ModelConfig.ModelId != "" {
		log.Debugf("检测到模型配置，模型ID: %s", resp.ModelConfig.ModelId)
		modelInfo, err := model.GetModelById(ctx.Request.Context(), &model_service.GetModelByIdReq{ModelId: resp.ModelConfig.ModelId})
		if err != nil {
			log.Errorf("获取模型信息失败，模型ID: %s, 错误: %v", resp.ModelConfig.ModelId, err)
			return response.Assistant{}, err
		}
		modelConfig, err = appModelConfigProto2Model(resp.ModelConfig, modelInfo.DisplayName)
		if err != nil {
			log.Errorf("模型配置Proto转换到模型失败，模型ID: %s, 错误: %v", resp.ModelConfig.ModelId, err)
			return response.Assistant{}, err
		}
		log.Debugf("模型配置转换成功: %+v", modelConfig)
	} else {
		log.Debugf("模型配置为空或模型ID为空")
	}
	var rerankConfig request.AppModelConfig
	if resp.RerankConfig != nil && resp.RerankConfig.ModelId != "" {
		log.Debugf("检测到Rerank配置，模型ID: %s", resp.RerankConfig.ModelId)
		modelInfo, err := model.GetModelById(ctx.Request.Context(), &model_service.GetModelByIdReq{ModelId: resp.RerankConfig.ModelId})
		if err != nil {
			log.Errorf("获取Rerank模型信息失败，模型ID: %s, 错误: %v", resp.RerankConfig.ModelId, err)
			return response.Assistant{}, err
		}
		rerankConfig, err = appModelConfigProto2Model(resp.RerankConfig, modelInfo.DisplayName)
		if err != nil {
			log.Errorf("Rerank配置Proto转换到模型失败，模型ID: %s, 错误: %v", resp.RerankConfig.ModelId, err)
			return response.Assistant{}, err
		}
		log.Debugf("Rerank配置转换成功: %+v", rerankConfig)
	} else {
		log.Debugf("Rerank配置为空或模型ID为空")
	}
	var actionInfos []*response.ActionInfos
	if resp.ActionInfos != nil {
		actionInfos = make([]*response.ActionInfos, 0, len(resp.ActionInfos))
		for _, action := range resp.ActionInfos {
			actionInfos = append(actionInfos, &response.ActionInfos{
				ActionId: action.ActionId,
				ApiName:  action.ApiName,
				Enable:   action.Enable,
			})
			log.Debugf("添加动作信息: ActionId=%s, ApiName=%s", action.ActionId, action.ApiName)
		}
		log.Debugf("总共添加 %d 个动作信息", len(actionInfos))
	} else {
		log.Debugf("动作信息为空")
	}
	var workFlowInfos []*response.WorkFlowInfos
	if resp.WorkFlowInfos != nil {
		workFlowInfos = make([]*response.WorkFlowInfos, 0, len(resp.WorkFlowInfos))
		for _, wf := range resp.WorkFlowInfos {
			workFlowInfos = append(workFlowInfos, &response.WorkFlowInfos{
				Id:         wf.Id,
				WorkFlowId: wf.WorkFlowId,
				ApiName:    wf.ApiName,
				Enable:     wf.Enable,
			})
			log.Debugf("添加工作流信息: WorkFlowId=%s, ApiName=%s", wf.WorkFlowId, wf.ApiName)
		}
		log.Debugf("总共添加 %d 个工作流信息", len(workFlowInfos))
	} else {
		log.Debugf("工作流信息为空")
	}
	var onlineSearchConfig request.OnlineSearchConfig
	if resp.OnlineSearchConfig != nil {
		onlineSearchConfig = request.OnlineSearchConfig{
			SearchUrl:      resp.OnlineSearchConfig.SearchUrl,
			SearchKey:      resp.OnlineSearchConfig.SearchKey,
			Enable:         resp.OnlineSearchConfig.Enable,
			SearchRerankId: resp.OnlineSearchConfig.SearchRerankId,
		}
	}

	assistantModel := response.Assistant{
		AssistantId:       resp.AssistantId,
		AppBriefConfig:    appBriefConfigProto2Model(ctx, resp.AssistantBrief),
		Prologue:          resp.Prologue,
		Instructions:      resp.Instructions,
		RecommendQuestion: resp.RecommendQuestion,
		KnowledgeBaseConfig: func() request.AppKnowledgebaseConfig {
			if resp.KnowledgeBaseConfig != nil {
				log.Debugf("检测到知识库配置")
				return request.AppKnowledgebaseConfig{
					Knowledgebases: transKnowledgebases2Model(resp.KnowledgeBaseConfig.KnowledgeBases),
					Config: request.AppKnowledgebaseParams{
						MaxHistory:       resp.KnowledgeBaseConfig.MaxHistory,
						MaxHistoryEnable: resp.KnowledgeBaseConfig.MaxHistoryEnable,
						Threshold:        resp.KnowledgeBaseConfig.Threshold,
						ThresholdEnable:  resp.KnowledgeBaseConfig.ThresholdEnable,
						TopK:             resp.KnowledgeBaseConfig.TopK,
						TopKEnable:       resp.KnowledgeBaseConfig.TopKEnable,
					},
				}
			}
			log.Debugf("知识库配置为空")
			return request.AppKnowledgebaseConfig{}
		}(),
		ModelConfig:        modelConfig,
		RerankConfig:       rerankConfig,
		OnlineSearchConfig: onlineSearchConfig,
		Scope:              resp.Scope,
		ActionInfos:        actionInfos,
		WorkFlowInfos:      workFlowInfos,
		CreatedAt:          util.Time2Str(resp.CreatTime),
		UpdatedAt:          util.Time2Str(resp.UpdateTime),
	}
	log.Debugf("Assistant响应到模型转换完成，结果: %+v", assistantModel)
	return assistantModel, nil
}

func transKnowledgebases2Model(kbs []*assistant_service.AssistantKnowledgeBase) []request.AppKnowledgeBase {
	if kbs == nil {
		return nil
	}
	result := make([]request.AppKnowledgeBase, 0, len(kbs))
	for _, kb := range kbs {
		result = append(result, request.AppKnowledgeBase{
			ID:   kb.Id,
			Name: kb.Name,
		})
	}
	return result
}

func transActionResp2Model(resp *assistant_service.GetAssistantActionInfoResp) response.Action {
	if resp == nil {
		return response.Action{}
	}

	var apiList []response.ActionApiResponse
	if resp.List != nil {
		apiList = make([]response.ActionApiResponse, 0, len(resp.List))
		for _, api := range resp.List {
			apiList = append(apiList, response.ActionApiResponse{
				Name:   api.Name,
				Method: api.Method,
				Path:   api.Path,
			})
		}
	}

	return response.Action{
		ActionId:   resp.ActionId,
		Schema:     resp.Schema,
		SchemaType: resp.SchemaType,
		ApiAuth: func() response.ApiAuthWebRequest {
			if resp.ApiAuth != nil {
				return response.ApiAuthWebRequest{
					Type:             resp.ApiAuth.Type,
					APIKey:           resp.ApiAuth.ApiKey,
					CustomHeaderName: resp.ApiAuth.CustomHeaderName,
					AuthType:         resp.ApiAuth.AuthType,
				}
			}
			return response.ApiAuthWebRequest{}
		}(),
		ApiList: apiList,
	}
}

package assistant

import (
	"bufio"
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"

	assistant_service "github.com/UnicomAI/wanwu/api/proto/assistant-service"
	"github.com/UnicomAI/wanwu/api/proto/common"
	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/assistant-service/client/model"
	"github.com/UnicomAI/wanwu/internal/assistant-service/config"
	"github.com/UnicomAI/wanwu/internal/assistant-service/pkg/util"
	"github.com/UnicomAI/wanwu/pkg/constant"
	"github.com/UnicomAI/wanwu/pkg/es"
	"github.com/UnicomAI/wanwu/pkg/log"
	mp "github.com/UnicomAI/wanwu/pkg/model-provider"
	"github.com/google/uuid"
	"google.golang.org/protobuf/types/known/emptypb"
)

// ConversationCreate 创建对话
func (s *Service) ConversationCreate(ctx context.Context, req *assistant_service.ConversationCreateReq) (*assistant_service.ConversationCreateResp, error) {
	// 组装model参数
	assistantID, err := strconv.ParseUint(req.AssistantId, 10, 32)
	if err != nil {
		return nil, err
	}

	conversation := &model.Conversation{
		AssistantId: uint32(assistantID),
		Title:       req.Prompt, // 使用prompt作为初始标题
		UserId:      req.Identity.UserId,
		OrgId:       req.Identity.OrgId,
	}

	// 调用client方法创建对话
	if status := s.cli.CreateConversation(ctx, conversation); status != nil {
		return nil, errStatus(errs.Code_AssistantConversationErr, status)
	}

	return &assistant_service.ConversationCreateResp{
		ConversationId: strconv.FormatUint(uint64(conversation.ID), 10),
	}, nil
}

// ConversationDelete 删除对话
func (s *Service) ConversationDelete(ctx context.Context, req *assistant_service.ConversationDeleteReq) (*emptypb.Empty, error) {
	// 转换ID
	conversationID, err := strconv.ParseUint(req.ConversationId, 10, 32)
	if err != nil {
		return nil, err
	}

	// 调用client方法删除对话
	if status := s.cli.DeleteConversation(ctx, uint32(conversationID)); status != nil {
		return nil, errStatus(errs.Code_AssistantConversationErr, status)
	}

	return &emptypb.Empty{}, nil
}

// GetConversationList 对话列表
func (s *Service) GetConversationList(ctx context.Context, req *assistant_service.GetConversationListReq) (*assistant_service.GetConversationListResp, error) {
	// 计算offset
	offset := (req.PageNo - 1) * req.PageSize

	// 调用client方法获取对话列表
	conversations, total, status := s.cli.GetConversationList(ctx, req.AssistantId, req.Identity.UserId, req.Identity.OrgId, offset, req.PageSize)
	if status != nil {
		return nil, errStatus(errs.Code_AssistantConversationErr, status)
	}

	// 转换为响应格式
	var conversationInfos []*assistant_service.ConversationInfo
	for _, conversation := range conversations {
		conversationInfos = append(conversationInfos, &assistant_service.ConversationInfo{
			ConversationId: strconv.FormatUint(uint64(conversation.ID), 10),
			AssistantId:    strconv.FormatUint(uint64(conversation.AssistantId), 10),
			Title:          conversation.Title,
			CreatTime:      conversation.CreatedAt,
		})
	}

	return &assistant_service.GetConversationListResp{
		Data:     conversationInfos,
		Total:    total,
		PageSize: req.PageSize,
		PageNo:   req.PageNo,
	}, nil
}

// GetConversationDetailList 对话详情历史列表
func (s *Service) GetConversationDetailList(ctx context.Context, req *assistant_service.GetConversationDetailListReq) (*assistant_service.GetConversationDetailListResp, error) {
	// 计算分页参数
	from := (req.PageNo - 1) * req.PageSize
	size := int(req.PageSize)

	// 组装查询条件
	fieldConditions := map[string]interface{}{
		"conversationId": req.ConversationId,
		"userId":         req.Identity.UserId,
		"orgId":          req.Identity.OrgId,
	}

	// 使用通配符查询所有对话详情索引
	indexPattern := "conversation_detail_infos_*"

	// 从ES查询数据
	documents, total, err := es.Assistant().SearchByFields(ctx, indexPattern, fieldConditions, int(from), size)
	if err != nil {
		log.Errorf("从ES查询对话详情失败，conversationId: %s, userId: %s, error: %v", req.ConversationId, req.Identity.UserId, err)
		return nil, fmt.Errorf("查询对话详情失败: %v", err)
	}

	// 转换查询结果为响应格式
	var conversationDetails []*assistant_service.ConversionDetailInfo
	for _, doc := range documents {
		var detail model.ConversationDetails
		if err := json.Unmarshal(doc, &detail); err != nil {
			log.Warnf("解析ES文档失败: %v", err)
			continue
		}

		conversationDetails = append(conversationDetails, &assistant_service.ConversionDetailInfo{
			Id:              detail.Id,
			AssistantId:     detail.AssistantId,
			ConversationId:  detail.ConversationId,
			Prompt:          detail.Prompt,
			SysPrompt:       detail.SysPrompt,
			Response:        detail.Response,
			SearchList:      detail.SearchList,
			QaType:          detail.QaType,
			CreatedBy:       detail.UserId, // 使用CreatedBy字段映射UserId
			CreatedAt:       detail.CreatedAt,
			UpdatedAt:       detail.UpdatedAt,
			RequestFileUrls: []string{detail.FileUrl},
			FileSize:        detail.FileSize,
			FileName:        detail.FileName,
		})
	}

	log.Infof("成功从ES查询对话详情，conversationId: %s, userId: %s, 总数: %d, 返回: %d",
		req.ConversationId, req.Identity.UserId, total, len(conversationDetails))

	return &assistant_service.GetConversationDetailListResp{
		Data:     conversationDetails,
		Total:    total,
		PageSize: req.PageSize,
		PageNo:   req.PageNo,
	}, nil
}

// AssistantConversionStream 智能体流式对话
func (s *Service) AssistantConversionStream(req *assistant_service.AssistantConversionStreamReq, stream assistant_service.AssistantService_AssistantConversionStreamServer) error {
	ctx := stream.Context()
	reqUserId := req.Identity.UserId
	log.Debugf("Assistant服务开始智能体流式对话，assistantId: %s, userId: %s, orgId: %s, conversationId: %s, fileInfo: %+v, trial: %v, prompt: %s",
		req.AssistantId, reqUserId, req.Identity.OrgId, req.ConversationId, req.FileInfo, req.Trial, req.Prompt)

	// 根据智能体id查询智能体信息
	assistantID, err := strconv.ParseUint(req.AssistantId, 10, 32)
	if err != nil {
		log.Errorf("Assistant服务智能体ID转换失败，assistantId: %s, error: %v", req.AssistantId, err)
		return err
	}

	assistant, status := s.cli.GetAssistant(ctx, uint32(assistantID))
	if status != nil {
		log.Errorf("Assistant服务获取智能体信息失败，assistantId: %s, error: %v", req.AssistantId, status)
		if ctx.Err() != nil {
			saveConversation(ctx, req, "本次回答已被终止", "")
			return ctx.Err()
		}
		SSEError(stream, "智能体信息获取失败")
		return errStatus(errs.Code_AssistantConversationErr, status)
	}

	log.Debugf("Assistant服务获取到智能体信息，assistantId: %s, 名称: %s, Scope: %d, userId: %s, orgId: %s",
		req.AssistantId, assistant.Name, assistant.Scope, assistant.UserId, assistant.OrgId)

	// 公开的智能体，xuid使用智能体创建者用户信息
	xuid := reqUserId
	if req.AppPublishType == constant.AppPublishPublic {
		xuid = assistant.UserId
		log.Debugf("Assistant服务公开智能体，使用创建者信息，assistantId: %s, userId: %s", req.AssistantId, assistant.UserId)
	}

	// 获取Assistant配置
	assistantConfig := config.Cfg().Assistant
	if assistantConfig.SseUrl == "" {
		log.Errorf("Assistant服务SSE URL配置为空，assistantId: %s", req.AssistantId)
		if ctx.Err() != nil {
			saveConversation(ctx, req, "本次回答已被终止", "")
			return ctx.Err()
		}
		SSEError(stream, "智能体配置错误")
		return fmt.Errorf("智能体配置错误")
	}

	// 组装智能体能力接口请求体
	requestBody := make(map[string]interface{})
	requestBody["input"] = req.Prompt
	requestBody["stream"] = true
	if assistant.Instructions != "" {
		requestBody["system_role"] = assistant.Instructions
	}
	if req.FileInfo.FileUrl != "" {
		requestBody["upload_file_url"] = req.FileInfo.FileUrl
		requestBody["file_name"] = req.FileInfo.FileName
	}

	actionPluginList := []PluginListAlgRequest{}
	workflowPluginList := []PluginListAlgRequest{}
	if assistant.HasAction {
		actionPluginList, err = buildActionPluginListAlgParam(ctx, s, req.AssistantId, reqUserId, req.Identity.OrgId)
		if err != nil {
			log.Errorf(err.Error())
			if ctx.Err() != nil {
				saveConversation(ctx, req, "本次回答已被终止", "")
				return ctx.Err()
			}
			SSEError(stream, "智能体action配置错误")
			return err
		}
		log.Debugf("智能体action配置，assistantId: %s, actionPluginList: %s", req.AssistantId, actionPluginList)
	}
	if assistant.HasWorkflow {
		workflowPluginList, err = buildWorkflowPluginListAlgParam(ctx, s, req.AssistantId, reqUserId, req.Identity.OrgId)
		if err != nil {
			log.Errorf(err.Error())
			if ctx.Err() != nil {
				saveConversation(ctx, req, "本次回答已被终止", "")
				return ctx.Err()
			}
			SSEError(stream, "智能体workflow配置错误")
			return err
		}
		log.Debugf("智能体workflow配置，assistantId: %s, workflowPluginList: %s", req.AssistantId, workflowPluginList)
	}
	allPlugin := append(actionPluginList, workflowPluginList...)
	requestBody["plugin_list"] = allPlugin
	log.Debugf("智能体plugin_list，assistantId: %s, plugin_list: %s", req.AssistantId, allPlugin)

	// 将string类型的ModelConfig转换为common.AppModelConfig
	var modelConfig *common.AppModelConfig
	if assistant.ModelConfig != "" {
		log.Debugf("Assistant服务解析模型配置，assistantId: %s, modelConfig: %s", req.AssistantId, assistant.ModelConfig)
		modelConfig = &common.AppModelConfig{}
		if err := json.Unmarshal([]byte(assistant.ModelConfig), modelConfig); err != nil {
			log.Errorf("Assistant服务解析智能体模型配置失败，assistantId: %s, error: %v, modelConfigRaw: %s", req.AssistantId, err, assistant.ModelConfig)
			if ctx.Err() != nil {
				saveConversation(ctx, req, "本次回答已被终止", "")
				return ctx.Err()
			}
			SSEError(stream, "智能体模型配置解析失败")
			return err
		}
		log.Debugf("Assistant服务成功解析智能体模型配置，assistantId: %s, provider: %s, model: %s, modelId: %s, modelType: %s",
			req.AssistantId, modelConfig.Provider, modelConfig.Model, modelConfig.ModelId, modelConfig.ModelType)

		modelEndpoint := mp.ToModelEndpoint(modelConfig.ModelId, modelConfig.Model)
		log.Debugf("Assistant服务生成模型端点，assistantId: %s, modelEndpoint: %+v", req.AssistantId, modelEndpoint)
		requestBody["model"] = modelEndpoint["model"]
		requestBody["model_url"] = modelEndpoint["model_url"]

		_, modelParams, _ := mp.ToModelParams(modelConfig.Provider, modelConfig.ModelType, modelConfig.Config)
		log.Debugf("Assistant服务生成模型参数，assistantId: %s, modelParams: %+v", req.AssistantId, modelParams)
		if modelParams != nil {
			requestBody = mergeMaps(requestBody, modelParams)
		}
	} else {
		log.Warnf("Assistant服务智能体模型配置为空，assistantId: %s", req.AssistantId)
	}

	onlineSearchConfig := &AppOnlineSearchConfig{}
	log.Debugf("Assistant服务解析智能体在线搜索配置，assistantId: %s, onlineSearchConfig: %+v", req.AssistantId, assistant.OnlineSearchConfig)
	if assistant.OnlineSearchConfig != "" {
		if err := json.Unmarshal([]byte(assistant.OnlineSearchConfig), onlineSearchConfig); err != nil {
			log.Errorf("Assistant服务解析智能体在线搜索配置失败，assistantId: %s, error: %v, onlineSearchConfigRaw: %s", req.AssistantId, err, assistant.OnlineSearchConfig)
			if ctx.Err() != nil {
				saveConversation(ctx, req, "本次回答已被终止", "")
				return ctx.Err()
			}
			SSEError(stream, "智能体在线搜索配置解析失败")
			return err
		}
		log.Debugf("Assistant服务解析智能体在线搜索配置，assistantId: %s, onlineSearchConfig: %+v", req.AssistantId, onlineSearchConfig)
	}
	if onlineSearchConfig.Enable && onlineSearchConfig.SearchUrl != "" && onlineSearchConfig.SearchKey != "" {
		requestBody["search_url"] = onlineSearchConfig.SearchUrl
		requestBody["search_key"] = onlineSearchConfig.SearchKey
		requestBody["search_rerank_id"] = onlineSearchConfig.SearchRerankId
		requestBody["use_search"] = true
		log.Debugf("Assistant服务添加在线搜索配置到请求参数，assistantId: %s, search_url: %s, search_key: %s, use_search: %v", req.AssistantId, onlineSearchConfig.SearchUrl, onlineSearchConfig.SearchKey, onlineSearchConfig.Enable)
	}

	knowledgebaseConfig := &AppKnowledgebaseConfig{}
	if assistant.KnowledgebaseConfig != "" {
		// 将string类型的knowledgebase_config转换为common.AppKnowledgebaseConfig
		if err := json.Unmarshal([]byte(assistant.KnowledgebaseConfig), knowledgebaseConfig); err != nil {
			log.Errorf("Assistant服务解析智能体知识库配置失败，assistantId: %s, error: %v, knowledgebaseConfigRaw: %s", req.AssistantId, err, assistant.KnowledgebaseConfig)
			if ctx.Err() != nil {
				saveConversation(ctx, req, "本次回答已被终止", "")
				return ctx.Err()
			}
			SSEError(stream, "智能体知识库配置解析失败")
			return err
		}
	}
	if len(knowledgebaseConfig.Knowledgebases) > 0 {
		rerankConfig := &common.AppModelConfig{}
		if assistant.RerankConfig != "" {
			// 将string类型的assistant.RerankConfig转换为common.AppModelConfig
			if err := json.Unmarshal([]byte(assistant.RerankConfig), rerankConfig); err != nil {
				log.Errorf("Assistant服务解析智能体rerank配置失败，assistantId: %s, error: %v, rerankConfigRaw: %s", req.AssistantId, err, assistant.RerankConfig)
				if ctx.Err() != nil {
					saveConversation(ctx, req, "本次回答已被终止", "")
					return ctx.Err()
				}
				SSEError(stream, "智能体rerank配置解析失败")
				return err
			}
		}
		if rerankConfig.Model == "" || rerankConfig.ModelId == "" {
			log.Errorf("Assistant服务缺少rerank配置，assistantId: %s", req.AssistantId)
			if ctx.Err() != nil {
				saveConversation(ctx, req, "本次回答已被终止", "")
				return ctx.Err()
			}
			SSEError(stream, "智能体缺少rerank配置")
			return err
		}

		rerankEndpoint := mp.ToModelEndpoint(rerankConfig.ModelId, rerankConfig.Model)

		names := make([]string, 0, len(knowledgebaseConfig.Knowledgebases))
		for _, kb := range knowledgebaseConfig.Knowledgebases {
			names = append(names, kb.Name)
		}
		requestBody["kn_params"] = map[string]interface{}{
			"knowledgeBase": names,
			"rerank_id":     rerankConfig.ModelId,
			"model":         rerankEndpoint["model"],
			"model_url":     rerankEndpoint["model_url"],
		}
		requestBody["use_know"] = true
		requestBody["model_id"] = modelConfig.ModelId
	}

	// 如果不是试用模式，查询历史聊天记录并添加到请求参数中
	if !req.Trial && req.ConversationId != "" {
		// 组装查询条件
		fieldConditions := map[string]interface{}{
			"conversationId": req.ConversationId,
			"userId":         reqUserId,
			"orgId":          req.Identity.OrgId,
		}

		// 使用通配符查询所有对话详情索引
		indexPattern := "conversation_detail_infos_*"

		// 从ES查询历史聊天记录，查询所有记录用于构建history
		documents, _, err := es.Assistant().SearchByFields(ctx, indexPattern, fieldConditions, 0, 1000)
		if err != nil {
			log.Warnf("Assistant服务查询历史聊天记录失败，conversationId: %s, userId: %s, error: %v", req.ConversationId, reqUserId, err)
		} else {
			// 解析查询结果并构建history数组
			var historyList []AssistantConversionHistory
			for _, doc := range documents {
				var detail model.ConversationDetails
				if err := json.Unmarshal(doc, &detail); err != nil {
					log.Warnf("Assistant服务解析ES历史聊天记录失败: %v", err)
					continue
				}

				history := AssistantConversionHistory{
					Query:         detail.Prompt,
					UploadFileUrl: detail.FileUrl,
					Response:      detail.Response,
				}
				historyList = append(historyList, history)
			}

			// 将history添加到请求参数中
			requestBody["history"] = historyList
			log.Debugf("Assistant服务添加历史聊天记录到请求参数，conversationId: %s, 历史记录数: %d", req.ConversationId, len(historyList))
		}
	}

	// 向底层智能体能力接口发起请求
	requestBodyBytes, err := json.Marshal(requestBody)
	if err != nil {
		log.Errorf("Assistant服务序列化请求体失败，assistantId: %s, error: %v", req.AssistantId, err)
		if ctx.Err() != nil {
			saveConversation(ctx, req, "本次回答已被终止", "")
			return ctx.Err()
		}
		SSEError(stream, "请求参数错误")
		return err
	}

	timeout := 300 * time.Second
	requestCtx, cancelFunc := context.WithTimeout(ctx, timeout)
	defer cancelFunc()

	startTime := time.Now()
	id := uuid.New().String()
	log.Infof("Assistant服务开始调用HttpRequestLlmStream，uuid: %s, assistantId: %s, url: %s, userId: %s, timeout: %v, body: %s",
		id, req.AssistantId, assistantConfig.SseUrl, reqUserId, timeout, string(requestBodyBytes))
	sseResp, err := HttpRequestLlmStream(requestCtx, assistantConfig.SseUrl, reqUserId, xuid, bytes.NewReader(requestBodyBytes))
	if err != nil {
		log.Errorf("Assistant服务调用智能体能力接口失败，assistantId: %s, uuid: %s, error: %v", req.AssistantId, id, err)
		if ctx.Err() != nil {
			saveConversation(ctx, req, "本次回答已被终止", "")
			return ctx.Err()
		}
		SSEError(stream, "智能体服务异常")
		return err
	}
	defer sseResp.Body.Close()
	log.Infof("Assistant服务成功连接智能体能力接口，uuid: %s, assistantId: %s, statusCode: %d, time: %v毫秒", id, req.AssistantId, sseResp.StatusCode, time.Since(startTime).Milliseconds())

	// SSE 请求返回Code大于400
	if sseResp.StatusCode > http.StatusBadRequest {
		log.Errorf("Assistant服务智能体能力接口返回错误状态码，assistantId: %s, statusCode: %d", req.AssistantId, sseResp.StatusCode)
		if ctx.Err() != nil {
			saveConversation(ctx, req, "本次回答已被终止", "")
			return ctx.Err()
		}
		SSEError(stream, "智能体服务异常")
		return fmt.Errorf("智能体服务返回错误状态码: %d", sseResp.StatusCode)
	}

	// 读取智能体接口返回，并写入流式响应
	reader := bufio.NewReader(sseResp.Body)
	lineCount := 0

	// 初始化聊天记录数据
	var fullResponse strings.Builder
	var searchList string
	searchListExtracted := false
	hasReadFirstMessage := false

	for {
		if err := ctx.Err(); err != nil {
			if !hasReadFirstMessage {
				// 如果还没有读取到第一条消息，保存终止消息
				saveConversation(ctx, req, "本次回答已被终止", searchList)
			} else {
				// 如果已经读取到消息，保存已经收到的消息
				saveConversation(ctx, req, fullResponse.String(), searchList)
			}
			return err
		}

		line, err := reader.ReadBytes('\n')
		if err != nil && err != io.ErrUnexpectedEOF && err != io.EOF {
			log.Errorf("Assistant服务读取流式响应失败，assistantId: %s, error: %v, 已处理行数: %d", req.AssistantId, err, lineCount)
			if ctx.Err() != nil {
				if !hasReadFirstMessage {
					// 如果还没有读取到第一条消息，保存终止消息
					saveConversation(ctx, req, "本次回答已被终止", searchList)
				} else {
					// 如果已经读取到消息，保存已经收到的消息
					saveConversation(ctx, req, fullResponse.String(), searchList)
				}
				return ctx.Err()
			}
			SSEError(stream, "智能体响应中断")
			return err
		}

		strLine := string(line)
		lineCount++

		if len(strLine) >= 5 && strLine[:5] == "data:" {

			jsonStrData := strLine[5:]

			// 解析流式数据，提取response字段和search_list
			var streamData map[string]interface{}
			if err := json.Unmarshal([]byte(jsonStrData), &streamData); err == nil {
				if response, ok := streamData["response"].(string); ok && response != "" {
					fullResponse.WriteString(response)
				}

				// 提取第一个search_list
				if !searchListExtracted {
					if searchListData, ok := streamData["search_list"]; ok {
						searchListBytes, err := json.Marshal(searchListData)
						if err == nil {
							searchList = string(searchListBytes)
							searchListExtracted = true
							log.Debugf("Assistant服务提取到search_list，assistantId: %s, searchList: %s", req.AssistantId, searchList)
						}
					}
				}
			}

			if err := stream.Send(&assistant_service.AssistantConversionStreamResp{
				Content: jsonStrData,
			}); err != nil {
				log.Errorf("Assistant服务发送流式响应失败，assistantId: %s, error: %v", req.AssistantId, err)
				return err
			}

			// 标记已读取到并返回了第一条有效消息
			if !hasReadFirstMessage {
				hasReadFirstMessage = true
			}

		}

		if err != nil && (err == io.ErrUnexpectedEOF || err == io.EOF) {
			log.Debugf("Assistant服务流式响应结束，assistantId: %s, 总处理行数: %d", req.AssistantId, lineCount)
			break
		}
	}

	// 问答调试不保存
	if !req.Trial {
		saveConversation(ctx, req, fullResponse.String(), searchList)
	}

	return nil
}

// 使用独立上下文保存对话的辅助函数
func saveConversation(originalCtx context.Context, req *assistant_service.AssistantConversionStreamReq, response, searchList string) {
	// 如果原始上下文已取消，创建一个新的独立上下文
	if originalCtx.Err() != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()

		if err := saveConversationDetailToES(ctx, req, response, searchList); err != nil {
			log.Errorf("保存聊天记录到ES失败，assistantId: %s, conversationId: %s, error: %v",
				req.AssistantId, req.ConversationId, err)
		}
		return
	}

	// 原始上下文未取消时，继续使用它
	if err := saveConversationDetailToES(originalCtx, req, response, searchList); err != nil {
		log.Errorf("保存聊天记录到ES失败，assistantId: %s, conversationId: %s, error: %v",
			req.AssistantId, req.ConversationId, err)
	}
}

type AssistantConversionHistory struct {
	Query         string `json:"query"`
	UploadFileUrl string `json:"upload_file_url"`
	Response      string `json:"response"`
}

type PluginListAlgRequest struct {
	APISchema map[string]interface{} `json:"api_schema"`
	APIAuth   *APIAuth               `json:"api_auth"`
}

type APIAuth struct {
	Type  string `json:"type"`
	In    string `json:"in"`
	Name  string `json:"name"`
	Value string `json:"value"`
}

type AppKnowledgebaseConfig struct {
	Knowledgebases []AppKnowledgeBase     `json:"knowledgebases"`
	Config         AppKnowledgebaseParams `json:"config"`
}

type AppKnowledgeBase struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

type AppKnowledgebaseParams struct {
	MaxHistory       int  `json:"max_history"`
	MaxHistoryEnable bool `json:"max_history_enable"`
	Threshold        int  `json:"threshold"`
	ThresholdEnable  bool `json:"threshold_enable"`
	TopK             int  `json:"top_k"`
	TopKEnable       bool `json:"top_k_enable"`
}

type AppOnlineSearchConfig struct {
	SearchUrl      string `json:"searchUrl"`
	SearchKey      string `json:"searchKey"`
	SearchRerankId string `json:"SearchRerankId"`
	Enable         bool   `json:"enable"`
}

func mergeMaps(map1, map2 map[string]interface{}) map[string]interface{} {
	result := make(map[string]interface{})
	for k, v := range map1 {
		result[k] = v
	}
	for k, v := range map2 {
		result[k] = v // 若 key 重复，map2 的值覆盖 map1
	}
	return result
}

func buildWorkflowPluginListAlgParam(ctx context.Context, s *Service, assistantId, userId, orgId string) (pluginList []PluginListAlgRequest, err error) {
	pluginList = []PluginListAlgRequest{}
	resp, status := s.cli.GetAssistantWorkflowsByAssistantID(ctx, assistantId)
	if status != nil {
		return pluginList, errStatus(errs.Code_AssistantConversationErr, status)
	}
	for _, assistantWorkFlowModel := range resp {
		log.Infof("Assistant服务查询到workflow，assistantId: %s, workflowId: %s, enable: %v",
			assistantId, assistantWorkFlowModel.WorkflowId, assistantWorkFlowModel.Enable)
		if !assistantWorkFlowModel.Enable {
			continue
		}
		tmp := PluginListAlgRequest{}
		schema, err := util.ValidateOpenAPISchema(assistantWorkFlowModel.APISchema)
		if err != nil {
			return pluginList, err
		}
		// 将*openapi3.T转换为map[string]interface{}
		bytes, err := json.Marshal(schema)
		if err != nil {
			return pluginList, err
		}
		err = json.Unmarshal(bytes, &tmp.APISchema)
		if err != nil {
			return pluginList, err
		}
		if assistantWorkFlowModel.Type == "apiKey" {
			apiAuth := APIAuth{
				Type:  "apiKey",
				In:    "query",
				Name:  assistantWorkFlowModel.CustomHeaderName,
				Value: assistantWorkFlowModel.APIKey,
			}
			tmp.APIAuth = &apiAuth
		}
		//TODO 适配 assistantActionModel.Type ==None情况
		pluginList = append(pluginList, tmp)
	}
	log.Infof("Assistant服务查询到workflow，assistantId: %s, workflowList: %v", assistantId, pluginList)
	return pluginList, nil
}

func buildActionPluginListAlgParam(ctx context.Context, s *Service, assistantId, userId, orgId string) (pluginList []PluginListAlgRequest, err error) {
	pluginList = []PluginListAlgRequest{}
	resp, status := s.cli.GetAssistantActionsByAssistantID(ctx, assistantId)
	if status != nil {
		return pluginList, errStatus(errs.Code_AssistantConversationErr, status)
	}
	for _, assistantActionModel := range resp {
		if !assistantActionModel.Enable {
			continue
		}
		tmp := PluginListAlgRequest{}
		schema, err := util.ValidateOpenAPISchema(assistantActionModel.APISchema)
		if err != nil {
			return pluginList, err
		}
		// 将*openapi3.T转换为map[string]interface{}
		bytes, err := json.Marshal(schema)
		if err != nil {
			return pluginList, err
		}
		err = json.Unmarshal(bytes, &tmp.APISchema)
		if err != nil {
			return pluginList, err
		}

		if assistantActionModel.Type == "apiKey" {
			apiAuth := APIAuth{
				Type:  "apiKey",
				In:    "query",
				Name:  assistantActionModel.CustomHeaderName,
				Value: assistantActionModel.APIKey,
			}
			tmp.APIAuth = &apiAuth
		}
		//TODO 适配 assistantActionModel.Type ==None情况
		pluginList = append(pluginList, tmp)
	}

	return pluginList, nil
}

// SSEError 发送SSE错误响应
func SSEError(stream assistant_service.AssistantService_AssistantConversionStreamServer, message string) {
	log.Errorf("SSE错误: %s", message)
	// 通过流式响应发送错误信息
	if stream != nil {
		errorResponse := fmt.Sprintf("error:%s", message)
		if err := stream.Send(&assistant_service.AssistantConversionStreamResp{
			Content: errorResponse,
		}); err != nil {
			log.Errorf("发送SSE错误响应失败: %v", err)
		} else {
			log.Infof("成功发送SSE错误响应: %s", message)
		}
	} else {
		log.Warnf("stream为nil，无法发送SSE错误响应: %s", message)
	}
}

func HttpRequestLlmStream(ctx context.Context, url, userId, xuid string, body io.Reader) (*http.Response, error) {
	requestCtx, err := http.NewRequestWithContext(ctx, http.MethodPost, url, body)
	if err != nil {
		log.Errorf("HttpRequestLlmStream创建HTTP请求失败，url: %s, userId: %s, error: %v", url, userId, err)
		return nil, err
	}

	// 设置请求头
	requestCtx.Header.Set("Content-Type", "application/json")
	requestCtx.Header.Set("X-Uid", xuid)

	log.Debugf("HttpRequestLlmStream请求详情，url: %s, userId: %s, method: %s, headers: %+v",
		url, userId, requestCtx.Method, requestCtx.Header)

	// 创建客户端并发送请求
	client := &http.Client{Transport: &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}}

	response, err := client.Do(requestCtx)
	if err != nil {
		log.Errorf("HttpRequestLlmStream发送HTTP请求失败，url: %s, userId: %s, error: %v", url, userId, err)
		return nil, err
	}

	log.Debugf("HttpRequestLlmStream收到HTTP响应，url: %s, userId: %s, statusCode: %d, responseHeaders: %+v",
		url, userId, response.StatusCode, response.Header)

	return response, err
}

// saveConversationDetailToES 保存聊天记录到ES
func saveConversationDetailToES(ctx context.Context, req *assistant_service.AssistantConversionStreamReq, response, searchList string) error {
	// 根据当前时间生成索引名称，格式为conversation_detail_infos_YYYYMM
	now := time.Now()
	indexName := fmt.Sprintf("conversation_detail_infos_%d%02d", now.Year(), now.Month())

	// 组装ConversationDetails数据
	nowMilli := now.UnixMilli()
	conversationDetail := &model.ConversationDetails{
		Id:             uuid.New().String(),
		AssistantId:    req.AssistantId,
		ConversationId: req.ConversationId,
		Prompt:         req.Prompt,
		FileUrl:        req.FileInfo.FileUrl,
		FileSize:       req.FileInfo.FileSize,
		FileName:       req.FileInfo.FileName,
		Response:       response,
		SearchList:     searchList,
		UserId:         req.Identity.UserId,
		OrgId:          req.Identity.OrgId,
		CreatedAt:      nowMilli,
		UpdatedAt:      nowMilli,
	}

	// 写入ES
	if err := es.Assistant().IndexDocument(ctx, indexName, conversationDetail); err != nil {
		return fmt.Errorf("写入ES失败: %v", err)
	}

	log.Infof("成功保存聊天记录到ES，索引: %s, assistantId: %s, conversationId: %s",
		indexName, req.AssistantId, req.ConversationId)
	return nil
}

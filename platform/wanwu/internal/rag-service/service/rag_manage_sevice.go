package service

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"github.com/UnicomAI/wanwu/internal/rag-service/config"
	"net/http"
	"strconv"
	"time"

	knowledgeBase_service "github.com/UnicomAI/wanwu/api/proto/knowledgebase-service"
	rag_service "github.com/UnicomAI/wanwu/api/proto/rag-service"
	"github.com/UnicomAI/wanwu/internal/rag-service/client/model"
	http_client "github.com/UnicomAI/wanwu/internal/rag-service/pkg/http-client"
	"github.com/UnicomAI/wanwu/pkg/log"
)

const (
	DefaultThreshold  = 0.4
	DefaultTopK       = 5
	DefaultMaxHistory = 0
)

type RagChatParams struct {
	KnowledgeBase   string           `json:"knowledgeBase"`
	Question        string           `json:"question"`
	Threshold       float32          `json:"threshold"`
	TopK            int32            `json:"topK"`
	Stream          bool             `json:"stream"`
	Chichat         bool             `json:"chichat"` // 当知识库召回结果为空时是否使用默认话术（兜底），默认为true
	RerankModelId   string           `json:"rerank_model_id"`
	CustomModelInfo *CustomModelInfo `json:"custom_model_info"`
	History         []*HistoryItem   `json:"history"`
	MaxHistory      int32            `json:"maxHistory"`
}

type CustomModelInfo struct {
	LlmModelID string `json:"llm_model_id"`
}

type HistoryItem struct {
	Query       string `json:"query"`
	Response    string `json:"response"`
	NeedHistory bool   `json:"needHistory"`
}

func RagStreamChat(ctx context.Context, userId string, req *RagChatParams) (<-chan string, error) {
	log.Infof("ragStreamChat")
	params, err := buildHttpParams(userId, req)
	if err != nil {
		log.Errorf("build http params fail", "err", err)
		return nil, err
	}
	ret := make(chan string, 1024)
	go func() {
		// 确保通道最终被关闭
		defer close(ret)

		// 捕获 panic 并记录日志（不重新抛出，避免崩溃）
		defer func() {
			if r := recover(); r != nil {
				log.Errorf("RagStreamChat panic: %v", r)
			}
		}()

		//1.开启超时监控
		if params.Timeout == 0 {
			params.Timeout = time.Minute * 1
		}
		ctx, cancel := context.WithTimeout(ctx, params.Timeout)
		defer cancel()

		resp, err := http_client.GetClient().PostJsonOriResp(ctx, params)
		if err != nil {
			log.Errorf("request %+v rag stream err: %v", params, err)
			ret <- fmt.Sprintf("error: 调用下游服务失败: %v", err)
			return
		}
		defer resp.Body.Close() // 确保响应体关闭

		if resp.StatusCode != http.StatusOK {
			log.Errorf("request %+v rag stream returned non-OK status: %d", params, resp.StatusCode)
			ret <- fmt.Sprintf("error: 调用下游服务失败: %s", strconv.Itoa(resp.StatusCode))
			return
		}
		log.Infof("resp: %v", resp)
		scan := bufio.NewScanner(resp.Body)
		for scan.Scan() {
			ret <- scan.Text()
		}
		if err := scan.Err(); err != nil {
			log.Errorf("error reading stream from %v: %v", params, err)
			ret <- fmt.Sprintf("error: 调用下游服务失败: %s", strconv.Itoa(resp.StatusCode))
		}
	}()

	return ret, nil
}

func buildHttpParams(userId string, req *RagChatParams) (*http_client.HttpRequestParams, error) {
	log.Infof("build http param")
	url := fmt.Sprintf("%s%s", config.Cfg().RagServer.ChatEndpoint, config.Cfg().RagServer.ChatUrl)
	body, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	return &http_client.HttpRequestParams{
		Url:        url,
		Body:       body,
		Headers:    map[string]string{"X-uid": userId},
		Timeout:    time.Minute * 3,
		MonitorKey: "rag_search_service",
		LogLevel:   http_client.LogAll,
	}, nil
}

// BuildChatConsultParams 构造rag 会话参数
func BuildChatConsultParams(req *rag_service.ChatRagReq, rag *model.RagInfo, knowledge *knowledgeBase_service.KnowledgeInfo) *RagChatParams {
	// 判断enable状态
	ragChatParams := &RagChatParams{}
	if !rag.KnowledgeBaseConfig.MaxHistoryEnable {
		ragChatParams.MaxHistory = DefaultMaxHistory
	} else {
		ragChatParams.MaxHistory = int32(rag.KnowledgeBaseConfig.MaxHistory)
	}
	if !rag.KnowledgeBaseConfig.ThresholdEnable {
		ragChatParams.Threshold = DefaultThreshold
	} else {
		ragChatParams.Threshold = float32(rag.KnowledgeBaseConfig.Threshold)
	}
	if !rag.KnowledgeBaseConfig.TopKEnable {
		ragChatParams.TopK = DefaultTopK
	} else {
		ragChatParams.TopK = int32(rag.KnowledgeBaseConfig.TopK)
	}
	ragChatParams.CustomModelInfo = &CustomModelInfo{LlmModelID: rag.ModelConfig.ModelId}
	ragChatParams.KnowledgeBase = knowledge.Name
	ragChatParams.Question = req.Question
	ragChatParams.Stream = true
	ragChatParams.Chichat = true
	ragChatParams.RerankModelId = rag.RerankConfig.ModelId
	ragChatParams.History = []*HistoryItem{}
	log.Infof("ragparams = %+v", ragChatParams)
	return ragChatParams
}

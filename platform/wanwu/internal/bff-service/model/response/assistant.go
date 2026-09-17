package response

import (
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
)

type Assistant struct {
	AssistantId            string                         `json:"assistantId"  validate:"required"`
	request.AppBriefConfig                                // 基本信息
	Prologue               string                         `json:"prologue"`            // 开场白
	Instructions           string                         `json:"instructions"`        // 系统提示词
	RecommendQuestion      []string                       `json:"recommendQuestion"`   // 推荐问题
	ModelConfig            request.AppModelConfig         `json:"modelConfig"`         // 模型
	KnowledgeBaseConfig    request.AppKnowledgebaseConfig `json:"knowledgeBaseConfig"` // 知识库
	RerankConfig           request.AppModelConfig         `json:"rerankConfig"`        // Rerank模型
	OnlineSearchConfig     request.OnlineSearchConfig     `json:"onlineSearchConfig"`  // 在线搜索配置
	Scope                  int32                          `json:"scope"`               // 作用域
	ActionInfos            []*ActionInfos                 `json:"actionInfos"`         // action信息
	WorkFlowInfos          []*WorkFlowInfos               `json:"workFlowInfos"`       // 工作流信息
	CreatedAt              string                         `json:"createdAt"`           // 创建时间
	UpdatedAt              string                         `json:"updatedAt"`           // 更新时间
}

type ActionInfos struct {
	ActionId string `json:"actionId"`
	ApiName  string `json:"apiName"`
	Enable   bool   `json:"enable"`
}

type WorkFlowInfos struct {
	Id         string `json:"id"`
	WorkFlowId string `json:"workFlowId"`
	ApiName    string `json:"apiName"`
	Enable     bool   `json:"enable"`
}

type Action struct {
	ActionId   string              `json:"actionId"`
	Schema     string              `json:"schema"`
	SchemaType string              `json:"schemaType"`
	ApiAuth    ApiAuthWebRequest   `json:"apiAuth"`
	ApiList    []ActionApiResponse `json:"list"`
}

type ApiAuthWebRequest struct {
	Type             string `json:"type"`
	APIKey           string `json:"apiKey"`
	CustomHeaderName string `json:"customHeaderName"`
	AuthType         string `json:"authType"`
}

type ActionAddResponse struct {
	ActionId string              `json:"actionId"`
	ApiList  []ActionApiResponse `json:"list"`
}

type ActionApiResponse struct {
	Name   string `json:"name"`
	Method string `json:"method"`
	Path   string `json:"path"`
}

type ConversationInfo struct {
	ConversationId string `json:"conversationId"`
	AssistantId    string `json:"assistantId"`
	Title          string `json:"title"`
	CreatedAt      string `json:"createdAt"`
}

type ConversationDetailInfo struct {
	Id              string      `json:"id"`
	AssistantId     string      `json:"assistantId"`
	ConversationId  string      `json:"conversationId"`
	Prompt          string      `json:"prompt"`
	SysPrompt       string      `json:"sysPrompt"`
	Response        string      `json:"response"`
	SearchList      interface{} `json:"searchList"`
	QaType          int32       `json:"qa_type"`
	CreatedBy       string      `json:"createdBy"`
	CreatedAt       int64       `json:"createdAt"`
	UpdatedAt       int64       `json:"updatedAt"`
	RequestFileUrls []string    `json:"requestFileUrls"`
	FileSize        int64       `json:"fileSize"`
	FileName        string      `json:"fileName"`
}

type ConversationCreateResp struct {
	ConversationId string `json:"conversationId"`
}

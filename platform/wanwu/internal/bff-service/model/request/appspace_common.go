package request

import (
	"encoding/json"
	"fmt"

	mp "github.com/UnicomAI/wanwu/pkg/model-provider"
)

type Avatar struct {
	Key  string `json:"key"`  // 前端透传给后端用于保存avatar，例如：custom-upload/avatar/abc/def.png
	Path string `json:"path"` // 前端请求地址，例如：/v1/static/avatar/abc/def.png (请求非必填)
}

type AppBriefConfig struct {
	Avatar Avatar `json:"avatar"`                   // 图标
	Name   string `json:"name" validate:"required"` // 名称
	Desc   string `json:"desc"`                     // 描述
}

func (a AppBriefConfig) Check() error {
	return nil
}

type AppModelConfig struct {
	Provider    string      `json:"provider"`    // 模型供应商
	Model       string      `json:"model"`       // 模型名称
	ModelId     string      `json:"modelId"`     // 模型ID
	ModelType   string      `json:"modelType"`   // 模型类型(llm/embedding/rerank)
	DisplayName string      `json:"displayName"` // 模型展示名称(请求非必填)
	Config      interface{} `json:"config"`      // 模型配置

	Examples *mp.AppModelParams // 仅用于swagger展示；模型对应供应商中的对应llm、embedding或rerank结构是config实际的参数
}

func (cfg *AppModelConfig) Check() error {
	_, err := cfg.ConfigString()
	return err
}

func (cfg *AppModelConfig) ConfigString() (string, error) {
	if cfg.Config == nil {
		return "", nil
	}
	b, err := json.Marshal(cfg.Config)
	if err != nil {
		return "", fmt.Errorf("marshal app model config err: %v", err)
	}
	modelParams, _, err := mp.ToModelParams(cfg.Provider, cfg.ModelType, string(b))
	if err != nil {
		return "", err
	}
	b, err = json.Marshal(modelParams)
	if err != nil {
		return "", fmt.Errorf("marshal app model config err: %v", err)
	}
	return string(b), nil
}

type AppKnowledgebaseConfig struct {
	Knowledgebases []AppKnowledgeBase     `json:"knowledgebases"` // 知识库id、名字
	Config         AppKnowledgebaseParams `json:"config"`         // 知识库参数
}

type AppKnowledgeBase struct {
	ID   string `json:"id" validate:"required"` // 知识库id
	Name string `json:"name"`                   // 知识库名称(请求非必填)
}

type AppKnowledgebaseParams struct {
	MaxHistory       int32   `json:"maxHistory"`       // 最长上下文
	MaxHistoryEnable bool    `json:"maxHistoryEnable"` // 最长上下文(开关)
	Threshold        float32 `json:"threshold"`        // 过滤阈值
	ThresholdEnable  bool    `json:"thresholdEnable"`  // 过滤阈值(开关)
	TopK             int32   `json:"topK"`             // 知识条数
	TopKEnable       bool    `json:"topKEnable"`       // 知识条数(开关)
}

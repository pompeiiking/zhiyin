package mp_common

import (
	"encoding/json"
	"strings"

	"github.com/UnicomAI/wanwu/pkg/log"
)

type Header struct {
	Key   string `json:"key"`
	Value string `json:"value"`
}

// --- request ---

type ILLMReq interface {
	Stream() bool
	Data() map[string]interface{}
	OpenAIReq() (*OpenAILLMReq, bool)
}

type OpenAILLMReq struct {
	Model    string      `json:"model" validate:"required"`
	Messages []OpenAIMsg `json:"messages" validate:"required"`

	Stream         bool `json:"stream,omitempty"`
	MaxTokens      int  `json:"max_tokens,omitempty"`
	EnableThinking bool `json:"enable_thinking,omitempty"`

	Temperature float64 `json:"temperature,omitempty"`
	TopP        float64 `json:"top_p,omitempty"`
	TopK        int     `json:"top_k,omitempty"`
	MinP        float64 `json:"min_p,omitempty"`

	PresencePenalty   float64 `json:"presence_penalty,omitempty"`
	FrequencyPenalty  float64 `json:"frequency_penalty,omitempty"`
	RepetitionPenalty float64 `json:"repetition_penalty,omitempty"`

	Seed        int  `json:"seed,omitempty"`
	Logprobs    bool `json:"logprobs,omitempty"`
	TopLogprobs int  `json:"top_logprobs,omitempty"`
	N           int  `json:"n,omitempty"`

	ResponseFormat *OpenAIResponseFormat `json:"response_format,omitempty"`
	Stop           string                `json:"stop,omitempty"`

	User string `json:"user,omitempty"`

	//tools
}

type OpenAIMsg struct {
	Role    string `json:"role" validate:"required"` // "system" | "user" | "assistant" | "function(已弃用)"
	Content string `json:"content" validate:"required"`
}

type OpenAIResponseFormat struct {
	Type string `json:"type"` // "text" | "json"
}

// llmReq implementation of ILLMReq
type llmReq struct {
	data map[string]interface{}
}

func NewLLMReq(data map[string]interface{}) ILLMReq {
	return &llmReq{data: data}
}

func (req *llmReq) Data() map[string]interface{} {
	return req.data
}

func (req *llmReq) Stream() bool {
	if req.data == nil {
		return false
	}
	v, ok := req.data["stream"]
	if !ok {
		return false
	}
	stream, _ := v.(bool)
	return stream
}

func (req *llmReq) OpenAIReq() (*OpenAILLMReq, bool) {
	if req == nil {
		return nil, false
	}
	b, err := json.Marshal(req.data)
	if err != nil {
		log.Errorf("LLMReq to OpenAILLMReq marshal err: %v", err)
		return nil, false
	}
	ret := &OpenAILLMReq{}
	if err = json.Unmarshal(b, ret); err != nil {
		log.Errorf("LLMReq to OpenAILLMReq unmarshal err: %v", err)
		return nil, false
	}
	return ret, true
}

// --- response ---

type ILLMResp interface {
	String() string
	Data() (map[string]interface{}, bool)
	OpenAIResp() (*OpenAILLMResp, bool)
}

type OpenAILLMResp struct {
	ID      string             `json:"id"`      // 唯一标识
	Object  string             `json:"object"`  // 固定为 "chat.completion"
	Created int                `json:"created"` // 时间戳（秒）
	Model   string             `json:"model"`   // 使用的模型
	Choices []OpenAIRespChoice `json:"choices"` // 生成结果列表
	Usage   OpenAIRespUsage    `json:"usage"`   // token 使用统计
}

// OpenAIRespUsage 结构体表示 token 消耗
type OpenAIRespUsage struct {
	CompletionTokens int `json:"completion_tokens"` // 输出 token 数
	PromptTokens     int `json:"prompt_tokens"`     // 输入 token 数
	TotalTokens      int `json:"total_tokens"`      // 总 token 数
}

// OpenAIRespChoice 结构体表示单个生成选项
type OpenAIRespChoice struct {
	Index        int                  `json:"index"`             // 选项索引
	Message      *OpenAIRespChoiceMsg `json:"message,omitempty"` // 非流式生成的消息
	Delta        *OpenAIRespChoiceMsg `json:"delta,omitempty"`   // 流式生成的消息
	FinishReason string               `json:"finish_reason"`     // 停止原因
}

type OpenAIRespChoiceMsg struct {
	Content string `json:"content"`
	Role    string `json:"role"`
}

// llmResp implementation of ILLMResp
type llmResp struct {
	stream bool
	raw    string
}

func NewLLMResp(stream bool, raw string) ILLMResp {
	return &llmResp{stream: stream, raw: raw}
}

func (resp *llmResp) String() string {
	return resp.raw
}

func (resp *llmResp) Data() (map[string]interface{}, bool) {
	if resp.stream {
		if resp.raw == "data: [DONE]" || !strings.HasPrefix(resp.raw, "data:") {
			return nil, false
		}
	}

	raw := resp.raw
	if resp.stream {
		raw = strings.TrimPrefix(resp.raw, "data:")
	}

	ret := make(map[string]interface{})
	if err := json.Unmarshal([]byte(raw), &ret); err != nil {
		log.Errorf("llm stream resp (%v) convert to data err: %v", raw, err)
		return nil, false
	}
	return ret, true
}

func (resp *llmResp) OpenAIResp() (*OpenAILLMResp, bool) {
	if resp.stream {
		if resp.raw == "data: [DONE]" || !strings.HasPrefix(resp.raw, "data:") {
			return nil, false
		}
	}

	raw := resp.raw
	if resp.stream {
		raw = strings.TrimPrefix(resp.raw, "data:")
	}

	ret := &OpenAILLMResp{}
	if err := json.Unmarshal([]byte(raw), ret); err != nil {
		log.Errorf("llm stream resp (%v) convert to openai resp err: %v", raw, err)
		return nil, false
	}
	return ret, true
}

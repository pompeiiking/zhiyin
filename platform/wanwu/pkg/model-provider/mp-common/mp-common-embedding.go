package mp_common

import (
	"encoding/json"

	"github.com/UnicomAI/wanwu/pkg/log"
)

// --- request ---

type IEmbeddingReq interface {
	Data() map[string]interface{}
}

// embeddingReq implementation of IEmbeddingReq
type embeddingReq struct {
	data map[string]interface{}
}

func NewEmbeddingReq(data map[string]interface{}) IEmbeddingReq {
	return &embeddingReq{data: data}
}

func (req *embeddingReq) Data() map[string]interface{} {
	return req.data
}

// --- response ---

type IEmbeddingResp interface {
	String() string
	Data() (map[string]interface{}, bool)
}

// embeddingResp implementation of IEmbeddingResp
type embeddingResp struct {
	raw string
}

func NewEmbeddingResp(raw string) IEmbeddingResp {
	return &embeddingResp{raw: raw}
}

func (resp *embeddingResp) String() string {
	return resp.raw
}

func (resp *embeddingResp) Data() (map[string]interface{}, bool) {
	ret := make(map[string]interface{})
	if err := json.Unmarshal([]byte(resp.raw), &ret); err != nil {
		log.Errorf("embedding resp (%v) convert to data err: %v", resp.raw, err)
		return nil, false
	}
	return ret, true
}

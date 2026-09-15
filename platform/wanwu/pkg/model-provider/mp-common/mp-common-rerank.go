package mp_common

import (
	"encoding/json"

	"github.com/UnicomAI/wanwu/pkg/log"
)

// --- request ---

type IRerankReq interface {
	Data() map[string]interface{}
}

// rerankReq implementation of IRerankReq
type rerankReq struct {
	data map[string]interface{}
}

func NewRerankReq(data map[string]interface{}) IRerankReq {
	return &rerankReq{data: data}
}

func (req *rerankReq) Data() map[string]interface{} {
	return req.data
}

// --- response ---

type IRerankResp interface {
	String() string
	Data() (interface{}, bool)
}

// rerankResp implementation of IRerankResp
type rerankResp struct {
	raw string
}

func NewRerankResp(raw string) IRerankResp {
	return &rerankResp{raw: raw}
}

func (resp *rerankResp) String() string {
	return resp.raw
}

func (resp *rerankResp) Data() (interface{}, bool) {
	ret := make(map[string]interface{})
	if err := json.Unmarshal([]byte(resp.raw), &ret); err != nil {
		log.Errorf("rerank resp (%v) convert to data err: %v", resp.raw, err)
		return nil, false
	}
	return ret, true
}

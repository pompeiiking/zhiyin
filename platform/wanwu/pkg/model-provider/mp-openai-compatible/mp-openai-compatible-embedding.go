package mp_openai_compatible

import (
	"context"
	"crypto/tls"
	"fmt"
	"io"
	"net/url"

	mp_common "github.com/UnicomAI/wanwu/pkg/model-provider/mp-common"
	"github.com/go-resty/resty/v2"
)

type Embedding struct {
	ApiKey      string `json:"apiKey"`      // ApiKey
	EndpointUrl string `json:"endpointUrl"` // 推理url
}

func (cfg *Embedding) Embeddings(ctx context.Context, req mp_common.IEmbeddingReq, headers ...mp_common.Header) (mp_common.IEmbeddingResp, error) {
	if cfg.ApiKey != "" {
		headers = append(headers, mp_common.Header{
			Key:   "Authorization",
			Value: "Bearer " + cfg.ApiKey,
		})
	}

	request := resty.New().
		SetTLSClientConfig(&tls.Config{InsecureSkipVerify: true}). // 关闭证书校验
		SetTimeout(0).                                             // 关闭请求超时
		R().
		SetContext(ctx).
		SetHeader("Content-Type", "application/json").
		SetHeader("Accept", "application/json").
		SetBody(req.Data()).
		SetDoNotParseResponse(true)
	for _, header := range headers {
		request.SetHeader(header.Key, header.Value)
	}

	url := cfg.embeddingsUrl()
	resp, err := request.Post(url)
	if err != nil {
		return nil, fmt.Errorf("request %v openai compatible embeddings err: %v", url, err)
	} else if resp.StatusCode() >= 300 {
		return nil, fmt.Errorf("request %v openai compatible embeddings http status %v msg: %v", url, resp.StatusCode(), resp.String())
	}
	b, err := io.ReadAll(resp.RawResponse.Body)
	if err != nil {
		return nil, fmt.Errorf("request %v openai compatible embeddings read response body err: %v", url, err)
	}
	return mp_common.NewEmbeddingResp(string(b)), nil
}

func (cfg *Embedding) embeddingsUrl() string {
	ret, _ := url.JoinPath(cfg.EndpointUrl, "/embeddings")
	return ret
}

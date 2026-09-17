package middleware

import (
	"encoding/json"
	"io"
	"strings"

	err_code "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/bff-service/config"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	"github.com/UnicomAI/wanwu/pkg/log"

	"github.com/gin-gonic/gin"
)

func Record(ctx *gin.Context) {
	var req string
	var err error
	if ctx.ContentType() == gin.MIMEJSON {
		if req, err = requestBody(ctx); err != nil {
			log.Errorf("[%v] | %v | %v", ctx.Request.Method, requestFullPath(ctx), err)
			gin_util.ResponseErrCodeKey(ctx, err_code.Code_BFFInvalidArg, "", err.Error())
			ctx.Abort()
			return
		}
	}
	ctx.Next()

	resp := ctx.GetString(config.RESULT)
	log.Debugf("[%v] %v | %v | %v", ctx.Request.Method, requestFullPath(ctx), req, resp)
}

func requestFullPath(ctx *gin.Context) string {
	if ctx.Request.URL.RawQuery != "" {
		return ctx.Request.URL.Path + "?" + ctx.Request.URL.RawQuery
	}
	return ctx.Request.URL.Path
}

func requestBody(ctx *gin.Context) (string, error) {
	var body []byte
	var err error
	if cb, ok := ctx.Get(gin.BodyBytesKey); ok {
		if cbb, ok := cb.([]byte); ok {
			body = cbb
		}
	}
	if body == nil {
		body, err = io.ReadAll(ctx.Request.Body)
		if err != nil {
			return "", err
		}
		ctx.Set(gin.BodyBytesKey, body)
	}

	// avoid err: unexpected end of JSON input
	if strings.TrimSpace(string(body)) == "" {
		return "", nil
	}

	kv := make(map[string]interface{})
	if err = json.Unmarshal(body, &kv); err != nil {
		return "", err
	}
	if b, err := json.Marshal(kv); err != nil {
		return "", err
	} else {
		return string(b), nil
	}
}

package middleware

import (
	"fmt"
	"net/http"
	"strings"

	err_code "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/bff-service/config"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	"github.com/UnicomAI/wanwu/internal/bff-service/service"
	"github.com/gin-gonic/gin"
	"google.golang.org/grpc/codes"
)

func AuthOpenAPI(appType string) func(*gin.Context) {
	return func(ctx *gin.Context) {
		token, err := getApiKey(ctx)
		if err != nil {
			gin_util.ResponseDetail(ctx, http.StatusUnauthorized, codes.Code(err_code.Code_BFFAuth), nil, err.Error())
			ctx.Abort()
			return
		}
		apiKey, err := service.GetApiKeyByKey(ctx, token)
		if err != nil {
			gin_util.ResponseDetail(ctx, http.StatusUnauthorized, codes.Code(err_code.Code_BFFAuth), nil, err.Error())
			ctx.Abort()
			return
		}
		if apiKey.AppType != appType {
			gin_util.ResponseDetail(ctx, http.StatusUnauthorized, codes.Code(err_code.Code_BFFAuth), nil, "invalid appType")
			ctx.Abort()
			return
		}
		ctx.Set(config.USER_ID, apiKey.UserId)
		ctx.Set(config.X_ORG_ID, apiKey.OrgId)
		ctx.Set(config.APP_ID, apiKey.AppId)
	}

}

func getApiKey(ctx *gin.Context) (string, error) {
	authorization := ctx.Request.Header.Get("Authorization")
	if authorization != "" {
		tks := strings.Split(authorization, " ")
		if len(tks) > 1 && tks[0] == "Bearer" {
			return tks[1], nil
		} else {
			return "", fmt.Errorf("not Bearer token format")
		}
	} else {
		return "", fmt.Errorf("token is nil")
	}
}

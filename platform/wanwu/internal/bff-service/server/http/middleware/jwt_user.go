package middleware

import (
	"fmt"
	"net/http"
	"strings"
	"time"

	err_code "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/bff-service/config"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	jwt_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/jwt-util"
	"github.com/UnicomAI/wanwu/pkg/util"
	"github.com/gin-gonic/gin"
	"google.golang.org/grpc/codes"
)

func JWTUser(ctx *gin.Context) {
	token, err := getJWTToken(ctx)
	if err != nil {
		gin_util.ResponseDetail(ctx, http.StatusUnauthorized, codes.Code(err_code.Code_BFFJWT), nil, err.Error())
		ctx.Abort()
		return
	}
	jwtUserAuth(ctx, token)
}

func jwtUserAuth(ctx *gin.Context, token string) {
	httpStatus := http.StatusUnauthorized
	claims, err := jwt_util.ParseToken(token)
	if err != nil {
		gin_util.ResponseDetail(ctx, httpStatus, codes.Code(err_code.Code_BFFJWT), nil, err.Error())
		ctx.Abort()
		return
	}
	if claims.Subject != config.USER {
		gin_util.ResponseDetail(ctx, httpStatus, codes.Code(err_code.Code_BFFJWT), nil, "token subject错误")
		ctx.Abort()
		return
	}

	// 生成新的token
	if claims.BufferTime <= time.Now().Unix() {
		newClaims, newToken, _ := jwt_util.GenerateToken(claims.UserID, jwt_util.UserTokenTimeout)
		ctx.Header("new-token", newToken)
		ctx.Header("new-expires-at", util.Int2Str(newClaims.ExpiresAt))
	}
	ctx.Set(config.CLAIMS, claims)
	ctx.Next()
}

// 从Header Authorization中获取Token
func getJWTToken(c *gin.Context) (token string, err error) {
	authorization := c.Request.Header.Get("Authorization")
	if authorization != "" {
		tks := strings.Split(authorization, " ")
		if len(tks) > 1 && tks[0] == "Bearer" {
			return tks[1], err
		} else {
			err = fmt.Errorf("not Bearer token format")
			return "", err
		}
	} else {
		return "", fmt.Errorf("token is nil")
	}
}

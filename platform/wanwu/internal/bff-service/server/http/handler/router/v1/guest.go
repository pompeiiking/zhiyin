package v1

import (
	"net/http"

	mid "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util/mid-wrap"
	v1 "github.com/UnicomAI/wanwu/internal/bff-service/server/http/handler/v1"
	"github.com/gin-gonic/gin"
)

func registerGuest(apiV1 *gin.RouterGroup) {
	apiV1.Static("/static", "./configs/microservice/bff-service/static")
	apiV1.Static("/cache", "./cache")

	mid.Sub("guest").Reg(apiV1, "/base/login", http.MethodPost, v1.Login, "用户登录")
	mid.Sub("guest").Reg(apiV1, "/base/captcha", http.MethodGet, v1.GetCaptcha, "获取验证码")
	mid.Sub("guest").Reg(apiV1, "/base/custom", http.MethodGet, v1.GetLogoCustomInfo, "自定义logo和title")
	mid.Sub("guest").Reg(apiV1, "/base/language/select", http.MethodGet, v1.GetLanguageSelect, "获取语言列表（用于下拉选择）")
}

package middleware

import (
	"encoding/json"

	"github.com/UnicomAI/wanwu/internal/bff-service/service"
	"github.com/UnicomAI/wanwu/pkg/log"
	"github.com/gin-gonic/gin"
	"github.com/gin-gonic/gin/binding"
)

func AppHistoryRecord(filedId, appType string) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		appID := getFieldValue(ctx, filedId)
		userID, _ := getUserID(ctx)
		ctx.Next()
		if appID == "" || userID == "" || appType == "" {
			log.Errorf("record user %v app %v type %v history err", userID, appID, appType)
			return
		}
		if err := service.AddAppHistoryRecord(ctx, userID, appID, appType); err != nil {
			log.Errorf("record user %v app %v type %v history err: %v", userID, appID, appType, err)
		}
	}
}

func getFieldValue(ctx *gin.Context, fieldName string) string {
	if binding.MIMEJSON != ctx.ContentType() {
		return ""
	}
	//获取原始数据
	body, err := requestBody(ctx)
	if err != nil || len(body) == 0 {
		return ""
	}
	//构造参数对应map
	paramsMap := make(map[string]interface{})
	err = json.Unmarshal([]byte(body), &paramsMap)
	if err != nil {
		return ""
	}
	//获取对应filed的值
	fieldValue := paramsMap[fieldName]
	if fieldValue == nil {
		return ""
	}
	retValue, ok := fieldValue.(string)
	if !ok {
		return ""
	}
	return retValue
}

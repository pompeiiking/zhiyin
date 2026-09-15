package v1

import (
	"net/http"

	mid "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util/mid-wrap"
	v1 "github.com/UnicomAI/wanwu/internal/bff-service/server/http/handler/v1"
	"github.com/gin-gonic/gin"
)

func registerModel(apiV1 *gin.RouterGroup) {
	mid.Sub("model").Reg(apiV1, "/model", http.MethodPost, v1.ImportModel, "模型导入")
	mid.Sub("model").Reg(apiV1, "/model", http.MethodPut, v1.UpdateModel, "导入模型更新")
	mid.Sub("model").Reg(apiV1, "/model", http.MethodDelete, v1.DeleteModel, "导入模型删除")
	mid.Sub("model").Reg(apiV1, "/model", http.MethodGet, v1.GetModel, "查询单个模型")
	mid.Sub("model").Reg(apiV1, "/model/list", http.MethodGet, v1.ListModels, "导入模型列表展示")
	mid.Sub("model").Reg(apiV1, "/model/status", http.MethodPut, v1.ChangeModelStatus, "模型启用/关闭")
}

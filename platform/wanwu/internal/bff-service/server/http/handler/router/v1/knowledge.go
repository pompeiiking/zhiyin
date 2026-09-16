package v1

import (
	"net/http"

	mid "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util/mid-wrap"
	v1 "github.com/UnicomAI/wanwu/internal/bff-service/server/http/handler/v1"
	"github.com/gin-gonic/gin"
)

func registerKnowledge(apiV1 *gin.RouterGroup) {
	// 知识库增删改查
	mid.Sub("knowledge").Reg(apiV1, "/knowledge", http.MethodPost, v1.CreateKnowledge, "创建知识库（文档分类）")
	mid.Sub("knowledge").Reg(apiV1, "/knowledge", http.MethodPut, v1.UpdateKnowledge, "修改知识库（文档分类）")
	mid.Sub("knowledge").Reg(apiV1, "/knowledge", http.MethodDelete, v1.DeleteKnowledge, "删除知识库（文档分类）")
	// 知识库文档
	mid.Sub("knowledge").Reg(apiV1, "/knowledge/doc/list", http.MethodGet, v1.GetDocList, "获取文档列表")
	mid.Sub("knowledge").Reg(apiV1, "/knowledge/doc/import", http.MethodPost, v1.ImportDoc, "上传文档")
	mid.Sub("knowledge").Reg(apiV1, "/knowledge/doc/import/tip", http.MethodGet, v1.GetDocImportTip, "获取知识库文档上传状态")
	mid.Sub("knowledge").Reg(apiV1, "/knowledge/doc", http.MethodDelete, v1.DeleteDoc, "删除文档")
	// 知识库文档切片
	mid.Sub("knowledge").Reg(apiV1, "/knowledge/doc/segment/list", http.MethodGet, v1.GetDocSegmentList, "获取文档切分结果")
	mid.Sub("knowledge").Reg(apiV1, "/knowledge/doc/segment/status/update", http.MethodPost, v1.UpdateDocSegmentStatus, "更新文档切片启用状态")
	// 知识库url文档导入
	mid.Sub("knowledge").Reg(apiV1, "/knowledge/doc/url/analysis", http.MethodPost, v1.AnalysisDocUrl, "解析url")
}

package import_service

import (
	"context"

	"github.com/UnicomAI/wanwu/internal/knowledge-service/client/model"
)

type CheckFileResult struct {
	DocInfo    *model.DocInfo
	Status     int
	ErrMessage string
}

type DocImportService interface {
	ImportType() int
	AnalyzeDoc(ctx context.Context, importTask *model.KnowledgeImportTask, importDocInfo *model.DocImportInfo) ([]*model.DocInfo, error)
	CheckDoc(ctx context.Context, importTask *model.KnowledgeImportTask, docList []*model.DocInfo) ([]*CheckFileResult, error)
	ImportDoc(ctx context.Context, importTask *model.KnowledgeImportTask, checkDocList []*CheckFileResult) ([]*model.DocInfo, error)
}

package request

import (
	"errors"
	"fmt"

	"github.com/UnicomAI/wanwu/pkg/util"
)

type KnowledgeSelectReq struct {
	Name string `json:"name" form:"name" `
	CommonCheck
}

type CreateKnowledgeReq struct {
	Name           string          `json:"name"  validate:"required"`
	Description    string          `json:"description"`
	EmbeddingModel *EmbeddingModel `json:"embeddingModelInfo" validate:"required"`
}

type UpdateKnowledgeReq struct {
	KnowledgeId string `json:"knowledgeId"   validate:"required"`
	Name        string `json:"name"   validate:"required"`
	Description string `json:"description"`
	CommonCheck
}

type EmbeddingModel struct {
	ModelId string `json:"modelId"  validate:"required"`
}

type DeleteKnowledge struct {
	KnowledgeId string `json:"knowledgeId" validate:"required"`
	CommonCheck
}

type CallbackUpdateDocStatusReq struct {
	DocId  string `json:"id" validate:"required"`
	Status int32  `json:"status" validate:"required"`
	CommonCheck
}

type SearchKnowledgeInfoReq struct {
	KnowledgeName string `json:"categoryName" form:"categoryName" validate:"required"`
	UserId        string `json:"userId" form:"userId" validate:"required"`
	OrgId         string `json:"orgId"`
	CommonCheck
}

func (c *CreateKnowledgeReq) Check() error {
	if !util.IsAlphanumeric(c.Name) {
		errMsg := fmt.Sprintf("知识库名称只能包含中文、数字、小写英文，符号之只能包含下划线和减号 参数(%v)", c.Name)
		return errors.New(errMsg)
	}
	return nil
}

package response

type KnowledgeListResp struct {
	KnowledgeList []*KnowledgeInfo `json:"knowledgeList"`
}

type CreateKnowledgeResp struct {
	KnowledgeId string `json:"knowledgeId"`
}

type EmbeddingModelInfo struct {
	ModelId string `json:"modelId"`
}

type KnowledgeInfo struct {
	KnowledgeId        string              `json:"knowledgeId"`        //知识库id
	Name               string              `json:"name"`               //知识库名称
	Description        string              `json:"description"`        //知识库描述
	DocCount           int                 `json:"docCount"`           //文档数量
	EmbeddingModelInfo *EmbeddingModelInfo `json:"embeddingModelInfo"` //embedding模型信息
}

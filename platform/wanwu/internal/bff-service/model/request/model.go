package request

type ImportOrUpdateModelRequest struct {
	ModelConfig
}

func (o *ImportOrUpdateModelRequest) Check() error {
	return o.ModelConfig.Check()
}

type DeleteModelRequest struct {
	Provider  string `json:"provider" form:"provider" validate:"required"`               // 模型供应商
	ModelType string `json:"modelType" validate:"required" enums:"llm,embedding,rerank"` // 模型类型
	Model     string `json:"model" validate:"required"`                                  // 模型名称
}

func (o *DeleteModelRequest) Check() error {
	return nil
}

type GetModelRequest struct {
	ModelType string `json:"modelType" form:"modelType" validate:"required"` // 模型类型
	Model     string `json:"model" form:"model" validate:"required"`         // 模型名称
	Provider  string `json:"provider" form:"provider" validate:"required"`   // 模型供应商
}

func (o *GetModelRequest) Check() error {
	return nil
}

type ListModelsRequest struct {
	ModelType   string `json:"modelType" form:"modelType" `    // 模型类型
	Provider    string `json:"provider" form:"provider"`       // 模型供应商
	DisplayName string `json:"displayName" form:"displayName"` // 模型显示名称
	IsActive    bool   `json:"isActive" form:"isActive"`       // 启用状态（true: 启用）
}

func (o *ListModelsRequest) Check() error {
	return nil
}

type ListTypeModelsRequest struct {
	ModelType string `json:"modelType" form:"modelType" ` // 模型类型
}

func (o *ListTypeModelsRequest) Check() error {
	return nil
}

type ModelStatusRequest struct {
	ModelType string `json:"modelType" validate:"required" enums:"llm,embedding,rerank"` // 模型类型
	Model     string `json:"model" validate:"required"`                                  // 模型名称
	IsActive  bool   `json:"isActive"`                                                   // 启用状态（true: 启用，false: 禁用）
	Provider  string `json:"provider" validate:"required"`                               // 模型供应商
}

func (o *ModelStatusRequest) Check() error {
	return nil
}

type ModelSelectRequest struct {
	ModelType string `json:"modelType" form:"modelType" validate:"required" enums:"llm,embedding,rerank"` // 模型类型
	Model     string `json:"model" form:"model" validate:"required"`                                      // 模型名称
	Provider  string `json:"provider" form:"provider" validate:"required"`                                // 模型供应商(初版：OpenAI-API-compatible)
}

func (o *ModelSelectRequest) Check() error {
	return nil
}

type GetModelByIdRequest struct {
	ModelId string `json:"modelId" form:"modelId" validate:"required"` // 模型的主键ID
}

func (o *GetModelByIdRequest) Check() error {
	return nil
}

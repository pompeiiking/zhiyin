package model

type RagInfo struct {
	ID    int64  `json:"id" gorm:"primaryKey;type:bigint(20) auto_increment;not null;"`
	RagID string `json:"ragId" gorm:"uniqueIndex:idx_unique_rag_id;column:rag_id;type:varchar(255);comment:ragId"`

	// 使用嵌入结构体（将字段直接映射到主表）
	BriefConfig         AppBriefConfig      `gorm:"embedded;embeddedPrefix:brief_"`
	ModelConfig         AppModelConfig      `gorm:"embedded;embeddedPrefix:model_"`
	RerankConfig        AppModelConfig      `gorm:"embedded;embeddedPrefix:rerank_"`
	KnowledgeBaseConfig KnowledgeBaseConfig `gorm:"embedded;embeddedPrefix:kb_"`
	PublicModel
}

type AppBriefConfig struct {
	Name       string `json:"name" gorm:"column:name;type:varchar(255);comment:应用名称"`
	Desc       string `json:"desc" gorm:"column:desc;type:varchar(255);comment:应用描述"`
	AvatarPath string `json:"avatarPath" gorm:"column:avatar_path;type:varchar(255);comment:应用图标"`
}

type AppModelConfig struct {
	Provider  string `json:"provider" gorm:"column:provider;type:varchar(255);comment:模型供应商"`
	Model     string `json:"model" gorm:"column:model;type:varchar(255);comment:模型名称"`
	ModelId   string `json:"modelId" gorm:"column:model_id;type:varchar(255);comment:模型ID"`
	ModelType string `json:"modelType" gorm:"column:model_type;type:varchar(255);comment:模型类型"`
	Config    string `json:"config" gorm:"column:config;type:varchar(255);comment:模型配置"`
}

type KnowledgeBaseConfig struct {
	KnowId           string  `json:"knowId" gorm:"column:know_id;type:text;comment:知识库ID"`
	MaxHistory       int64   `json:"maxHistory" gorm:"column:max_history;type:bigint(20);comment:最大历史记录"`
	MaxHistoryEnable bool    `json:"maxHistoryEnable" gorm:"column:max_history_enable;type:tinyint(1);comment:是否启用最大历史记录"`
	Threshold        float64 `json:"threshold" gorm:"column:threshold;type:float(10,2);comment:阈值"`
	ThresholdEnable  bool    `json:"thresholdEnable" gorm:"column:threshold_enable;type:tinyint(1);comment:是否启用阈值"`
	TopK             int64   `json:"topK" gorm:"column:top_k;type:bigint(20);comment:TopK"`
	TopKEnable       bool    `json:"topKEnable" gorm:"column:top_k_enable;type:tinyint(1);comment:是否启用TopK"`
}

type PublicModel struct {
	CreatedAt int64  `json:"createdAt" gorm:"autoCreateTime:milli;index:created_at;column:created_at;type:bigint(20);comment:创建时间"`
	UpdatedAt int64  `json:"updatedAt" gorm:"autoUpdateTime:milli;index:updated_at;column:updated_at;type:bigint(20);comment:更新时间"`
	OrgID     string `gorm:"index:org_id;column:org_id;type:varchar(255);comment:组织ID" json:"orgId"`
	UserID    string `gorm:"index:user_id;column:user_id;type:varchar(255);comment:用户ID" json:"userId"`
}

func (r RagInfo) TableName() string {
	return "rag_info"
}

package model

type AssistantWorkflow struct {
	ID               uint32 `gorm:"primarykey;column:id"`
	AssistantId      uint32 `gorm:"column:assistant_id;comment:智能体id"`
	WorkflowId       string `gorm:"column:workflow_id;comment:工作流id"`
	APISchema        string `gorm:"column:api_schema;type:longtext;comment:schema配置"`
	Name             string
	Method           string
	Path             string
	APIKey           string `gorm:"column:api_key;type:varchar(255);comment:'api_key'"`
	CustomHeaderName string `gorm:"column:custom_header_name;type:varchar(255);comment:'自定义header名称'"`
	AuthType         string `gorm:"column:auth_type;type:varchar(255);comment:'authType(basic/bearer/custom)'"`
	Type             string `gorm:"column:type;type:varchar(255);comment:'apiAuth认证类型(none/apiKey/oAuth)'"`
	Enable           bool   `gorm:"column:enable;comment:是否启用"`
	UserId           string `gorm:"column:user_id;index:idx_assistant_workflow_user_id;comment:用户id"`
	OrgId            string `gorm:"column:org_id;index:idx_assistant_workflow_org_id;comment:组织id"`
	CreatedAt        int64  `gorm:"autoCreateTime:milli;comment:创建时间"`
	UpdatedAt        int64  `gorm:"autoUpdateTime:milli;comment:更新时间"`
}

package model

type AssistantAction struct {
	ID               uint32 `gorm:"primarykey;column:id"`
	AssistantId      uint32 `gorm:"index:assistant_id;column:assistant_id;type:varchar(100);comment:'智能体id'"`
	ActionName       string `gorm:"column:action_name;type:varchar(255);comment:'action名称'"`
	APISchema        string `gorm:"column:api_schema;type:longtext;comment:'schema配置'"`
	APIAuth          string `gorm:"column:api_auth;type:text;comment:'auth配置'"`
	Name             string `gorm:"column:name;type:varchar(255);comment:'oauth名称'"`
	Method           string `gorm:"column:method;type:varchar(50);comment:'oauth方法'"`
	Path             string `gorm:"column:path;type:varchar(255);comment:'路径'"`
	APIKey           string `gorm:"column:api_key;type:varchar(255);comment:'api_key'"`
	CustomHeaderName string `gorm:"column:custom_header_name;type:varchar(255);comment:'自定义header名称'"`
	AuthType         string `gorm:"column:auth_type;type:varchar(255);comment:'authType(basic/bearer/custom)'"`
	Type             string `gorm:"column:type;type:varchar(255);comment:'apiAuth认证类型(none/apiKey/oAuth)'"`
	Enable           bool   `gorm:"column:enable;comment:是否启用"`
	UserId           string `gorm:"column:user_id;index:idx_assistant_action_user_id;comment:用户id"`
	OrgId            string `gorm:"column:org_id;index:idx_assistant_action_org_id;comment:组织id"`
	CreatedAt        int64  `gorm:"autoCreateTime:milli;comment:创建时间"`
	UpdatedAt        int64  `gorm:"autoUpdateTime:milli;comment:更新时间"`
}

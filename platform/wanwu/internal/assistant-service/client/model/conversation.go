package model

type Conversation struct {
	ID          uint32 `gorm:"primarykey;column:id;comment:对话Id"`
	AssistantId uint32 `gorm:"column:assistant_id;comment:'智能体id'"`
	Title       string `gorm:"column:title;type:text;comment:'对话标题'"`
	UserId      string `gorm:"column:user_id;index:idx_conversation_user_id;comment:用户id"`
	OrgId       string `gorm:"column:org_id;index:idx_conversation_org_id;comment:组织id"`
	CreatedAt   int64  `gorm:"autoCreateTime:milli;comment:创建时间"`
	UpdatedAt   int64  `gorm:"autoUpdateTime:milli;comment:更新时间"`
}

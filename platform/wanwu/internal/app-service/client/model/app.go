package model

type App struct {
	ID        uint32 `gorm:"primary_key"`
	CreatedAt int64  `gorm:"autoCreateTime:milli;index:idx_app_created_at"`
	UpdatedAt int64  `gorm:"autoUpdateTime:milli"`
	// 用户ID
	UserID string `gorm:"index:idx_app_user_id"`
	// 组织ID
	OrgID string `gorm:"index:idx_app_org_id"`
	// APP ID
	AppID string `gorm:"index:idx_app_app_id"`
	// 应用类型
	AppType string `gorm:"index:idx_app_app_type"`
	// 发布类型
	PublishType string `gorm:"index:idx_app_publish_type"`
}

package model

const TimeFormat = "2006-01-02 15:04:05"

type PublicModel struct {
	CreatedAt int64  `gorm:"autoCreateTime:milli;index:created_at;column:created_at;type:bigint" json:"createdAt"`
	UpdatedAt int64  `gorm:"autoUpdateTime:milli;column:updated_at;type:bigint" json:"updatedAt"`
	OrgID     string `gorm:"index:org_id;column:org_id;type:varchar(255);comment:组织ID" json:"orgId"`
	UserID    string `gorm:"index:user_id;column:user_id;type:varchar(255);comment:用户ID" json:"userId"`
}

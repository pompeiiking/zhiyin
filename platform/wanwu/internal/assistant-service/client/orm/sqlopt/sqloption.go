package sqlopt

import (
	"gorm.io/gorm"
)

type sqlOptions []SQLOption

func SQLOptions(opts ...SQLOption) sqlOptions {
	return opts
}

func (s sqlOptions) Apply(db *gorm.DB) *gorm.DB {
	for _, opt := range s {
		db = opt.Apply(db)
	}
	return db
}

type SQLOption interface {
	Apply(db *gorm.DB) *gorm.DB
}

type funcSQLOption func(db *gorm.DB) *gorm.DB

func (f funcSQLOption) Apply(db *gorm.DB) *gorm.DB {
	return f(db)
}

func WithID(id uint32) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("id = ?", id)
	})
}

func WithIDs(ids []uint32) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("id IN ?", ids)
	})
}

func WithOrgID(orgId string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("org_id = ?", orgId)
	})
}

func WithUserId(userId string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("user_id = ?", userId)
	})
}

func DataPerm(db *gorm.DB, userId, orgId string) *gorm.DB {
	if userId != "" && orgId == "" {
		//数据权限：所有org内本人，userId传有效值，orgId不传有效值
		return SQLOptions(
			WithUserId(userId),
		).Apply(db)
	} else if userId != "" && orgId != "" {
		//数据权限：本org内本人，userId和orgId都需要传有效值
		return SQLOptions(
			WithUserId(userId),
			WithOrgID(orgId),
		).Apply(db)
	} else if userId == "" && orgId != "" {
		//数据权限：本org内全部，userId不传有效值，orgId传有效值
		return SQLOptions(
			WithOrgID(orgId),
		).Apply(db)
	} else {
		//数据权限：全部
		return db
	}
}

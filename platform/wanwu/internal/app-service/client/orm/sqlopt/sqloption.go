package sqlopt

import (
	"github.com/UnicomAI/wanwu/pkg/constant"
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

func WithOrgID(orgID string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if orgID != "" {
			return db.Where("org_id = ?", orgID)
		}
		return db
	})
}

func WithUserID(userID string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if userID != "" {
			return db.Where("user_id = ?", userID)
		}
		return db
	})
}

func WithExcludeUserID(userID string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if userID != "" {
			return db.Where("user_id != ?", userID)
		}
		return db
	})
}

func WithID(Id string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if Id != "" {
			return db.Where("id = ?", Id)
		}
		return db
	})
}

func WithAppID(appID string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if appID != "" {
			return db.Where("app_id = ?", appID)
		}
		return db
	})
}

func WithAppType(appType string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if appType != "" {
			return db.Where("app_type = ?", appType)
		}
		return db
	})
}

func WithApiKey(apiKey string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if apiKey != "" {
			return db.Where("api_key = ?", apiKey)
		}
		return db
	})
}

func InAppIds(appIds []string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if len(appIds) > 0 {
			return db.Where("app_id IN ?", appIds)
		}
		return db
	})
}

func LikeName(name string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if name != "" {
			return db.Where("name LIKE ?", "%"+name+"%")
		}
		return db
	})
}

func Private() SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("publish_type = ? ", constant.AppPublishPrivate)
	})
}

func StartCreatedAt(startCreatedAt int64) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if startCreatedAt != 0 {
			return db.Where("created_at >= ?", startCreatedAt)
		}
		return db
	})
}

func EndCreatedAt(endCreatedAt int64) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if endCreatedAt != 0 {
			return db.Where("created_at <= ?", endCreatedAt)
		}
		return db
	})
}

func StartUpdatedAt(startUpdatedAt int64) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if startUpdatedAt != 0 {
			return db.Where("updated_at >= ?", startUpdatedAt)
		}
		return db
	})
}

func EndUpdatedAt(endUpdatedAt int64) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if endUpdatedAt != 0 {
			return db.Where("updated_at <= ?", endUpdatedAt)
		}
		return db
	})
}

func WithSearchType(userID, searchType string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		var query string
		var args []interface{}
		switch searchType {
		case "", "all":
			query = "user_id = ? AND publish_type = ?"
			args = append(args, userID, constant.AppPublishPrivate)
			query = "(" + query + ") OR " + "publish_type = ?"
			args = append(args, constant.AppPublishPublic)
		case "private":
			query = "user_id = ? AND publish_type = ?"
			args = append(args, userID, constant.AppPublishPrivate)
		}
		return db.Where(query, args...)
	})
}

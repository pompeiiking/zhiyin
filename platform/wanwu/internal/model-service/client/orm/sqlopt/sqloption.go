package sqlopt

import (
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
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

func WithProvider(provider string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if provider != "" {
			return db.Where("provider = ?", provider)
		}
		return db
	})
}

func WithModelType(modelType string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if modelType != "" {
			return db.Where("model_type = ?", modelType)
		}
		return db
	})
}

func WithModel(model string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if model != "" {
			return db.Where("model = ?", model)
		}
		return db
	})
}

func WithDisplayName(DisplayName string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if DisplayName != "" {
			return db.Where("display_name = ?", DisplayName)
		}
		return db
	})
}

func WithIsActive(isActive bool) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("is_active = ?", isActive)
	})
}

func LikeDisplayName(displayName string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if displayName != "" {
			return db.Where("display_name LIKE ?", "%"+displayName+"%")
		}
		return db
	})
}

func LikeDisplayNameOrModel(displayName string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if displayName != "" {
			return db.Where(
				"display_name LIKE ? OR (display_name='' AND model LIKE ?)",
				"%"+displayName+"%",
				"%"+displayName+"%",
			)
		}
		return db
	})
}

func WithUpdateLock() SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Clauses(clause.Locking{
			Strength: "UPDATE",
		})
	})
}

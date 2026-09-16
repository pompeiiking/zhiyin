package sqlopt

import (
	"gorm.io/gorm"
)

type SqlOptions []SQLOption

func SQLOptions(opts ...SQLOption) SqlOptions {
	return opts
}

func (s SqlOptions) Apply(db *gorm.DB, model interface{}) *gorm.DB {
	if model != nil {
		db = db.Model(model)
	}
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

func WithKnowledgeID(id string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("knowledge_id = ?", id)
	})
}

func WithImportID(id string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("import_id = ?", id)
	})
}

func WithDocIDs(ids []string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("doc_id in ?", ids)
	})
}

func WithIDs(ids []uint32) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("id IN ?", ids)
	})
}

func WithOrgID(orgID string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("org_id = ?", orgID)
	})
}

func WithUserID(userID string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("user_id = ?", userID)
	})
}

// WithPermit 权限查询条件
func WithPermit(orgID, userID string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if len(orgID) > 0 {
			return db.Where("org_id = ?", orgID)
		}
		if len(userID) > 0 {
			return db.Where("user_id = ?", userID)
		}
		return db
	})
}

func WithStatusList(status []int) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if len(status) == 0 {
			return db
		} else if len(status) == 1 {
			return db.Where("status = ?", status[0])
		}
		return db.Where("status IN ?", status)
	})
}

func WithoutStatus(status int) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("status != ?", status)
	})
}

func WithName(name string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if len(name) > 0 {
			return db.Where("name = ?", name)
		}
		return db
	})
}

func WithFilePathMd5(filePathMd5 string) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		if len(filePathMd5) > 0 {
			return db.Where("file_path_md5 = ?", filePathMd5)
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

func WithDelete(deleted int) SQLOption {
	return funcSQLOption(func(db *gorm.DB) *gorm.DB {
		return db.Where("deleted = ?", deleted)
	})
}

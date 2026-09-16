package config

// gin.Contex key
const (
	CLAIMS = "claims"
	STATUS = "STATUS"
	RESULT = "RESULT"

	// http header
	X_LANGUAGE = "X-Language" // 当前语言
	X_ORG_ID   = "X-Org-Id"   // 当前组织

	// gin.Context
	USER_ID   = "USER_ID"   // 当前用户
	IS_ADMIN  = "IS_ADMIN"  // USER_ID是否当前组织X_ORG_ID的内置管理员角色
	IS_SYSTEM = "IS_SYSTEM" // 当前组织X_ORG_ID是否是【系统】

	// openapi相关
	APP_ID   = "APP_ID"
	APP_TYPE = "APP_TYPE"

	ANSWER = "ANSWER"
)

// jwt subject
const (
	USER = "user"
)

// http common query key
const (
	PageNo   = "pageNo"
	PageSize = "pageSize"
)

// permission const
const (
	TopOrgID          = "1" // top org id
	SystemAdminUserID = "1" // system admin user id
)

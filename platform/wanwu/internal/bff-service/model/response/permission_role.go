package response

type RoleTemplate struct {
	Routes []Route `json:"routes"` // 一级路由
}

type Route struct {
	Name     string  `json:"name"`     // 路由名
	Perm     string  `json:"perm"`     // 权限
	Children []Route `json:"children"` // 子路由
}

type RoleID struct {
	RoleID string `json:"roleId"`
}

type RoleInfo struct {
	RoleID    string `json:"roleId"`
	Name      string `json:"name"`
	Remark    string `json:"remark"`
	CreatedAt string `json:"createdAt"`
	Creator   IDName `json:"creator"`
	Status    bool   `json:"status"`
	IsAdmin   bool   `json:"isAdmin"` // 是否组织内置管理员角色

	*RoleTemplate
	Permissions []Permission `json:"permissions"` // 权限列表
}

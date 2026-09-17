package request

type RoleCreate struct {
	Name   string `json:"name" validate:"required"` // 角色名
	Remark string `json:"remark"`                   // 备注

	Permissions []string // 权限列表
}

func (r *RoleCreate) Check() error {
	return nil
}

type RoleUpdate struct {
	RoleID string `json:"roleId" validate:"required"`
	RoleCreate
}

func (r *RoleUpdate) Check() error {
	return nil
}

type RoleID struct {
	RoleID string `json:"roleId" validate:"required"` // 角色ID
}

func (r *RoleID) Check() error {
	return nil
}

type RoleStatus struct {
	RoleID
	Status bool `json:"status"`
}

func (r *RoleStatus) Check() error {
	return nil
}

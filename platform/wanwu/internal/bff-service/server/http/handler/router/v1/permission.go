package v1

import (
	"net/http"

	mid "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util/mid-wrap"
	v1 "github.com/UnicomAI/wanwu/internal/bff-service/server/http/handler/v1"
	"github.com/gin-gonic/gin"
)

func registerPermission(apiV1 *gin.RouterGroup) {
	// permission.user
	mid.Sub("permission.user").Reg(apiV1, "/user", http.MethodPost, v1.CreateUser, "创建用户")
	mid.Sub("permission.user").Reg(apiV1, "/user", http.MethodPut, v1.ChangeUser, "编辑用户")
	mid.Sub("permission.user").Reg(apiV1, "/user", http.MethodDelete, v1.DeleteUser, "删除用户")
	mid.Sub("permission.user").Reg(apiV1, "/user/list", http.MethodGet, v1.GetUserList, "获取用户列表")
	mid.Sub("permission.user").Reg(apiV1, "/user/status", http.MethodPut, v1.ChangeUserStatus, "修改用户状态")
	mid.Sub("permission.user").Reg(apiV1, "/user/admin/password", http.MethodPut, v1.AdminChangeUserPassword, "重置用户密码（by 管理员）")
	mid.Sub("permission.user").Reg(apiV1, "/org/other/select", http.MethodGet, v1.GetOrgUserNotSelect, "获取不在组织中的用户列表（用于下拉选择）")
	mid.Sub("permission.user").Reg(apiV1, "/role/select", http.MethodGet, v1.GetRoleSelect, "获取组织角色列表（用于下拉选择）")
	mid.Sub("permission.user").Reg(apiV1, "/org/user", http.MethodPost, v1.AddOrgUser, "邀请用户加入组织")
	// permission.org
	mid.Sub("permission.org").Reg(apiV1, "/org", http.MethodPost, v1.CreateOrg, "创建下级组织")
	mid.Sub("permission.org").Reg(apiV1, "/org", http.MethodPut, v1.ChangeOrg, "编辑下级组织")
	mid.Sub("permission.org").Reg(apiV1, "/org", http.MethodDelete, v1.DeleteOrg, "删除下级组织")
	mid.Sub("permission.org").Reg(apiV1, "/org/info", http.MethodGet, v1.GetOrgInfo, "获取组织信息")
	mid.Sub("permission.org").Reg(apiV1, "/org/list", http.MethodGet, v1.GetOrgList, "获取下级组织列表")
	mid.Sub("permission.org").Reg(apiV1, "/org/status", http.MethodPut, v1.ChangeOrgStatus, "修改下级组织状态")
	// permission.role
	mid.Sub("permission.role").Reg(apiV1, "/role/template", http.MethodGet, v1.GetRoleTemplate, "获取角色模板（用于创建角色）")
	mid.Sub("permission.role").Reg(apiV1, "/role", http.MethodPost, v1.CreateRole, "创建角色")
	mid.Sub("permission.role").Reg(apiV1, "/role", http.MethodPut, v1.ChangeRole, "编辑角色")
	mid.Sub("permission.role").Reg(apiV1, "/role", http.MethodDelete, v1.DeleteRole, "删除角色")
	mid.Sub("permission.role").Reg(apiV1, "/role/info", http.MethodGet, v1.GetRoleInfo, "获取角色信息")
	mid.Sub("permission.role").Reg(apiV1, "/role/list", http.MethodGet, v1.GetRoleList, "获取角色列表")
	mid.Sub("permission.role").Reg(apiV1, "/role/status", http.MethodPut, v1.ChangeRoleStatus, "修改角色状态")
}

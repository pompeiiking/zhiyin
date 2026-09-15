package service

import (
	"fmt"
	"strings"

	iam_service "github.com/UnicomAI/wanwu/api/proto/iam-service"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/response"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	mid "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util/mid-wrap"
	"github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util/route"
	"github.com/UnicomAI/wanwu/pkg/util"
	"github.com/gin-gonic/gin"
)

func GetRoleTemplate(ctx *gin.Context, userID, orgID string) (*response.RoleTemplate, error) {
	resp, err := GetUserPermission(ctx, userID, orgID)
	if err != nil {
		return nil, err
	}
	routes := mid.CollectRoutes()
	ret := &response.RoleTemplate{}
	for _, r := range routes {
		if ok, sub := cutRoute(r, resp.OrgPermission.Permissions); ok {
			ret.Routes = append(ret.Routes, sub)
		}
	}
	return ret, nil
}

func CreateRole(ctx *gin.Context, creatorID, orgID string, roleCreate *request.RoleCreate) (*response.RoleID, error) {
	// creator permission
	creatorPermission, err := GetUserPermission(ctx, creatorID, orgID)
	if err != nil {
		return nil, err
	}
	// req
	req := &iam_service.CreateRoleReq{
		CreatorId: creatorID,
		OrgId:     orgID,
		Name:      roleCreate.Name,
		Remark:    roleCreate.Remark,
	}
	routes := mid.CollectPerms()
	for _, perm := range roleCreate.Permissions {
		var exist bool
		for _, p := range creatorPermission.OrgPermission.Permissions {
			if p.Perm != perm {
				continue
			}
			exist = true
			break
		}
		if !exist {
			return nil, fmt.Errorf("当前用户没有 %v 权限", perm)
		}
		for _, r := range routes {
			if strings.HasPrefix(perm, r.Tag) {
				var add bool
				for _, p := range req.Perms {
					if p.Perm == r.Tag {
						add = true
						break
					}
				}
				if !add {
					req.Perms = append(req.Perms, &iam_service.Perm{Perm: r.Tag})
				}
			}
		}
	}
	// create role
	resp, err := iam.CreateRole(ctx.Request.Context(), req)
	if err != nil {
		return nil, err
	}
	return &response.RoleID{RoleID: resp.Id}, nil
}

func ChangeRole(ctx *gin.Context, userID, orgID string, roleUpdate *request.RoleUpdate) error {
	// creator permission
	userPermission, err := GetUserPermission(ctx, userID, orgID)
	if err != nil {
		return err
	}
	// req
	req := &iam_service.UpdateRoleReq{
		OrgId:  orgID,
		RoleId: roleUpdate.RoleID,
		Name:   roleUpdate.Name,
		Remark: roleUpdate.Remark,
	}
	routes := mid.CollectPerms()
	for _, perm := range roleUpdate.Permissions {
		var exist bool
		for _, p := range userPermission.OrgPermission.Permissions {
			if p.Perm != perm {
				continue
			}
			exist = true
			break
		}
		if !exist {
			return fmt.Errorf("当前用户没有 %v 权限", perm)
		}
		for _, r := range routes {
			if strings.HasPrefix(perm, r.Tag) {
				var add bool
				for _, p := range req.Perms {
					if p.Perm == r.Tag {
						add = true
						break
					}
				}
				if !add {
					req.Perms = append(req.Perms, &iam_service.Perm{Perm: r.Tag})
				}
			}
		}
	}
	_, err = iam.UpdateRole(ctx.Request.Context(), req)
	return err
}

func DeleteRole(ctx *gin.Context, orgID, roleID string) error {
	_, err := iam.DeleteRole(ctx.Request.Context(), &iam_service.DeleteRoleReq{
		OrgId:  orgID,
		RoleId: roleID,
	})
	return err
}

func GetRoleInfo(ctx *gin.Context, userID, orgID, roleID string) (*response.RoleInfo, error) {
	role, err := iam.GetRoleInfo(ctx.Request.Context(), &iam_service.GetRoleInfoReq{
		OrgId:  orgID,
		RoleId: roleID,
	})
	if err != nil {
		return nil, err
	}
	template, err := GetRoleTemplate(ctx, userID, orgID)
	if err != nil {
		return nil, err
	}
	return toRoleInfo(role, template), nil
}

func GetRoleList(ctx *gin.Context, userID, orgID, name string, pageNo, pageSize int32) (*response.PageResult, error) {
	resp, err := iam.GetRoleList(ctx.Request.Context(), &iam_service.GetRoleListReq{
		OrgId:    orgID,
		Name:     name,
		PageNo:   pageNo,
		PageSize: pageSize,
	})
	if err != nil {
		return nil, err
	}
	template, err := GetRoleTemplate(ctx, userID, orgID)
	if err != nil {
		return nil, err
	}
	var roles []*response.RoleInfo
	for _, role := range resp.Roles {
		roles = append(roles, toRoleInfo(role, template))
	}
	return &response.PageResult{
		List:     roles,
		Total:    resp.Total,
		PageNo:   int(pageNo),
		PageSize: int(pageSize),
	}, nil
}

func ChangeRoleStatus(ctx *gin.Context, orgID, roleID string, status bool) error {
	_, err := iam.ChangeRoleStatus(ctx.Request.Context(), &iam_service.ChangeRoleStatusReq{
		OrgId:  orgID,
		RoleId: roleID,
		Status: status,
	})
	return err
}

// --- internal ---

func toRoleIDName(ctx *gin.Context, role *iam_service.RoleIDName) response.IDName {
	ret := response.IDName{
		ID:   role.Id,
		Name: role.Name,
	}
	if role.IsAdmin {
		if role.IsSystem {
			ret.Name = gin_util.I18nKey(ctx, "bff_role_system_admin_name")
		} else {
			ret.Name = gin_util.I18nKey(ctx, "bff_role_org_admin_name")
		}
	}
	return ret
}

func toRoleIDNames(ctx *gin.Context, roles []*iam_service.RoleIDName) []response.IDName {
	var ret []response.IDName
	for _, role := range roles {
		ret = append(ret, toRoleIDName(ctx, role))
	}
	return ret
}

func toRoleInfo(role *iam_service.RoleInfo, template *response.RoleTemplate) *response.RoleInfo {
	ret := &response.RoleInfo{
		RoleID:       role.RoleId,
		Name:         role.Name,
		Remark:       role.Remark,
		CreatedAt:    util.Time2Str(role.CreatedAt),
		Creator:      toIDName(role.Creator),
		Status:       role.Status,
		IsAdmin:      role.IsAdmin,
		RoleTemplate: template,
	}
	if role.IsAdmin {
		ret.Permissions = toPermissions(true, false, nil)
		return ret
	}
	for _, perm := range role.Perms {
		for _, route := range template.Routes {
			if ok, name := inRoute(route, perm.Perm); ok {
				ret.Permissions = append(ret.Permissions, response.Permission{
					Perm: perm.Perm,
					Name: name,
				})
				break
			}
		}
	}
	return ret
}

func inRoute(r response.Route, perm string) (bool, string) {
	if r.Perm == perm {
		return true, r.Name
	}
	for _, child := range r.Children {
		if ok, name := inRoute(child, perm); ok {
			return true, name
		}
	}
	return false, ""
}

func cutRoute(r route.Route, perms []response.Permission) (bool, response.Route) {
	var exist bool
	var ret response.Route
	for _, perm := range perms {
		if perm.Perm == r.Tag {
			exist = true
			ret.Perm = perm.Perm
			ret.Name = perm.Name
			break
		}
	}
	if !exist {
		return false, ret
	}
	for _, sub := range r.Subs {
		if ok, child := cutRoute(sub, perms); ok {
			ret.Children = append(ret.Children, child)
		}
	}
	return true, ret
}

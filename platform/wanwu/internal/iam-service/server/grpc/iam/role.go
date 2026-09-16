package iam

import (
	"context"
	"strconv"

	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	iam_service "github.com/UnicomAI/wanwu/api/proto/iam-service"
	"github.com/UnicomAI/wanwu/internal/iam-service/client/orm"
	"github.com/UnicomAI/wanwu/internal/iam-service/config"
	"github.com/UnicomAI/wanwu/pkg/util"
	"github.com/gromitlee/access/pkg/perm"
	"google.golang.org/protobuf/types/known/emptypb"
)

func (s *Service) GetRoleSelect(ctx context.Context, req *iam_service.GetRoleSelectReq) (*iam_service.GetRoleSelectResp, error) {
	roles, err := s.cli.SelectRoles(ctx, util.MustU32(req.OrgId))
	if err != nil {
		return nil, errStatus(errs.Code_IAMRole, err)
	}
	return &iam_service.GetRoleSelectResp{Roles: toRoleIDNames(roles)}, nil
}

func (s *Service) GetRoleList(ctx context.Context, req *iam_service.GetRoleListReq) (*iam_service.GetRoleListResp, error) {
	roles, count, err := s.cli.GetRoles(ctx, util.MustU32(req.OrgId), req.Name, toOffset(req), req.PageSize)
	if err != nil {
		return nil, errStatus(errs.Code_IAMRole, err)
	}
	resp := &iam_service.GetRoleListResp{
		Total:    count,
		PageNo:   req.PageNo,
		PageSize: req.PageSize,
	}
	for _, role := range roles {
		resp.Roles = append(resp.Roles, toRoleInfo(role))
	}
	return resp, nil
}

func (s *Service) GetRoleInfo(ctx context.Context, req *iam_service.GetRoleInfoReq) (*iam_service.RoleInfo, error) {
	role, err := s.cli.GetRole(ctx, util.MustU32(req.OrgId), util.MustU32(req.RoleId))
	if err != nil {
		return nil, errStatus(errs.Code_IAMRole, err)
	}
	return toRoleInfo(role), nil
}

func (s *Service) CreateRole(ctx context.Context, req *iam_service.CreateRoleReq) (*iam_service.RoleIDName, error) {
	var perms []perm.Perm
	for _, p := range req.Perms {
		perms = append(perms, perm.Perm{Obj: perm.Obj(p.Perm)})
	}
	roleID, err := s.cli.CreateRole(ctx, util.MustU32(req.OrgId), util.MustU32(req.CreatorId), req.Name, req.Remark, perms)
	if err != nil {
		return nil, errStatus(errs.Code_IAMRole, toErrStatus("iam_role_create", err.Error()))
	}
	return &iam_service.RoleIDName{
		Id:       strconv.Itoa(int(roleID)),
		Name:     req.Name,
		IsAdmin:  false,
		IsSystem: util.MustU32(req.OrgId) == config.TopOrgID(),
	}, nil
}

func (s *Service) UpdateRole(ctx context.Context, req *iam_service.UpdateRoleReq) (*emptypb.Empty, error) {
	var perms []perm.Perm
	for _, p := range req.Perms {
		perms = append(perms, perm.Perm{Obj: perm.Obj(p.Perm)})
	}
	if err := s.cli.UpdateRole(ctx, util.MustU32(req.OrgId), util.MustU32(req.RoleId), req.Name, req.Remark, perms); err != nil {
		return nil, errStatus(errs.Code_IAMRole, err)
	}
	return &emptypb.Empty{}, nil
}

func (s *Service) DeleteRole(ctx context.Context, req *iam_service.DeleteRoleReq) (*emptypb.Empty, error) {
	if err := s.cli.DeleteRole(ctx, util.MustU32(req.OrgId), util.MustU32(req.RoleId)); err != nil {
		return nil, errStatus(errs.Code_IAMRole, err)
	}
	return &emptypb.Empty{}, nil
}

func (s *Service) ChangeRoleStatus(ctx context.Context, req *iam_service.ChangeRoleStatusReq) (*emptypb.Empty, error) {
	if err := s.cli.ChangeRoleStatus(ctx, util.MustU32(req.OrgId), util.MustU32(req.RoleId), req.Status); err != nil {
		return nil, errStatus(errs.Code_IAMRole, err)
	}
	return &emptypb.Empty{}, nil
}

// --- internal function ---

func toRoleInfo(role *orm.RoleInfo) *iam_service.RoleInfo {
	ret := &iam_service.RoleInfo{
		RoleId:    strconv.Itoa(int(role.ID)),
		Name:      role.Name,
		Remark:    role.Remark,
		IsAdmin:   role.IsAdmin,
		IsSystem:  role.IsSystem,
		Status:    role.Status,
		CreatedAt: role.CreatedAt,
		Creator:   toIDName(role.Creator),
	}
	for _, perm := range role.Perms {
		ret.Perms = append(ret.Perms, toPerm(perm))
	}
	return ret
}

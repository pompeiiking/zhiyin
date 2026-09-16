package iam

import (
	"context"

	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	iam_service "github.com/UnicomAI/wanwu/api/proto/iam-service"
	"github.com/UnicomAI/wanwu/internal/iam-service/pkg/util"
)

func (s *Service) GetCaptcha(ctx context.Context, req *iam_service.GetCaptchaReq) (*iam_service.GetCaptchaResp, error) {
	code, b64s, err := util.GenerateCaptcha()
	if err != nil {
		return nil, errStatus(errs.Code_IAMCaptcha, toErrStatus("iam_login_captcha", err.Error()))
	}
	if err := s.cli.RefreshCaptcha(ctx, req.Key, code); err != nil {
		return nil, errStatus(errs.Code_IAMCaptcha, err)
	}
	return &iam_service.GetCaptchaResp{
		Key: req.Key,
		B64: b64s,
	}, nil
}

func (s *Service) Login(ctx context.Context, req *iam_service.LoginReq) (*iam_service.LoginResp, error) {
	// captcha
	if err := s.cli.CheckCaptcha(ctx, req.Key, req.Code); err != nil {
		return nil, errStatus(errs.Code_IAMCaptcha, err)
	}
	// login
	user, permission, err := s.cli.Login(ctx, req.UserName, req.Password, req.Language)
	if err != nil {
		return nil, errStatus(errs.Code_IAMLogin, err)
	}
	return &iam_service.LoginResp{
		User:       toUserInfo(user),
		Permission: toPermission(permission),
	}, nil
}

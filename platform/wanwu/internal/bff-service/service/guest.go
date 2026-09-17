package service

import (
	"fmt"
	"strconv"

	iam_service "github.com/UnicomAI/wanwu/api/proto/iam-service"
	"github.com/UnicomAI/wanwu/internal/bff-service/config"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/response"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	mid "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util/mid-wrap"
	jwt_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/jwt-util"
	"github.com/gin-gonic/gin"
)

func GetLanguageSelect() *response.LanguageSelect {
	language := make([]response.Language, len(config.Cfg().I18n.Langs))
	for i, lang := range config.Cfg().I18n.Langs {
		language[i].Code = lang.Code
		language[i].Name = lang.Name
	}
	return &response.LanguageSelect{
		Languages:       language,
		DefaultLanguage: getLanguageByCode(config.Cfg().I18n.DefaultLang),
	}
}

func GetLogoCustomInfo(ctx *gin.Context) (response.LogoCustomInfo, error) {
	ret := response.LogoCustomInfo{
		Version: config.Cfg().CustomInfo.Version,
		Login: response.CustomLogin{
			BackgroundPath:   config.Cfg().CustomInfo.Login.BackgroundPath,
			LoginButtonColor: config.Cfg().CustomInfo.Login.LoginButtonColor,
			WelcomeText:      gin_util.I18nKey(ctx, config.Cfg().CustomInfo.Login.WelcomeText),
		},
		Home: response.CustomHome{
			LogoPath: config.Cfg().CustomInfo.Home.LogoPath,
			Title:    gin_util.I18nKey(ctx, config.Cfg().CustomInfo.Home.Title),
		},
		Tab: response.CustomTab{
			LogoPath: config.Cfg().CustomInfo.Tab.TabLogoPath,
			Title:    gin_util.I18nKey(ctx, config.Cfg().CustomInfo.Tab.TabTitle),
		},
	}
	return ret, nil
}

func GetCaptcha(ctx *gin.Context, key string) (*response.Captcha, error) {
	resp, err := iam.GetCaptcha(ctx.Request.Context(), &iam_service.GetCaptchaReq{
		Key: key,
	})
	if err != nil {
		return nil, err
	}
	return &response.Captcha{
		Key: key,
		B64: resp.B64,
	}, nil
}

func Login(ctx *gin.Context, login *request.Login, language string) (*response.Login, error) {
	password, err := decryptPD(login.Password)
	if err != nil {
		return nil, fmt.Errorf("decrypt password err: %v", err)
	}
	resp, err := iam.Login(ctx.Request.Context(), &iam_service.LoginReq{
		UserName: login.Username,
		Password: password,
		Key:      login.Key,
		Code:     login.Code,
		Language: language,
	})
	if err != nil {
		return nil, err
	}
	// orgs
	orgs, err := iam.GetOrgSelect(ctx.Request.Context(), &iam_service.GetOrgSelectReq{UserId: resp.User.GetUserId()})
	if err != nil {
		return nil, err
	}
	// jwt token
	claims, token, err := jwt_util.GenerateToken(
		resp.User.GetUserId(),
		jwt_util.UserTokenTimeout,
	)
	if err != nil {
		return nil, err
	}
	ctx.Set(config.CLAIMS, &claims)
	// resp
	return &response.Login{
		UID:           resp.User.GetUserId(),
		Username:      resp.User.GetUserName(),
		Nickname:      resp.User.GetNickName(),
		Token:         token,
		ExpiresAt:     claims.StandardClaims.ExpiresAt * 1000, // 超时事件戳毫秒
		ExpireIn:      strconv.FormatInt(jwt_util.UserTokenTimeout, 10),
		Orgs:          toOrgIDNames(ctx, orgs.Selects, resp.User.GetUserId() == config.SystemAdminUserID),
		OrgPermission: toOrgPermission(ctx, resp.Permission),
		Language:      getLanguageByCode(resp.User.Language),
	}, nil
}

// --- internal ---

func getLanguageByCode(languageCode string) response.Language {
	langs := config.Cfg().I18n.Langs
	language := response.Language{Code: languageCode}
	for _, lang := range langs {
		if lang.Code == languageCode {
			language.Name = lang.Name
		}
	}
	return language
}

func toOrgPermission(ctx *gin.Context, orgPerm *iam_service.UserPermission) response.UserOrgPermission {
	return response.UserOrgPermission{
		IsAdmin:     orgPerm.IsAdmin,
		IsSystem:    orgPerm.IsSystem,
		Org:         toOrgIDName(ctx, orgPerm.Org),
		Roles:       toRoleIDNames(ctx, orgPerm.Roles),
		Permissions: toPermissions(orgPerm.IsAdmin, orgPerm.IsSystem, orgPerm.Perms),
	}
}

func toPermissions(isAdmin, isSystem bool, perms []*iam_service.Perm) []response.Permission {
	routes := mid.CollectPerms()
	var ret []response.Permission
	if isAdmin {
		for _, r := range routes {
			if isSystem && r.Tag == "permission.role" {
				continue
			}
			ret = append(ret, response.Permission{
				Perm: r.Tag,
				Name: r.Name,
			})
		}
		return ret
	}
	for _, r := range routes {
		for _, perm := range perms {
			if perm.Perm == r.Tag {
				ret = append(ret, response.Permission{
					Perm: r.Tag,
					Name: r.Name,
				})
				break
			}
		}
	}
	return ret
}

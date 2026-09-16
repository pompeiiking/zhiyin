package service

import (
	perm_service "github.com/UnicomAI/wanwu/api/proto/perm-service"
	"github.com/gin-gonic/gin"
)

func CheckUserEnable(ctx *gin.Context, userID, genTokenAt string) (*perm_service.CheckUserEnableResp, error) {
	return perm.CheckUserEnable(ctx.Request.Context(), &perm_service.CheckUserEnableReq{
		UserId:     userID,
		GenTokenAt: genTokenAt,
	})
}

func CheckUserPerm(ctx *gin.Context, userID, genTokenAt, orgID string, perms []string) (*perm_service.CheckUserPermResp, error) {
	return perm.CheckUserPerm(ctx.Request.Context(), &perm_service.CheckUserPermReq{
		UserId:     userID,
		GenTokenAt: genTokenAt,
		OrgId:      orgID,
		OneOfPerms: perms,
	})
}

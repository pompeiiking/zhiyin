package service

import (
	"bytes"
	"fmt"
	"io"
	"mime/multipart"
	"os"
	"path"
	"path/filepath"
	"strings"
	"sync"

	err_code "github.com/UnicomAI/wanwu/api/proto/err-code"
	iam_service "github.com/UnicomAI/wanwu/api/proto/iam-service"
	"github.com/UnicomAI/wanwu/internal/bff-service/config"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/response"
	grpc_util "github.com/UnicomAI/wanwu/pkg/grpc-util"
	"github.com/UnicomAI/wanwu/pkg/log"
	"github.com/UnicomAI/wanwu/pkg/minio"
	"github.com/UnicomAI/wanwu/pkg/util"
	"github.com/gin-gonic/gin"
)

const docCenterLocalDir = "static/docs"

var (
	avatarCacheMu       sync.Mutex
	avatarCacheLocalDir = "cache"

	mcpAvatarCacheLocalDir = "cache/mcp"
)

func GetUserPermission(ctx *gin.Context, userID, orgID string) (*response.UserPermission, error) {
	resp, err := iam.GetUserPermission(ctx.Request.Context(), &iam_service.GetUserPermissionReq{
		UserId: userID,
		OrgId:  orgID,
	})
	if err != nil {
		return nil, err
	}
	user, err := iam.GetUserInfo(ctx.Request.Context(), &iam_service.GetUserInfoReq{
		UserId: userID,
	})
	if err != nil {
		return nil, err
	}
	return &response.UserPermission{
		OrgPermission: toOrgPermission(ctx, resp),
		Language:      getLanguageByCode(user.Language),
	}, nil
}

func GetOrgSelect(ctx *gin.Context, userID string) (*response.Select, error) {
	resp, err := iam.GetOrgSelect(ctx.Request.Context(), &iam_service.GetOrgSelectReq{UserId: userID})
	if err != nil {
		return nil, err
	}
	return &response.Select{
		Select: toOrgIDNames(ctx, resp.Selects, userID == config.SystemAdminUserID),
	}, nil
}

// UploadAvatar 返回avatar在minio的objectPath
func UploadAvatar(ctx *gin.Context, fileHeader *multipart.FileHeader) (string, error) {
	// 校验文件类型
	ext := strings.ToLower(filepath.Ext(fileHeader.Filename))
	switch ext {
	case ".jpg", ".jpeg", ".png":
	default:
		return "", grpc_util.ErrorStatusWithKey(err_code.Code_BFFInvalidArg, "bff_avatar_type_error")
	}

	// 读取文件内容
	file, err := fileHeader.Open()
	if err != nil {
		return "", grpc_util.ErrorStatusWithKey(err_code.Code_BFFInvalidArg, "bff_avatar_upload_error", err.Error())
	}
	defer file.Close()

	// 读取图片到内存缓冲区
	imgBuf := new(bytes.Buffer)
	if _, err := io.Copy(imgBuf, file); err != nil {
		return "", grpc_util.ErrorStatusWithKey(err_code.Code_BFFInvalidArg, "bff_avatar_upload_error", err.Error())
	}
	fileName := fmt.Sprintf("%s%s", util.GenUUID(), ext)
	// 生成存储路径，avatar/fileName前两位字母/fileName
	objectName := path.Join("avatar", fileName[:2], fileName)
	objectPath := path.Join(minio.BucketCustom, objectName)

	if _, err = minio.Custom().PutObject(ctx.Request.Context(), minio.BucketCustom, objectName, imgBuf.Bytes()); err != nil {
		return "", grpc_util.ErrorStatusWithKey(err_code.Code_BFFInvalidArg, "bff_avatar_upload_error", err.Error())
	}
	return objectPath, nil
}

// CacheAvatar 将avatar在minio的objectPath转为前端可访问的地址，同时在本地缓存avatar
// 例如 custom-upload/avatar/abc/def.png => /v1/static/avatar/abc/def.png
func CacheAvatar(ctx *gin.Context, avatarObjectPath string) request.Avatar {
	avatar := request.Avatar{}
	if avatarObjectPath == "" {
		return avatar
	}
	avatarCacheMu.Lock()
	defer avatarCacheMu.Unlock()

	avatar.Key = avatarObjectPath

	parts := strings.SplitN(avatarObjectPath, "/", 2)
	if len(parts) <= 1 {
		log.Errorf("cache avatar %v err: invalid objectPath")
		return avatar
	}
	bucketName := parts[0]
	objectName := parts[1]
	filePath := filepath.Join(avatarCacheLocalDir, objectName)

	_, err := os.Stat(filePath)
	// 1 文件存在
	if err == nil {
		avatar.Path = filepath.Join("/v1", filePath)
		return avatar
	}
	// 2 系统错误
	if !os.IsNotExist(err) {
		log.Errorf("cache avatar %v check %v exist err: %v", avatarObjectPath, filePath, err)
		return avatar
	}
	// 3 文件不存在
	// 3.1 创建目录
	if err := os.MkdirAll(filepath.Dir(filePath), 0755); err != nil {
		log.Errorf("cache avatar %v mkdir %v err: %v", avatarObjectPath, filepath.Dir(filePath))
		return avatar
	}
	// 3.2 下载文件
	b, err := minio.Custom().GetObject(ctx.Request.Context(), bucketName, objectName)
	if err != nil {
		log.Errorf("cache avatar %v minio download err: %v", avatarObjectPath, err)
		return avatar
	}
	// 3.3 写入文件
	if err := os.WriteFile(filePath, b, 0644); err != nil {
		log.Errorf("cache avatar %v write file %v err: %v", avatarObjectPath, filePath, err)
		return avatar
	}
	avatar.Path = filepath.Join("/v1", filePath)
	return avatar
}

func GetDocCenter() *response.DocCenter {
	return &response.DocCenter{
		DocCenterPath: path.Join("/v1", docCenterLocalDir, path.Base(config.Cfg().DocCenter.DocPath)),
	}
}

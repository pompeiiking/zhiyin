package assistant

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
	"strconv"
	"strings"

	assistant_service "github.com/UnicomAI/wanwu/api/proto/assistant-service"
	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/assistant-service/client/model"
	"github.com/UnicomAI/wanwu/internal/assistant-service/pkg/util"
	"github.com/UnicomAI/wanwu/pkg/log"
	"google.golang.org/protobuf/types/known/emptypb"
)

// AssistantActionCreate 添加api
func (s *Service) AssistantActionCreate(ctx context.Context, req *assistant_service.AssistantActionCreateReq) (*assistant_service.AssistantActionCreateResp, error) {
	//校验参数
	if req.ApiAuth.Type == "none" {
		req.ApiAuth.ApiKey = ""
		req.ApiAuth.AuthType = ""
		req.ApiAuth.CustomHeaderName = ""
	}

	//解析Action
	action, err := parseActionApiInfo(req)
	if err != nil {
		return nil, err
	}
	// 调用client方法创建Action（在事务中创建Action并更新Assistant）
	if status := s.cli.CreateAssistantAction(ctx, action); status != nil {
		return nil, errStatus(errs.Code_AssistantActionErr, status)
	}

	result := &assistant_service.AssistantActionCreateResp{}
	//解析并返回可用api列表
	result.ActionId = strconv.FormatUint(uint64(action.ID), 10)
	paths := strings.Split(action.Path, ",")
	names := strings.Split(action.Name, ",")
	methods := strings.Split(action.Method, ",")

	for i := range paths {
		api := &assistant_service.ActionApi{
			Name:   names[i],
			Path:   paths[i],
			Method: methods[i],
		}
		result.List = append(result.List, api)
	}
	return result, nil
}

func parseActionApiInfo(req *assistant_service.AssistantActionCreateReq) (tab *model.AssistantAction, err error) {
	userId, orgId := req.Identity.UserId, req.Identity.OrgId
	doc, err := util.ValidateOpenAPISchema(req.Schema)
	if err != nil {
		err = fmt.Errorf("%s", "Schema 不合法！")
		log.Errorf(fmt.Sprintf("ParseActionApiInfo 报错(%v) 参数(%v)", err, req))
		return nil, err
	}
	// 遍历所有的路径
	domain, err := parseDomain(doc.Servers[0].URL)
	if err != nil {
		log.Errorf(fmt.Sprintf("ParseActionApiInfo 报错(%v) 参数(%v)", err, req))
		return nil, err
	}
	apiAuthBytes, err := json.Marshal(map[string]string{
		"type":             req.ApiAuth.Type,
		"apiKey":           req.ApiAuth.ApiKey,
		"authType":         req.ApiAuth.AuthType,
		"customHeaderName": req.ApiAuth.CustomHeaderName,
	})
	if err != nil {
		log.Errorf(fmt.Sprintf("ParseActionApiInfo 报错(%v) 参数(%v)", err, req))
		return nil, err
	}
	var paths, names, methods []string
	for path, pathItem := range doc.Paths.Map() {
		paths = append(paths, path)
		for method, operation := range pathItem.Operations() {
			names = append(names, operation.OperationID)
			methods = append(methods, method)
		}
	}
	assistantId, err := strconv.ParseUint(req.AssistantId, 10, 32)
	if err != nil {
		return nil, err
	}
	aa := &model.AssistantAction{
		AssistantId:      uint32(assistantId),
		ActionName:       domain,
		APISchema:        req.Schema,
		APIAuth:          string(apiAuthBytes),
		Type:             req.ApiAuth.Type,
		APIKey:           req.ApiAuth.ApiKey,
		AuthType:         req.ApiAuth.AuthType,
		CustomHeaderName: req.ApiAuth.CustomHeaderName,
		Path:             strings.Join(paths, ","),
		Name:             strings.Join(names, ","),
		Method:           strings.Join(methods, ","),
		Enable:           true,
		UserId:           userId,
		OrgId:            orgId,
	}

	return aa, nil
}
func parseDomain(urlStr string) (string, error) {
	u, err := url.Parse(urlStr)
	if err != nil {
		fmt.Println("Error parsing URL:", err)
		return "", err
	}
	// 提取域名
	domain := u.Hostname()
	return domain, nil
}

// AssistantActionDelete 删除api
func (s *Service) AssistantActionDelete(ctx context.Context, req *assistant_service.AssistantActionDeleteReq) (*emptypb.Empty, error) {
	// 转换ID
	actionID, err := strconv.ParseUint(req.ActionId, 10, 32)
	if err != nil {
		return nil, err
	}

	// 调用client方法删除Action（在事务中删除Action并更新Assistant）
	if status := s.cli.DeleteAssistantAction(ctx, uint32(actionID)); status != nil {
		return nil, errStatus(errs.Code_AssistantActionErr, status)
	}

	return &emptypb.Empty{}, nil
}

// AssistantActionUpdate 编辑api
func (s *Service) AssistantActionUpdate(ctx context.Context, req *assistant_service.AssistantActionUpdateReq) (*emptypb.Empty, error) {
	// 转换ID
	actionID, err := strconv.ParseUint(req.ActionId, 10, 32)
	if err != nil {
		return nil, err
	}

	// 先获取现有Action信息
	existingAction, status := s.cli.GetAssistantAction(ctx, uint32(actionID))
	if status != nil {
		return nil, errStatus(errs.Code_AssistantActionErr, status)
	}

	// 更新字段
	existingAction.APISchema = req.Schema
	if req.ApiAuth != nil {
		existingAction.Type = req.ApiAuth.Type
		existingAction.APIKey = req.ApiAuth.ApiKey
		existingAction.CustomHeaderName = req.ApiAuth.CustomHeaderName
		existingAction.AuthType = req.ApiAuth.AuthType
	}

	// 调用client方法更新Action
	if status := s.cli.UpdateAssistantAction(ctx, existingAction); status != nil {
		return nil, errStatus(errs.Code_AssistantActionErr, status)
	}

	return &emptypb.Empty{}, nil
}

// GetAssistantActionInfo 查看智能体api详情
func (s *Service) GetAssistantActionInfo(ctx context.Context, req *assistant_service.GetAssistantActionInfoReq) (*assistant_service.GetAssistantActionInfoResp, error) {
	// 转换ID
	actionID, err := strconv.ParseUint(req.ActionId, 10, 32)
	if err != nil {
		return nil, err
	}

	// 调用client方法获取Action详情
	action, status := s.cli.GetAssistantAction(ctx, uint32(actionID))
	if status != nil {
		return nil, errStatus(errs.Code_AssistantActionErr, status)
	}

	// 组装API列表
	var actionApis []*assistant_service.ActionApi
	actionApis = append(actionApis, &assistant_service.ActionApi{
		Name:   action.Name,
		Method: action.Method,
		Path:   action.Path,
	})

	return &assistant_service.GetAssistantActionInfoResp{
		ActionId: strconv.FormatUint(uint64(action.ID), 10),
		Schema:   action.APISchema,
		ApiAuth: &assistant_service.ApiAuthWebRequest{
			Type:             action.Type,
			ApiKey:           action.APIKey,
			CustomHeaderName: action.CustomHeaderName,
			AuthType:         action.AuthType,
		},
		List: actionApis,
	}, nil
}

// AssistantActionEnableSwitch Action开关
func (s *Service) AssistantActionEnableSwitch(ctx context.Context, req *assistant_service.AssistantActionEnableSwitchReq) (*emptypb.Empty, error) {
	// 转换ID
	actionID, err := strconv.ParseUint(req.ActionId, 10, 32)
	if err != nil {
		return nil, err
	}

	// 先获取现有Action信息
	existingAction, status := s.cli.GetAssistantAction(ctx, uint32(actionID))
	if status != nil {
		return nil, errStatus(errs.Code_AssistantActionErr, status)
	}

	existingAction.Enable = !existingAction.Enable
	if status := s.cli.UpdateAssistantAction(ctx, existingAction); status != nil {
		return nil, errStatus(errs.Code_AssistantActionErr, status)
	}

	return &emptypb.Empty{}, nil
}

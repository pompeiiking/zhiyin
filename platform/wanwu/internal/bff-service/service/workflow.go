package service

import (
	"encoding/json"
	"errors"
	net_url "net/url"
	"time"

	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/bff-service/config"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/response"
	grpc_util "github.com/UnicomAI/wanwu/pkg/grpc-util"
	http_client "github.com/UnicomAI/wanwu/pkg/http-client"
	"github.com/gin-gonic/gin"
)

func ListWorkFlow(ctx *gin.Context, userId, orgId, name string) (*response.WorkFlowResultResp, error) {
	workflowService := config.Cfg().WorkFlow
	url := workflowService.Endpoint + workflowService.WorkFlowListUri
	result, err := http_client.Workflow().Get(ctx, &http_client.HttpRequestParams{
		Url: url,
		Headers: map[string]string{
			"x-org-id":      orgId,
			"x-user-id":     userId,
			"Authorization": ctx.GetHeader("Authorization"),
		},
		Params: map[string]string{
			"keyword": net_url.QueryEscape(name),
		},
		Timeout:    60 * time.Second,
		MonitorKey: "workflow_list",
		LogLevel:   http_client.LogAll,
	})
	if err != nil {
		return nil, grpc_util.ErrorStatusWithKey(errs.Code_BFFGeneral, "bff_workflow_apps_list", err.Error())
	}
	var resp = &response.WorkFlowListResp{}
	if err = json.Unmarshal(result, resp); err != nil {
		return nil, grpc_util.ErrorStatusWithKey(errs.Code_BFFGeneral, "bff_workflow_apps_list", err.Error())
	}
	if resp.Code != successCode {
		return nil, grpc_util.ErrorStatusWithKey(errs.Code_BFFGeneral, "bff_workflow_apps_list", errors.New(resp.Message).Error())
	}
	return resp.Data, nil
}

func DeleteWorkFlow(ctx *gin.Context, userId, orgId, id string) error {
	workflowService := config.Cfg().WorkFlow
	url := workflowService.Endpoint + workflowService.DeleteWorkFlowUri
	params := &request.DeleteWorkFlowRequest{
		AppId: id,
	}
	body, err := json.Marshal(params)
	if err != nil {
		return err
	}
	result, err := http_client.Workflow().Delete(ctx, &http_client.HttpRequestParams{
		Url: url,
		Headers: map[string]string{
			"x-org-id":      orgId,
			"x-user-id":     userId,
			"Authorization": ctx.GetHeader("Authorization"),
			"Content-Type":  "application/json",
		},
		Body:       body,
		Timeout:    60 * time.Second,
		MonitorKey: "workflow_delete",
		LogLevel:   http_client.LogAll,
	})
	if err != nil {
		return grpc_util.ErrorStatusWithKey(errs.Code_BFFGeneral, "bff_workflow_app_delete", err.Error())
	}
	var resp = &response.DeleteWorkFlowResp{}
	if err = json.Unmarshal(result, resp); err != nil {
		return grpc_util.ErrorStatusWithKey(errs.Code_BFFGeneral, "bff_workflow_app_delete", err.Error())
	}
	if resp.Code != successCode {
		return grpc_util.ErrorStatusWithKey(errs.Code_BFFGeneral, "bff_workflow_app_delete", errors.New(resp.Message).Error())
	}
	return nil
}

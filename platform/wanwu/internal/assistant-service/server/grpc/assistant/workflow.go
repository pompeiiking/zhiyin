package assistant

import (
	"context"
	"fmt"
	"strconv"
	"strings"

	assistant_service "github.com/UnicomAI/wanwu/api/proto/assistant-service"
	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/assistant-service/client/model"
	"github.com/UnicomAI/wanwu/internal/assistant-service/pkg/util"
	"github.com/UnicomAI/wanwu/pkg/log"
	"google.golang.org/protobuf/types/known/emptypb"
)

// AssistantWorkFlowCreate 添加workFlow
func (s *Service) AssistantWorkFlowCreate(ctx context.Context, req *assistant_service.AssistantWorkFlowCreateReq) (*emptypb.Empty, error) {
	workflow, err := parseWorkFlowApiInfo(req)
	if err != nil {
		return nil, err
	}

	// 调用client方法创建WorkFlow（在事务中创建WorkFlow并更新Assistant）
	if status := s.cli.CreateAssistantWorkflow(ctx, workflow); status != nil {
		return nil, errStatus(errs.Code_AssistantWorkflowErr, status)
	}

	return &emptypb.Empty{}, nil
}

func parseWorkFlowApiInfo(req *assistant_service.AssistantWorkFlowCreateReq) (*model.AssistantWorkflow, error) {
	userId, orgId := req.Identity.UserId, req.Identity.OrgId
	assistantID, err := strconv.ParseUint(req.AssistantId, 10, 32)
	if err != nil {
		return nil, err
	}
	doc, err := util.ValidateOpenAPISchema(req.Schema)
	if err != nil {
		log.Errorf(fmt.Sprintf("ParseWorkFlowApiInfo 报错：Schema 不合法！(%v) 参数(%v)", err, req))
		return nil, err
	}
	var paths, names, methods []string
	workFlowId := req.WorkFlowId
	for path, pathItem := range doc.Paths.Map() {
		paths = append(paths, path)
		for method, operation := range pathItem.Operations() {
			names = append(names, operation.OperationID)
			methods = append(methods, method)
		}
	}
	workFlow := &model.AssistantWorkflow{
		WorkflowId:  workFlowId,
		AssistantId: uint32(assistantID),
		APISchema:   req.Schema,
		Path:        strings.Join(paths, ","),
		Name:        strings.Join(names, ","),
		Method:      strings.Join(methods, ","),
		Enable:      true,
		UserId:      userId,
		OrgId:       orgId,
	}

	return workFlow, nil
}

// AssistantWorkFlowDelete 删除workFlow
func (s *Service) AssistantWorkFlowDelete(ctx context.Context, req *assistant_service.AssistantWorkFlowDeleteReq) (*emptypb.Empty, error) {
	// 转换ID
	workflowID, err := strconv.ParseUint(req.WorkFlowId, 10, 32)
	if err != nil {
		return nil, err
	}

	// 调用client方法删除WorkFlow（在事务中删除WorkFlow并更新Assistant）
	if status := s.cli.DeleteAssistantWorkflow(ctx, uint32(workflowID)); status != nil {
		return nil, errStatus(errs.Code_AssistantWorkflowErr, status)
	}

	return &emptypb.Empty{}, nil
}

// AssistantWorkFlowEnableSwitch WorkFlow开关
func (s *Service) AssistantWorkFlowEnableSwitch(ctx context.Context, req *assistant_service.AssistantWorkFlowEnableSwitchReq) (*emptypb.Empty, error) {
	// 转换ID
	workflowID, err := strconv.ParseUint(req.WorkFlowId, 10, 32)
	if err != nil {
		return nil, err
	}

	// 先获取现有WorkFlow信息
	existingWorkflow, status := s.cli.GetAssistantWorkflow(ctx, uint32(workflowID))
	if status != nil {
		return nil, errStatus(errs.Code_AssistantWorkflowErr, status)
	}

	existingWorkflow.Enable = !existingWorkflow.Enable
	if status := s.cli.UpdateAssistantWorkflow(ctx, existingWorkflow); status != nil {
		return nil, errStatus(errs.Code_AssistantWorkflowErr, status)
	}

	return &emptypb.Empty{}, nil
}

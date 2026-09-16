package assistant

import (
	assistant_service "github.com/UnicomAI/wanwu/api/proto/assistant-service"
	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/assistant-service/client"
	grpc_util "github.com/UnicomAI/wanwu/pkg/grpc-util"
)

type Service struct {
	assistant_service.UnimplementedAssistantServiceServer
	cli client.IClient
}

func NewService(cli client.IClient) *Service {
	return &Service{
		cli: cli,
	}
}

func errStatus(code errs.Code, status *errs.Status) error {
	return grpc_util.ErrorStatusWithKey(code, status.TextKey, status.Args...)
}

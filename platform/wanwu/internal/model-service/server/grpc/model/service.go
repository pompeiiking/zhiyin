package model

import (
	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	model_service "github.com/UnicomAI/wanwu/api/proto/model-service"
	"github.com/UnicomAI/wanwu/internal/model-service/client"
	grpc_util "github.com/UnicomAI/wanwu/pkg/grpc-util"
)

type Service struct {
	cli client.IClient
	model_service.UnimplementedModelServiceServer
}

func NewService(cli client.IClient) *Service {
	return &Service{
		cli: cli,
	}
}

func errStatus(code errs.Code, status *errs.Status) error {
	return grpc_util.ErrorStatusWithKey(code, status.TextKey, status.Args...)
}

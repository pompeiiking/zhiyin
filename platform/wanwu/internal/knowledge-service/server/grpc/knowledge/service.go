package knowledge

import (
	knowledgebase_service "github.com/UnicomAI/wanwu/api/proto/knowledgebase-service"
	grpc_provider "github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/grpc-provider"
	"google.golang.org/grpc"
)

type Service struct {
	knowledgebase_service.UnimplementedKnowledgeBaseServiceServer
}

var service = Service{}

func init() {
	grpc_provider.AddGrpcContainer(&service)
}

func (s *Service) GrpcType() string {
	return "grpc_knowledge_service"
}

func (s *Service) Register(serv *grpc.Server) error {
	knowledgebase_service.RegisterKnowledgeBaseServiceServer(serv, s)
	return nil
}

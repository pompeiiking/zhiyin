package knowledge_doc

import (
	knowledgebase_doc_service "github.com/UnicomAI/wanwu/api/proto/knowledgebase-doc-service"
	grpc_provider "github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/grpc-provider"
	"google.golang.org/grpc"
)

type Service struct {
	knowledgebase_doc_service.UnimplementedKnowledgeBaseDocServiceServer
}

var docService = Service{}

func init() {
	grpc_provider.AddGrpcContainer(&docService)
}

func (s *Service) GrpcType() string {
	return "grpc_knowledge_doc_service"
}

func (s *Service) Register(serv *grpc.Server) error {
	knowledgebase_doc_service.RegisterKnowledgeBaseDocServiceServer(serv, s)
	return nil
}

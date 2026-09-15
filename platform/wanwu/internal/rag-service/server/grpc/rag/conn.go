package rag

import (
	"fmt"

	knowledgeBase_service "github.com/UnicomAI/wanwu/api/proto/knowledgebase-service"
	"github.com/UnicomAI/wanwu/internal/rag-service/config"
	"github.com/UnicomAI/wanwu/pkg/log"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

const (
	maxMsgSize            = 1024 * 1024 * 4 // 4M
	headlessServiceSchema = "dns:///"
)

var (
	Knowledge knowledgeBase_service.KnowledgeBaseServiceClient
)

func StartService() error {
	// grpc connections
	knowledgeConn, err := newConn(config.Cfg().Knowledge.Host)
	if err != nil {
		return fmt.Errorf("init knowledgebase-service connection err: %v", err)
	}

	Knowledge = knowledgeBase_service.NewKnowledgeBaseServiceClient(knowledgeConn)
	log.Infof("Knowledge init success")
	log.Infof("Knowledge: %s", config.Cfg().Knowledge.Host)
	return nil
}

func newConn(host string) (*grpc.ClientConn, error) {
	conn, err := grpc.NewClient(headlessServiceSchema+host,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithDefaultServiceConfig(`{"loadBalancingPolicy":"round_robin"}`),
		grpc.WithDefaultCallOptions(
			grpc.MaxCallRecvMsgSize(maxMsgSize),
			grpc.MaxCallSendMsgSize(maxMsgSize)),
	)
	if err != nil {
		return nil, err
	}
	return conn, err
}

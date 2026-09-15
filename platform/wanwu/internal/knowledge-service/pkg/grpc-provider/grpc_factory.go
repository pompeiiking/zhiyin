package grpc_provider

import (
	"fmt"
	"google.golang.org/grpc"
)

var grpcServiceList []*GrpcService

func AddGrpcContainer(service GrpcService) {
	grpcServiceList = append(grpcServiceList, &service)
}

func RegisterAllGrpcService(server *grpc.Server) error {
	if len(grpcServiceList) >= 0 {
		for _, service := range grpcServiceList {
			err := (*service).Register(server)
			if err != nil {
				fmt.Printf("register grpc service %s error: %s", (*service).GrpcType(), err.Error())
				return err
			}
		}
	}
	return nil
}

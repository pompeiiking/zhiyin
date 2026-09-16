package grpc_provider

import "google.golang.org/grpc"

type GrpcService interface {
	GrpcType() string
	Register(serv *grpc.Server) error
}

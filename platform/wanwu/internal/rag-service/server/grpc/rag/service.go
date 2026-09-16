package rag

import (
	"context"

	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	knowledgebase_service "github.com/UnicomAI/wanwu/api/proto/knowledgebase-service"
	rag_service "github.com/UnicomAI/wanwu/api/proto/rag-service"
	"github.com/UnicomAI/wanwu/internal/rag-service/client"
	"github.com/UnicomAI/wanwu/internal/rag-service/client/model"
	"github.com/UnicomAI/wanwu/internal/rag-service/pkg/generator"
	"github.com/UnicomAI/wanwu/internal/rag-service/service"
	grpc_util "github.com/UnicomAI/wanwu/pkg/grpc-util"
	"github.com/UnicomAI/wanwu/pkg/log"
	"google.golang.org/grpc"
	"google.golang.org/protobuf/types/known/emptypb"
)

type Service struct {
	cli client.IClient
	rag_service.UnimplementedRagServiceServer
}

func NewService(cli client.IClient) *Service {
	return &Service{
		cli: cli,
	}
}

func errStatus(code errs.Code, status *errs.Status) error {
	return grpc_util.ErrorStatusWithKey(code, status.TextKey, status.Args...)
}

func (s *Service) ChatRag(req *rag_service.ChatRagReq, stream grpc.ServerStreamingServer[rag_service.ChatRagResp]) error {
	ctx := stream.Context()
	// 获取rag详情
	rag, err := s.cli.FetchRagFirst(ctx, req.RagId)
	if err != nil {
		return errStatus(errs.Code_RagChatErr, err)
	}
	log.Infof("get rag: %v", rag)
	// 校验知识库是否存在
	log.Infof("check know: userid = %s, orgId = %s, knowid = %s", rag.UserID, rag.UserID, rag.KnowledgeBaseConfig.KnowId)
	knowledge, errk := Knowledge.SelectKnowledgeDetailById(ctx, &knowledgebase_service.KnowledgeDetailSelectReq{
		UserId:      rag.UserID,
		OrgId:       rag.OrgID,
		KnowledgeId: rag.KnowledgeBaseConfig.KnowId,
	})
	if errk != nil {
		log.Errorf("errk = %s", errk.Error())
		return grpc_util.ErrorStatusWithKey(errs.Code_RagChatErr, "rag_chat_err", "check knowledge err:", errk.Error())
	}
	if knowledge == nil {
		log.Errorf("knowledge = nil")
		return grpc_util.ErrorStatusWithKey(errs.Code_RagChatErr, "rag_chat_err", "check knowledge err: knowledge is nil")
	}

	//  请求rag
	buildParams := service.BuildChatConsultParams(req, rag, knowledge)
	chatChan, errg := service.RagStreamChat(ctx, rag.UserID, buildParams)
	if errg != nil {
		return grpc_util.ErrorStatusWithKey(errs.Code_RagChatErr, "rag_chat_err", errg.Error())
	}
	for text := range chatChan {
		resp := &rag_service.ChatRagResp{
			Content: text,
		}
		if err := stream.Send(resp); err != nil {
			return grpc_util.ErrorStatusWithKey(errs.Code_RagChatErr, "rag_chat_err", err.Error())
		}
	}
	return nil
}

func (s *Service) CreateRag(ctx context.Context, in *rag_service.CreateRagReq) (*rag_service.CreateRagResp, error) {
	ragId := generator.GetGenerator().NewID()
	err := s.cli.CreateRag(ctx, &model.RagInfo{
		RagID: ragId,
		BriefConfig: model.AppBriefConfig{
			Name:       in.AppBrief.Name,
			Desc:       in.AppBrief.Desc,
			AvatarPath: in.AppBrief.AvatarPath,
		},
		PublicModel: model.PublicModel{
			OrgID:  in.Identity.OrgId,
			UserID: in.Identity.UserId,
		},
	})
	if err != nil {
		return nil, errStatus(errs.Code_RagCreateErr, err) // todo
	}
	return &rag_service.CreateRagResp{RagId: ragId}, nil
}

func (s *Service) UpdateRag(ctx context.Context, in *rag_service.UpdateRagReq) (*emptypb.Empty, error) {
	if err := s.cli.UpdateRag(ctx, &model.RagInfo{
		RagID: in.RagId,
		BriefConfig: model.AppBriefConfig{
			Name:       in.AppBrief.Name,
			Desc:       in.AppBrief.Desc,
			AvatarPath: in.AppBrief.AvatarPath,
		},
	}); err != nil {
		return nil, errStatus(errs.Code_RagUpdateErr, err)
	}
	return &emptypb.Empty{}, nil
}

func (s *Service) UpdateRagConfig(ctx context.Context, in *rag_service.UpdateRagConfigReq) (*emptypb.Empty, error) {
	if err := s.cli.UpdateRagConfig(ctx, &model.RagInfo{
		RagID: in.RagId,
		ModelConfig: model.AppModelConfig{
			Provider:  in.ModelConfig.Provider,
			Model:     in.ModelConfig.Model,
			ModelId:   in.ModelConfig.ModelId,
			ModelType: in.ModelConfig.ModelType,
			Config:    in.ModelConfig.Config,
		},
		RerankConfig: model.AppModelConfig{
			Provider:  in.RerankConfig.Provider,
			Model:     in.RerankConfig.Model,
			ModelId:   in.RerankConfig.ModelId,
			ModelType: in.RerankConfig.ModelType,
			Config:    in.RerankConfig.Config,
		},
		KnowledgeBaseConfig: model.KnowledgeBaseConfig{
			KnowId:           in.KnowledgeBaseConfig.KnowledgeBaseId,
			MaxHistory:       int64(in.KnowledgeBaseConfig.MaxHistory),
			MaxHistoryEnable: in.KnowledgeBaseConfig.MaxHistoryEnable,
			Threshold:        float64(in.KnowledgeBaseConfig.Threshold),
			ThresholdEnable:  in.KnowledgeBaseConfig.ThresholdEnable,
			TopK:             int64(in.KnowledgeBaseConfig.TopK),
			TopKEnable:       in.KnowledgeBaseConfig.TopKEnable,
		},
	}); err != nil {
		return nil, errStatus(errs.Code_RagUpdateErr, err)
	}
	return &emptypb.Empty{}, nil
}

func (s *Service) DeleteRag(ctx context.Context, in *rag_service.RagDeleteReq) (*emptypb.Empty, error) {
	errDelete := s.cli.DeleteRag(ctx, in)
	if errDelete != nil {
		return nil, errStatus(errs.Code_RagDeleteErr, errDelete)
	}
	return nil, nil
}

func (s *Service) GetRagDetail(ctx context.Context, in *rag_service.RagDetailReq) (*rag_service.RagInfo, error) {
	info, err := s.cli.GetRag(ctx, in)
	if err != nil {
		return nil, errStatus(errs.Code_RagGetErr, err)
	}
	return info, nil
}

func (s *Service) ListRag(ctx context.Context, in *rag_service.RagListReq) (*rag_service.RagListResp, error) {
	ragList, err := s.cli.GetRagList(ctx, in)
	if err != nil {
		return nil, errStatus(errs.Code_RagListErr, err)
	}
	return ragList, nil
}

func (s *Service) GetRagByIds(ctx context.Context, in *rag_service.GetRagByIdsReq) (*rag_service.AppBriefList, error) {
	ragList, err := s.cli.GetRagByIds(ctx, &rag_service.GetRagByIdsReq{
		RagIdList: in.RagIdList,
	})
	if err != nil {
		return nil, errStatus(errs.Code_RagListErr, err)
	}
	return ragList, nil
}

package knowledge

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/UnicomAI/wanwu/internal/knowledge-service/client/model"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/client/orm"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/generator"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/util"
	"github.com/UnicomAI/wanwu/pkg/log"

	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	knowledgebase_service "github.com/UnicomAI/wanwu/api/proto/knowledgebase-service"
	"google.golang.org/protobuf/types/known/emptypb"
)

func (s *Service) SelectKnowledgeList(ctx context.Context, req *knowledgebase_service.KnowledgeSelectReq) (*knowledgebase_service.KnowledgeSelectListResp, error) {
	list, err := orm.SelectKnowledgeList(ctx, req.UserId, req.OrgId, req.Name)
	if err != nil {
		log.Errorf(fmt.Sprintf("获取知识库列表失败(%v)  参数(%v)", err, req))
		return nil, util.ErrCode(errs.Code_KnowledgeBaseSelectFailed)
	}
	return buildKnowledgeListResp(list), nil
}

func (s *Service) SelectKnowledgeDetailById(ctx context.Context, req *knowledgebase_service.KnowledgeDetailSelectReq) (*knowledgebase_service.KnowledgeInfo, error) {
	knowledgeInfo, err := orm.SelectKnowledgeById(ctx, req.KnowledgeId, req.UserId, req.OrgId)
	if err != nil {
		log.Errorf(fmt.Sprintf("获取知识库详情(%v)  参数(%v)", err, req))
		return nil, err
	}
	return buildKnowledgeInfo(knowledgeInfo), nil
}

func (s *Service) SelectKnowledgeDetailByName(ctx context.Context, req *knowledgebase_service.KnowledgeDetailSelectReq) (*knowledgebase_service.KnowledgeInfo, error) {
	knowledgeInfo, err := orm.SelectKnowledgeByName(ctx, req.KnowledgeName, req.UserId, req.OrgId)
	if err != nil {
		log.Errorf(fmt.Sprintf("根据名称获取知识库详情失败(%v)  参数(%v)", err, req))
		return nil, err
	}
	return buildKnowledgeInfo(knowledgeInfo), nil
}

func (s *Service) CreateKnowledge(ctx context.Context, req *knowledgebase_service.CreateKnowledgeReq) (*knowledgebase_service.CreateKnowledgeResp, error) {
	//1.重名校验
	err := orm.CheckSameKnowledgeName(ctx, req.UserId, req.OrgId, req.Name)
	if err != nil {
		return nil, err
	}
	//2.创建创建知识库
	knowledgeModel, err := buildKnowledgeBaseModel(req)
	if err != nil {
		log.Errorf("buildKnowledgeBaseModel error %s", err)
		return nil, util.ErrCode(errs.Code_KnowledgeBaseCreateFailed)
	}
	err = orm.CreateKnowledge(ctx, knowledgeModel, req.EmbeddingModelInfo.ModelId)
	if err != nil {
		log.Errorf("CreateKnowledge error %v params %v", err, req)
		return nil, util.ErrCode(errs.Code_KnowledgeBaseCreateFailed)
	}
	//3.返回结果
	return &knowledgebase_service.CreateKnowledgeResp{
		KnowledgeId: knowledgeModel.KnowledgeId,
	}, nil
}

func (s *Service) UpdateKnowledge(ctx context.Context, req *knowledgebase_service.UpdateKnowledgeReq) (*emptypb.Empty, error) {
	//1.查询知识库详情
	knowledge, err := orm.SelectKnowledgeById(ctx, req.KnowledgeId, req.UserId, req.OrgId)
	if err != nil {
		log.Errorf(fmt.Sprintf("没有操作该知识库的权限 参数(%v)", req))
		return nil, err
	}
	//2.重名校验
	err = orm.CheckSameKnowledgeName(ctx, req.UserId, req.OrgId, req.Name)
	if err != nil {
		return nil, err
	}
	//3.更新知识库
	err = orm.UpdateKnowledge(ctx, req.Name, req.Description, knowledge)
	if err != nil {
		log.Errorf("知识库更新失败(%v)  参数(%v)", err, req)
		return nil, util.ErrCode(errs.Code_KnowledgeBaseUpdateFailed)
	}
	return &emptypb.Empty{}, nil
}

// DeleteKnowledge 删除知识库
func (s *Service) DeleteKnowledge(ctx context.Context, req *knowledgebase_service.DeleteKnowledgeReq) (*emptypb.Empty, error) {
	//1.查询知识库详情
	knowledge, err := orm.SelectKnowledgeById(ctx, req.KnowledgeId, req.UserId, req.OrgId)
	if err != nil {
		log.Errorf(fmt.Sprintf("没有操作该知识库的权限 参数(%v)", req))
		return nil, err
	}
	//2.校验导入状态
	err = orm.SelectKnowledgeRunningImportTask(ctx, knowledge.KnowledgeId)
	if err != nil {
		return nil, err
	}
	//3.先删除知识库，异步删除资源数据
	err = orm.DeleteKnowledge(ctx, knowledge)
	if err != nil {
		log.Errorf("删除知识库失败 error %v params %v", err, req)
		return nil, util.ErrCode(errs.Code_KnowledgeBaseDeleteFailed)
	}
	return &emptypb.Empty{}, nil
}

// buildKnowledgeListResp 构造知识库列表返回结果
func buildKnowledgeListResp(knowledgeList []*model.KnowledgeBase) *knowledgebase_service.KnowledgeSelectListResp {
	if len(knowledgeList) == 0 {
		return &knowledgebase_service.KnowledgeSelectListResp{}
	}
	var retList []*knowledgebase_service.KnowledgeInfo
	for _, knowledge := range knowledgeList {
		retList = append(retList, buildKnowledgeInfo(knowledge))
	}
	return &knowledgebase_service.KnowledgeSelectListResp{
		KnowledgeList: retList,
	}
}

// buildKnowledgeInfo 构造知识库信息
func buildKnowledgeInfo(knowledge *model.KnowledgeBase) *knowledgebase_service.KnowledgeInfo {
	embeddingModelInfo := &knowledgebase_service.EmbeddingModelInfo{}
	_ = json.Unmarshal([]byte(knowledge.EmbeddingModel), embeddingModelInfo)
	return &knowledgebase_service.KnowledgeInfo{
		KnowledgeId:        knowledge.KnowledgeId,
		Name:               knowledge.Name,
		Description:        knowledge.Description,
		DocCount:           int32(knowledge.DocCount),
		EmbeddingModelInfo: embeddingModelInfo,
	}
}

// buildKnowledgeBaseModel 构造知识库模型
func buildKnowledgeBaseModel(req *knowledgebase_service.CreateKnowledgeReq) (*model.KnowledgeBase, error) {
	embeddingModelInfo, err := json.Marshal(req.EmbeddingModelInfo)
	if err != nil {
		return nil, err
	}
	return &model.KnowledgeBase{
		KnowledgeId:    generator.GetGenerator().NewID(),
		Name:           req.Name,
		Description:    req.Description,
		OrgId:          req.OrgId,
		UserId:         req.UserId,
		EmbeddingModel: string(embeddingModelInfo),
		CreatedAt:      time.Now().UnixMilli(),
		UpdatedAt:      time.Now().UnixMilli(),
	}, nil
}

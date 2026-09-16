package knowledge_doc

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	knowledgebase_doc_service "github.com/UnicomAI/wanwu/api/proto/knowledgebase-doc-service"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/client/model"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/client/orm"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/generator"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/util"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/service"
	"github.com/UnicomAI/wanwu/pkg/log"
	util2 "github.com/UnicomAI/wanwu/pkg/util"
	"google.golang.org/protobuf/types/known/emptypb"
)

const (
	noSplitter      = "未设置"
	DocImportIng    = 1
	DocImportFinish = 2
	DocImportError  = 3
)

func (s *Service) GetDocList(ctx context.Context, req *knowledgebase_doc_service.GetDocListReq) (*knowledgebase_doc_service.GetDocListResp, error) {
	list, total, err := orm.GetDocList(ctx, req.UserId, req.OrgId,
		req.KnowledgeId, req.DocName, util.BuildDocReqStatusList(int(req.Status)), req.PageSize, req.PageNum)
	if err != nil {
		log.Errorf(fmt.Sprintf("获取知识库列表失败(%v)  参数(%v)", err, req))
		return nil, util.ErrCode(errs.Code_KnowledgeBaseSelectFailed)
	}
	return buildDocListResp(list, total, req.PageSize, req.PageNum), nil
}

func (s *Service) ImportDoc(ctx context.Context, req *knowledgebase_doc_service.ImportDocReq) (*emptypb.Empty, error) {
	task, err := buildImportTask(req)
	if err != nil {
		return nil, err
	}
	//创建导入任务
	err = orm.CreateKnowledgeImportTask(ctx, task)
	if err != nil {
		log.Errorf("import doc fail %v", err)
		return nil, util.ErrCode(errs.Code_KnowledgeDocImportFail)
	}
	return &emptypb.Empty{}, nil
}

func (s *Service) UpdateDocStatus(ctx context.Context, req *knowledgebase_doc_service.UpdateDocStatusReq) (*emptypb.Empty, error) {
	err := orm.UpdateDocStatusDocId(ctx, req.DocId, int(req.Status))
	if err != nil {
		log.Errorf(fmt.Sprintf("update doc fail %v", err), req.DocId)
		return nil, util.ErrCode(errs.Code_KnowledgeDocUpdateStatusFailed)
	}
	return &emptypb.Empty{}, nil
}

func (s *Service) InitDocStatus(ctx context.Context, req *knowledgebase_doc_service.InitDocStatusReq) (*emptypb.Empty, error) {
	err := orm.InitDocStatus(ctx, req.UserId, req.OrgId)
	if err != nil {
		log.Errorf(fmt.Sprintf("init doc fail %v", err), req)
		return nil, util.ErrCode(errs.Code_KnowledgeGeneral)
	}
	return &emptypb.Empty{}, nil
}

func (s *Service) DeleteDoc(ctx context.Context, req *knowledgebase_doc_service.DeleteDocReq) (*emptypb.Empty, error) {
	//1.查询文档详情
	docList, err := orm.SelectDocByDocIdList(ctx, req.Ids, req.UserId, req.OrgId)
	if err != nil {
		log.Errorf(fmt.Sprintf("没有操作该知识库的权限 参数(%v)", req))
		return nil, err
	}
	//2.校验导入状态
	docIdList, resultDocList, err := checkDocStatus(docList)
	if err != nil {
		log.Errorf("删除知识库文件失败 error %v params %v", err, req)
		return nil, util.ErrCode(errs.Code_KnowledgeDocDeleteDuringParse)
	}
	if len(docIdList) == 0 {
		return &emptypb.Empty{}, nil
	}
	//3.删除文档
	err = orm.DeleteDocByIdList(ctx, docIdList, resultDocList)
	if err != nil {
		log.Errorf("删除知识库文件失败 error %v params %v", err, req)
		return nil, util.ErrCode(errs.Code_KnowledgeDocDeleteFailed)
	}
	return &emptypb.Empty{}, nil
}

func (s *Service) GetDocCategoryUploadTip(ctx context.Context, req *knowledgebase_doc_service.DocImportTipReq) (*knowledgebase_doc_service.DocImportTipResp, error) {
	//1.查询知识库详情
	knowledge, err := orm.SelectKnowledgeById(ctx, req.KnowledgeId, req.UserId, req.OrgId)
	if err != nil {
		return nil, err
	}
	//2.查询第一个异步任务信息
	taskList, err := orm.SelectKnowledgeLatestImportTask(ctx, req.KnowledgeId)
	if err != nil {
		return nil, err
	}
	if len(taskList) == 0 {
		return &knowledgebase_doc_service.DocImportTipResp{
			KnowledgeId:   req.KnowledgeId,
			KnowledgeName: knowledge.Name,
			UploadStatus:  DocImportFinish,
		}, nil
	}
	if len(taskList) > 0 {
		task := taskList[0]
		if task.Status == model.KnowledgeImportError {
			return &knowledgebase_doc_service.DocImportTipResp{
				KnowledgeId:   req.KnowledgeId,
				KnowledgeName: knowledge.Name,
				Message:       "\n" + task.ErrorMsg,
				UploadStatus:  DocImportError,
			}, nil
		} else if task.Status == model.KnowledgeImportFinish {
			return &knowledgebase_doc_service.DocImportTipResp{
				KnowledgeId:   req.KnowledgeId,
				KnowledgeName: knowledge.Name,
				UploadStatus:  DocImportFinish,
			}, nil
		}
	}
	return &knowledgebase_doc_service.DocImportTipResp{
		KnowledgeId:   req.KnowledgeId,
		KnowledgeName: knowledge.Name,
		Message:       "",
		UploadStatus:  DocImportIng,
	}, nil
}

func (s *Service) GetDocSegmentList(ctx context.Context, req *knowledgebase_doc_service.DocSegmentListReq) (*knowledgebase_doc_service.DocSegmentListResp, error) {
	//1.查询文档详情
	docList, err := orm.SelectDocByDocIdList(ctx, []string{req.DocId}, req.UserId, req.OrgId)
	if err != nil {
		log.Errorf(fmt.Sprintf("没有操作该知识库的权限 参数(%v)", req))
		return nil, err
	}
	docInfo := docList[0]
	//2.查询知识库详情
	knowledge, err := orm.SelectKnowledgeById(ctx, docInfo.KnowledgeId, req.UserId, req.OrgId)
	if err != nil {
		log.Errorf(fmt.Sprintf("查询知识库详情失败 参数(%v)", req))
		return nil, err
	}
	//3.查询知识库导入详情
	importTask, err := orm.SelectKnowledgeImportTaskById(ctx, docInfo.ImportTaskId)
	if err != nil {
		log.Errorf(fmt.Sprintf("查询知识库导入详情失败 参数(%v)", req))
		return nil, err
	}
	//3.查询分片信息
	segmentListResp, err := service.RagGetDocSegmentList(ctx, &service.RagGetDocSegmentParams{
		UserId:            req.UserId,
		KnowledgeBaseName: knowledge.Name,
		FileName:          service.RebuildFileName(docInfo.DocId, docInfo.FileType, docInfo.Name),
		PageSize:          req.PageSize,
		SearchAfter:       req.PageSize * (req.PageNo - 1),
	})
	if err != nil {
		return nil, util.ErrCode(errs.Code_KnowledgeDocSplitFailed)
	}
	return buildSegmentListResp(importTask, docInfo, segmentListResp, req.PageNo, req.PageSize)
}

func (s *Service) UpdateDocSegmentStatus(ctx context.Context, req *knowledgebase_doc_service.UpdateDocSegmentReq) (*emptypb.Empty, error) {
	//1.查询文档详情
	docList, err := orm.SelectDocByDocIdList(ctx, []string{req.DocId}, req.UserId, req.OrgId)
	if err != nil {
		log.Errorf(fmt.Sprintf("没有操作该知识库的权限 参数(%v)", req))
		return nil, err
	}
	docInfo := docList[0]
	//2.查询知识库详情
	knowledge, err := orm.SelectKnowledgeById(ctx, docInfo.KnowledgeId, req.UserId, req.OrgId)
	if err != nil {
		log.Errorf(fmt.Sprintf("查询知识库详情失败 参数(%v)", req))
		return nil, err
	}
	//3.更新文档状态
	var params = buildDocUpdateSegmentStatusParams(req, knowledge, docInfo)
	err = service.RagDocUpdateDocSegmentStatus(ctx, params)
	if err != nil {
		log.Errorf(fmt.Sprintf("UpdateFileStatus 更新知识库文档切片启用状态 失败(%v)  参数(%v)", err, req))
		return nil, util.ErrCode(errs.Code_KnowledgeDocSegmentStatusUpdateFail)
	}
	return &emptypb.Empty{}, nil
}

func (s *Service) AnalysisDocUrl(ctx context.Context, req *knowledgebase_doc_service.AnalysisUrlDocReq) (*knowledgebase_doc_service.AnalysisUrlDocResp, error) {
	analysisResult, err := service.BatchRagDocUrlAnalysis(ctx, req.UrlList)
	if err != nil {
		return nil, err
	}
	var retUrlList []*knowledgebase_doc_service.UrlInfo
	for _, result := range analysisResult {
		retUrlList = append(retUrlList, &knowledgebase_doc_service.UrlInfo{
			Url:      result.Url,
			FileName: util.UrlNameFilter(result.FileName),
			FileSize: result.FileSize,
		})
	}
	return &knowledgebase_doc_service.AnalysisUrlDocResp{UrlList: retUrlList}, nil
}

func checkDocStatus(docList []*model.KnowledgeDoc) ([]uint32, []*model.KnowledgeDoc, error) {
	var docIdList []uint32
	var docResultList []*model.KnowledgeDoc
	for _, doc := range docList {
		if doc.Status == model.DocProcessing {
			return nil, nil, errors.New("解析中的文档无法删除")
		}
		docIdList = append(docIdList, doc.Id)
		docResultList = append(docResultList, doc)
	}
	return docIdList, docResultList, nil
}

// buildDocListResp 构造知识库文档列表
func buildDocListResp(list []*model.KnowledgeDoc, total int64, pageSize int32, pageNum int32) *knowledgebase_doc_service.GetDocListResp {
	var retList = make([]*knowledgebase_doc_service.DocInfo, 0)
	if len(list) > 0 {
		for _, item := range list {
			retList = append(retList, &knowledgebase_doc_service.DocInfo{
				DocId:       item.DocId,
				DocName:     item.Name,
				DocSize:     item.FileSize,
				DocType:     item.FileType,
				KnowledgeId: item.KnowledgeId,
				UploadTime:  util2.Time2Str(item.CreatedAt),
				Status:      int32(util.BuildDocRespStatus(item.Status)),
				ErrorMsg:    item.ErrorMsg,
			})
		}
	}
	return &knowledgebase_doc_service.GetDocListResp{
		Total:    total,
		Docs:     retList,
		PageSize: pageSize,
		PageNum:  pageNum,
	}
}

// buildImportTask 构造导入任务
func buildImportTask(req *knowledgebase_doc_service.ImportDocReq) (*model.KnowledgeImportTask, error) {
	if req.DocSegment.SegmentType == "0" {
		req.DocSegment.Overlap = 0.2
		req.DocSegment.MaxSplitter = 500
	}
	segmentConfig, err := json.Marshal(req.DocSegment)
	if err != nil {
		return nil, err
	}
	analyzer, err := json.Marshal(&model.DocAnalyzer{
		AnalyzerList: req.DocAnalyzer,
	})
	if err != nil {
		return nil, err
	}
	docList := make([]*model.DocInfo, 0)
	for _, docInfo := range req.DocInfoList {
		docList = append(docList, &model.DocInfo{
			DocId:   docInfo.DocId,
			DocName: docInfo.DocName,
			DocUrl:  docInfo.DocUrl,
			DocType: docInfo.DocType,
			DocSize: docInfo.DocSize,
		})
	}
	docImportInfo, err := json.Marshal(&model.DocImportInfo{
		DocInfoList: docList,
	})
	if err != nil {
		return nil, err
	}
	return &model.KnowledgeImportTask{
		ImportId:      generator.GetGenerator().NewID(),
		KnowledgeId:   req.KnowledgeId,
		ImportType:    int(req.DocImportType),
		SegmentConfig: string(segmentConfig),
		DocAnalyzer:   string(analyzer),
		CreatedAt:     time.Now().UnixMilli(),
		UpdatedAt:     time.Now().UnixMilli(),
		DocInfo:       string(docImportInfo),
		UserId:        req.UserId,
		OrgId:         req.OrgId,
	}, nil
}

// buildSegmentListResp 构造文档分段列表
func buildSegmentListResp(importTask *model.KnowledgeImportTask, doc *model.KnowledgeDoc, segmentListResp *service.ContentListResp, pageNo, pageSize int32) (*knowledgebase_doc_service.DocSegmentListResp, error) {
	var config = &model.SegmentConfig{}
	err := json.Unmarshal([]byte(importTask.SegmentConfig), config)
	if err != nil {
		log.Errorf("SegmentConfig process error %s", err.Error())
		return nil, err
	}

	content := segmentListResp.List[0]
	var resp = &knowledgebase_doc_service.DocSegmentListResp{
		FileName:        doc.Name,
		MaxSegmentSize:  int32(config.MaxSplitter),
		SegType:         config.SegmentType,
		CreatedAt:       util2.Time2Str(doc.CreatedAt),
		Splitter:        buildSplitter(config.Splitter),
		PageTotal:       buildPageTotal(int32(content.MetaData.ChunkTotalNum), pageSize),
		SegmentTotalNum: int32(content.MetaData.ChunkTotalNum),
		ContentList:     buildContentList(segmentListResp.List, pageNo, pageSize),
	}
	return resp, nil
}

func buildSplitter(splitterList []string) string {
	if len(splitterList) == 0 {
		return noSplitter
	}
	return strings.Join(splitterList, " 、 ")
}

func buildPageTotal(totalNum int32, pageSize int32) int32 {
	leftPageSize := totalNum % pageSize
	var leftPage int32 = 0
	if leftPageSize > 0 {
		leftPage = 1
	}
	return totalNum/pageSize + leftPage
}

func buildContentList(contentList []service.FileSplitContent, pageNo int32, pageSize int32) []*knowledgebase_doc_service.SegmentContent {
	var retList = make([]*knowledgebase_doc_service.SegmentContent, 0)
	for i := 0; i < len(contentList); i++ {
		content := contentList[i]
		retList = append(retList, &knowledgebase_doc_service.SegmentContent{
			Content:    content.Content,
			Len:        int32(content.MetaData.ChunkLen),
			Available:  content.Status,
			ContentId:  content.ContentId,
			ContentNum: (pageNo-1)*pageSize + int32(i+1),
		})
	}
	return retList
}

func buildDocUpdateSegmentStatusParams(req *knowledgebase_doc_service.UpdateDocSegmentReq, knowledge *model.KnowledgeBase, docInfo *model.KnowledgeDoc) interface{} {
	//前端逻辑，all + status 组合控制一键开启和一键关停，比如：all：true，status：false 则标识一键关停
	//但是底层 只要all false 就是一键关停
	var status = req.ContentStatus == "true"
	if req.All {
		return &service.DocSegmentStatusUpdateAllParams{
			DocSegmentStatusUpdateParams: service.DocSegmentStatusUpdateParams{
				UserId:        req.UserId,
				KnowledgeName: knowledge.Name,
				FileName:      service.RebuildFileName(docInfo.DocId, docInfo.FileType, docInfo.Name),
				ContentId:     req.ContentId,
			},
			All: status,
		}
	} else {
		return &service.DocSegmentStatusUpdateParams{
			UserId:        req.UserId,
			KnowledgeName: knowledge.Name,
			FileName:      service.RebuildFileName(docInfo.DocId, docInfo.FileType, docInfo.Name),
			ContentId:     req.ContentId,
			Status:        status,
		}
	}
}

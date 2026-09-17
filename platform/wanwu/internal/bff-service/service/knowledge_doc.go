package service

import (
	"strings"

	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	knowledgebase_doc_service "github.com/UnicomAI/wanwu/api/proto/knowledgebase-doc-service"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/response"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	grpc_util "github.com/UnicomAI/wanwu/pkg/grpc-util"
	"github.com/UnicomAI/wanwu/pkg/log"
	"github.com/UnicomAI/wanwu/pkg/minio"
	"github.com/UnicomAI/wanwu/pkg/util"
	"github.com/gin-gonic/gin"
)

// GetDocList 查询知识库所属文档列表
func GetDocList(ctx *gin.Context, userId, orgId string, r *request.DocListReq) (*response.PageResult, error) {
	resp, err := knowledgeBaseDoc.GetDocList(ctx.Request.Context(), &knowledgebase_doc_service.GetDocListReq{
		KnowledgeId: r.KnowledgeId,
		DocName:     r.DocName,
		Status:      int32(r.Status),
		PageSize:    int32(r.PageSize),
		PageNum:     int32(r.PageNo),
		UserId:      userId,
		OrgId:       orgId,
	})
	if err != nil {
		return nil, err
	}
	return &response.PageResult{
		List:     buildDocRespList(ctx, resp.Docs),
		Total:    resp.Total,
		PageNo:   int(resp.PageNum),
		PageSize: int(resp.PageSize),
	}, nil
}

// ImportDoc 导入文档
func ImportDoc(ctx *gin.Context, userId, orgId string, req *request.DocImportReq) error {
	segment := req.DocSegment
	var docInfoList []*knowledgebase_doc_service.DocFileInfo
	for _, info := range req.DocInfo {
		var docUrl = info.DocUrl
		var docType = info.DocType
		if len(docUrl) == 0 {
			var err error
			docUrl, err = minio.GetUploadFileWithExpire(ctx, info.DocId)
			if err != nil {
				log.Errorf("GetUploadFileWithNotExpire error %v", err)
				return grpc_util.ErrorStatus(errs.Code_KnowledgeDocImportUrlFailed)
			}
			//特殊处理类型
			if strings.HasSuffix(docUrl, ".tar.gz") {
				docType = ".tar.gz"
			}
		}
		docInfoList = append(docInfoList, &knowledgebase_doc_service.DocFileInfo{
			DocName: info.DocName,
			DocId:   info.DocId,
			DocUrl:  docUrl,
			DocType: docType,
			DocSize: info.DocSize,
		})
	}
	_, err := knowledgeBaseDoc.ImportDoc(ctx.Request.Context(), &knowledgebase_doc_service.ImportDocReq{
		UserId:        userId,
		OrgId:         orgId,
		KnowledgeId:   req.KnowledgeId,
		DocImportType: int32(req.DocImportType),
		DocSegment: &knowledgebase_doc_service.DocSegment{
			SegmentType: segment.SegmentType,
			Splitter:    segment.Splitter,
			MaxSplitter: int32(segment.MaxSplitter),
			Overlap:     segment.Overlap,
		},
		DocAnalyzer: req.DocAnalyzer,
		DocInfoList: docInfoList,
	})
	if err != nil {
		log.Errorf("上传失败(保存上传任务 失败(%v) ", err)
		return err
	}
	return nil
}

func UpdateDocStatus(ctx *gin.Context, r *request.CallbackUpdateDocStatusReq) error {
	_, err := knowledgeBaseDoc.UpdateDocStatus(ctx.Request.Context(), &knowledgebase_doc_service.UpdateDocStatusReq{
		DocId:  r.DocId,
		Status: r.Status,
	})
	return err
}

func DocStatusInit(ctx *gin.Context, userId, orgId string) (interface{}, error) {
	_, err := knowledgeBaseDoc.InitDocStatus(ctx, &knowledgebase_doc_service.InitDocStatusReq{
		UserId: userId,
		OrgId:  orgId,
	})
	return nil, err
}

func GetDocImportTip(ctx *gin.Context, userId, orgId string, r *request.QueryKnowledgeReq) (*response.DocImportTipResp, error) {
	resp, err := knowledgeBaseDoc.GetDocCategoryUploadTip(ctx.Request.Context(), &knowledgebase_doc_service.DocImportTipReq{
		UserId:      userId,
		OrgId:       orgId,
		KnowledgeId: r.KnowledgeId,
	})
	if err != nil {
		return nil, err
	}
	var message = ""
	if len(resp.Message) > 0 {
		message = gin_util.I18nKey(ctx, "know_doc_last_failure_info", resp.Message)
	}
	return &response.DocImportTipResp{
		Message:       message,
		UploadStatus:  resp.UploadStatus,
		KnowledgeId:   resp.KnowledgeId,
		KnowledgeName: resp.KnowledgeName,
	}, nil
}

func DeleteDoc(ctx *gin.Context, userId, orgId string, r *request.DeleteDocReq) error {
	_, err := knowledgeBaseDoc.DeleteDoc(ctx.Request.Context(), &knowledgebase_doc_service.DeleteDocReq{
		Ids:    r.DocIdList,
		UserId: userId,
		OrgId:  orgId,
	})
	return err
}

func GetDocSegmentList(ctx *gin.Context, userId, orgId string, req *request.DocSegmentListReq) (*response.DocSegmentResp, error) {
	resp, err := knowledgeBaseDoc.GetDocSegmentList(ctx.Request.Context(), &knowledgebase_doc_service.DocSegmentListReq{
		UserId:   userId,
		OrgId:    orgId,
		DocId:    req.DocId,
		PageSize: int32(req.PageSize),
		PageNo:   int32(req.PageNo),
	})
	if err != nil {
		return nil, err
	}
	return buildDocSegmentResp(resp), nil
}

func UpdateDocSegmentStatus(ctx *gin.Context, userId, orgId string, r *request.UpdateDocSegmentStatusReq) error {
	_, err := knowledgeBaseDoc.UpdateDocSegmentStatus(ctx.Request.Context(), &knowledgebase_doc_service.UpdateDocSegmentReq{
		UserId:        userId,
		OrgId:         orgId,
		DocId:         r.DocId,
		ContentId:     r.ContentId,
		ContentStatus: r.ContentStatus,
		All:           r.ALL,
	})
	return err
}

func AnalysisDocUrl(ctx *gin.Context, userId, orgId string, r *request.AnalysisUrlDocReq) (*response.AnalysisDocUrlResp, error) {
	resp, err := knowledgeBaseDoc.AnalysisDocUrl(ctx.Request.Context(), &knowledgebase_doc_service.AnalysisUrlDocReq{
		UserId:      userId,
		OrgId:       orgId,
		KnowledgeId: r.KnowledgeId,
		UrlList:     r.UrlList,
	})
	if err != nil {
		return nil, err
	}
	var urlList []*response.Url
	if len(resp.UrlList) > 0 {
		for _, url := range resp.UrlList {
			urlList = append(urlList, &response.Url{
				Url:      url.Url,
				FileName: url.FileName,
				FileSize: int(url.FileSize),
			})
		}
	}
	return &response.AnalysisDocUrlResp{UrlList: urlList}, nil
}

// buildDocRespList 构造文档返回列表
func buildDocRespList(ctx *gin.Context, dataList []*knowledgebase_doc_service.DocInfo) []*response.ListDocResp {
	var retList []*response.ListDocResp
	for _, data := range dataList {
		retList = append(retList, &response.ListDocResp{
			DocId:      data.DocId,
			DocName:    data.DocName,
			DocType:    data.DocType,
			UploadTime: data.UploadTime,
			Status:     int(data.Status),
			ErrorMsg:   gin_util.I18nKey(ctx, data.ErrorMsg),
			FileSize:   util.ToFileSizeStr(data.DocSize),
		})
	}
	return retList
}

// buildDocSegmentResp 构造doc分片返回信息
func buildDocSegmentResp(docSegmentListResp *knowledgebase_doc_service.DocSegmentListResp) *response.DocSegmentResp {
	var segmentContentList = make([]*response.SegmentContent, 0)
	if len(docSegmentListResp.ContentList) > 0 {
		for _, contentInfo := range docSegmentListResp.ContentList {
			segmentContentList = append(segmentContentList, &response.SegmentContent{
				ContentId:  contentInfo.ContentId,
				Content:    contentInfo.Content,
				Len:        int(contentInfo.Len),
				Available:  contentInfo.Available,
				ContentNum: int(contentInfo.ContentNum),
			})
		}
	}
	return &response.DocSegmentResp{
		FileName:           docSegmentListResp.FileName,
		PageTotal:          int(docSegmentListResp.PageTotal),
		SegmentTotalNum:    int(docSegmentListResp.SegmentTotalNum),
		MaxSegmentSize:     int(docSegmentListResp.MaxSegmentSize),
		SegmentType:        docSegmentListResp.SegType,
		UploadTime:         docSegmentListResp.CreatedAt,
		Splitter:           docSegmentListResp.Splitter,
		SegmentContentList: segmentContentList,
	}
}

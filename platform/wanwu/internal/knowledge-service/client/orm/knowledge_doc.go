package orm

import (
	"context"
	"encoding/json"
	"errors"
	"net/url"

	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/client/model"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/client/orm/sqlopt"
	async_task "github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/async-task"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/db"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/util"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/service"
	"github.com/UnicomAI/wanwu/pkg/log"
	"gorm.io/gorm"
)

// GetDocList 查询知识库文件列表
func GetDocList(ctx context.Context, userId, orgId, knowledgeId, name string, statusList []int, pageSize int32, pageNum int32) ([]*model.KnowledgeDoc, int64, error) {
	tx := sqlopt.SQLOptions(sqlopt.WithPermit(orgId, userId),
		sqlopt.WithKnowledgeID(knowledgeId),
		sqlopt.LikeName(name),
		sqlopt.WithStatusList(statusList),
		sqlopt.WithDelete(0)).
		Apply(db.GetHandle(ctx), &model.KnowledgeDoc{})
	var total int64
	err := tx.Count(&total).Error
	if err != nil {
		return nil, 0, err
	}
	limit := pageSize
	offset := pageSize * (pageNum - 1)
	var docList []*model.KnowledgeDoc
	err = tx.Order("create_at desc").Limit(int(limit)).Offset(int(offset)).Find(&docList).Error
	if err != nil {
		return nil, 0, err
	}
	return docList, total, nil
}

// GetDocListByKnowledgeIdNoDeleteCheck 根据知识库id查询知识库文件列表
func GetDocListByKnowledgeIdNoDeleteCheck(ctx context.Context, userId, orgId string, knowledgeId string) ([]*model.KnowledgeDoc, error) {
	var docList []*model.KnowledgeDoc
	err := sqlopt.SQLOptions(sqlopt.WithPermit(orgId, userId), sqlopt.WithKnowledgeID(knowledgeId)).
		Apply(db.GetHandle(ctx), &model.KnowledgeDoc{}).Find(&docList).Error
	if err != nil {
		return nil, err
	}
	return docList, nil
}

// GetDocListByIdListNoDeleteCheck 查询知识库文件列表
func GetDocListByIdListNoDeleteCheck(ctx context.Context, userId, orgId string, idList []uint32) ([]*model.KnowledgeDoc, error) {
	var docList []*model.KnowledgeDoc
	err := sqlopt.SQLOptions(sqlopt.WithPermit("", userId), sqlopt.WithIDs(idList)).
		Apply(db.GetHandle(ctx), &model.KnowledgeDoc{}).Find(&docList).Error
	if err != nil {
		return nil, err
	}
	return docList, nil
}

// CheckKnowledgeDocSameName 知识库文档同名校验
func CheckKnowledgeDocSameName(ctx context.Context, userId string, knowledgeId string, docName string, docUrl string) error {
	var count int64
	var docUrlMd5 = ""
	if len(docUrl) > 0 {
		docUrlMd5 = util.MD5(docUrl)
	}
	err := sqlopt.SQLOptions(sqlopt.WithPermit("", userId),
		sqlopt.WithKnowledgeID(knowledgeId),
		sqlopt.WithName(docName),
		sqlopt.WithFilePathMd5(docUrlMd5),
		sqlopt.WithoutStatus(model.DocFail)).
		Apply(db.GetHandle(ctx), &model.KnowledgeDoc{}).
		Count(&count).Error
	if err != nil {
		log.Errorf("CheckKnowledgeDocSameName knowledgeId %s err: %v", knowledgeId, err)
		return errors.New("CheckKnowledgeDocSameName error")
	}
	if count > 0 {
		return errors.New("CheckKnowledgeDocSameName exist error")
	}
	return nil
}

// SelectDocByDocIdList 查询知识库文档信息
func SelectDocByDocIdList(ctx context.Context, docIdList []string, userId, orgId string) ([]*model.KnowledgeDoc, error) {
	var docList []*model.KnowledgeDoc
	err := sqlopt.SQLOptions(sqlopt.WithPermit(orgId, userId), sqlopt.WithDocIDs(docIdList)).
		Apply(db.GetHandle(ctx), &model.KnowledgeDoc{}).
		Find(&docList).Error
	if err != nil {
		log.Errorf("SelectDocByDocId userId %s err: %v", userId, err)
		return nil, util.ErrCode(errs.Code_KnowledgeBaseAccessDenied)
	}
	if len(docList) == 0 {
		log.Errorf("SelectDocByDocId userId %s doc list empty", userId)
		return nil, util.ErrCode(errs.Code_KnowledgeBaseAccessDenied)
	}
	return docList, nil
}

// CreateKnowledgeDoc 创建知识库文件
func CreateKnowledgeDoc(ctx context.Context, doc *model.KnowledgeDoc, importTask *model.KnowledgeImportTask) error {
	knowledge, err := SelectKnowledgeById(ctx, doc.KnowledgeId, doc.UserId, doc.OrgId)
	if err != nil {
		return err
	}
	var config = &model.SegmentConfig{}
	err = json.Unmarshal([]byte(importTask.SegmentConfig), config)
	if err != nil {
		log.Errorf("SegmentConfig process error %s", err.Error())
		return err
	}
	var analyzer = &model.DocAnalyzer{}
	err = json.Unmarshal([]byte(importTask.DocAnalyzer), analyzer)
	if err != nil {
		log.Errorf("DocAnalyzer process error %s", err.Error())

		return err
	}
	_, objectName, _ := service.SplitFilePath(doc.FilePath)
	return db.GetHandle(ctx).Transaction(func(tx *gorm.DB) error {
		//1.逻辑删除数据
		err := createKnowledgeDoc(tx, doc)
		if err != nil {
			return err
		}
		//非初始话状态的不需要rag 导入，因为有可能直接失败了
		if doc.Status != model.DocInit {
			return nil
		}
		//2.rag文档导入
		return service.RagImportDoc(ctx, &service.RagImportDocParams{
			DocId:         doc.DocId,
			KnowledgeName: knowledge.Name,
			CategoryId:    knowledge.KnowledgeId,
			UserId:        doc.UserId,
			Overlap:       config.Overlap,
			SegmentSize:   config.MaxSplitter,
			SegmentType:   service.RebuildSegmentType(config.SegmentType),
			Separators:    config.Splitter,
			ParserChoices: analyzer.AnalyzerList,
			ObjectName:    objectName,
			OriginalName:  doc.Name,
			IsEnhanced:    "false",
		})
	})
}

// CreateKnowledgeUrlDoc 创建知识库url文件
func CreateKnowledgeUrlDoc(ctx context.Context, doc *model.KnowledgeDoc, importTask *model.KnowledgeImportTask) error {
	knowledge, err := SelectKnowledgeById(ctx, doc.KnowledgeId, doc.UserId, doc.OrgId)
	if err != nil {
		return err
	}
	var config = &model.SegmentConfig{}
	err = json.Unmarshal([]byte(importTask.SegmentConfig), config)
	if err != nil {
		log.Errorf("SegmentConfig process error %s", err.Error())
		return err
	}
	var analyzer = &model.DocAnalyzer{}
	err = json.Unmarshal([]byte(importTask.DocAnalyzer), analyzer)
	if err != nil {
		log.Errorf("DocAnalyzer process error %s", err.Error())

		return err
	}
	return db.GetHandle(ctx).Transaction(func(tx *gorm.DB) error {
		//1.逻辑删除数据
		err := createKnowledgeDoc(tx, doc)
		if err != nil {
			return err
		}
		//非初始话状态的不需要rag 导入，因为有可能直接失败了
		if doc.Status != model.DocInit {
			return nil
		}
		//2.rag url文档导入
		err = service.RagImportUrlDoc(ctx, &service.RagImportUrlDocParams{
			TaskId:            doc.DocId,
			FileName:          doc.Name,
			Url:               url.QueryEscape(doc.FilePath),
			UserId:            doc.UserId,
			Overlap:           config.Overlap,
			SegmentSize:       config.MaxSplitter,
			SegmentType:       service.RebuildSegmentType(config.SegmentType),
			Separators:        config.Splitter,
			KnowledgeBaseName: knowledge.Name,
		})
		if err != nil {
			return err
		}
		//3.rag 文档开始导入操作
		var fileName = service.RebuildFileName(doc.DocId, doc.FileType, doc.Name)
		return service.RagImportDoc(ctx, &service.RagImportDocParams{
			DocId:         doc.DocId,
			KnowledgeName: knowledge.Name,
			CategoryId:    knowledge.KnowledgeId,
			UserId:        doc.UserId,
			Overlap:       config.Overlap,
			SegmentSize:   config.MaxSplitter,
			SegmentType:   service.RebuildSegmentType(config.SegmentType),
			Separators:    config.Splitter,
			ParserChoices: analyzer.AnalyzerList,
			ObjectName:    fileName,
			OriginalName:  fileName,
			IsEnhanced:    "false",
		})
	})
}

// UpdateDocStatusDocId 更新文档状态
func UpdateDocStatusDocId(ctx context.Context, docId string, status int) error {
	var updateParams = map[string]interface{}{
		"status":    status,
		"error_msg": util.BuildDocErrMessage(status),
	}
	return db.GetHandle(ctx).Model(&model.KnowledgeDoc{}).Where("doc_id = ?", docId).Updates(updateParams).Error
}

// InitDocStatus 初始化文档状态
func InitDocStatus(ctx context.Context, userId, orgId string) error {
	// 获取所有分析中状态的文档并更新状态
	updateDoc := map[string]interface{}{
		"status":    5,
		"error_msg": "know_doc_parsing_interrupted",
	}
	//会锁表风险极高
	tx := sqlopt.SQLOptions(sqlopt.WithPermit(orgId, userId), sqlopt.WithStatusList(util.BuildAnalyzingStatus())).
		Apply(db.GetHandle(ctx), &model.KnowledgeDoc{})
	if err := tx.Updates(updateDoc).Error; err != nil {
		return err
	}
	return nil
}

// DeleteDocByIdList 删除文档
func DeleteDocByIdList(ctx context.Context, idList []uint32, resultDocList []*model.KnowledgeDoc) error {
	return db.GetHandle(ctx).Transaction(func(tx *gorm.DB) error {
		//1.逻辑删除数据
		err := logicDeleteDocByIdList(tx, idList)
		if err != nil {
			return err
		}
		err = DeleteKnowledgeFileInfo(tx, resultDocList[0].KnowledgeId, buildDocInfoList(resultDocList))
		//2.更新知识库条数
		if err != nil {
			return err
		}
		//3.异步执行删除数据
		return async_task.SubmitTask(ctx, async_task.DocDeleteTaskType, &async_task.DocDeleteParams{
			DocIdList: idList,
		})
	})
}

func buildDocInfoList(docList []*model.KnowledgeDoc) []*model.DocInfo {
	var retList []*model.DocInfo
	for _, doc := range docList {
		retList = append(retList, &model.DocInfo{
			DocSize: doc.FileSize,
		})
	}
	return retList
}

// ExecuteDeleteDocByIdList 执行删除
func ExecuteDeleteDocByIdList(tx *gorm.DB, idList []uint32) error {
	return tx.Unscoped().Where("id IN ?", idList).Delete(&model.KnowledgeDoc{}).Error
}

// logicDeleteDocByIdList 逻辑删除
func logicDeleteDocByIdList(tx *gorm.DB, idList []uint32) error {
	var updateParams = map[string]interface{}{
		"deleted": 1,
	}
	return tx.Model(&model.KnowledgeDoc{}).Where("id IN ?", idList).Updates(updateParams).Error
}

// createKnowledgeDoc 插入数据
func createKnowledgeDoc(tx *gorm.DB, knowledgeDoc *model.KnowledgeDoc) error {
	return tx.Model(&model.KnowledgeDoc{}).Create(knowledgeDoc).Error
}

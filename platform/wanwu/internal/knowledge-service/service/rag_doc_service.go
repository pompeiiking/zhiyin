package service

import (
	"context"
	"encoding/json"
	"errors"
	"strings"
	"sync"
	"time"

	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/config"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/http"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/mq"
	http_client "github.com/UnicomAI/wanwu/pkg/http-client"
	"github.com/UnicomAI/wanwu/pkg/log"
)

const (
	SplitByDesign  string = "split_by_design"
	SplitByDefault string = "split_by_default"
)

type RagOperationParams struct {
	Operation string              `json:"operation"`
	Type      string              `json:"type"`
	Doc       *RagImportDocParams `json:"doc"`
}

type RagGetDocSegmentParams struct {
	UserId            string `json:"userId"`
	KnowledgeBaseName string `json:"knowledgeBase"`
	FileName          string `json:"fileName"`
	PageSize          int32  `json:"page_size"`
	SearchAfter       int32  `json:"search_after"`
}

type RagImportDocParams struct {
	DocId         string   `json:"id"`         //文档id
	KnowledgeName string   `json:"categoryId"` //知识库名称
	CategoryId    string   `json:"kb_id"`      //知识库id
	IsEnhanced    string   `json:"is_enhanced"`
	UserId        string   `json:"userId"`
	Overlap       float32  `json:"overlap" `
	ObjectName    string   `json:"objectName"`
	SegmentSize   int      `json:"chunk_size"`
	OriginalName  string   `json:"originalName"`
	SegmentType   string   `json:"chunk_type"`
	Separators    []string `json:"separators"`
	ParserChoices []string `json:"parser_choices"`
}

type RagImportUrlDocParams struct {
	Url               string   `json:"url"`
	FileName          string   `json:"file_name"`
	Overlap           float32  `json:"overlap_size" `
	SegmentSize       int      `json:"sentence_size"`
	SegmentType       string   `json:"chunk_type"`
	UserId            string   `json:"userId"`
	KnowledgeBaseName string   `json:"knowledgeBase"`
	IsEnhanced        bool     `json:"is_enhanced"`
	Separators        []string `json:"separators"`
	TaskId            string   `json:"task_id"`
}

type RagDeleteDocParams struct {
	UserId        string `json:"userId"`
	KnowledgeBase string `json:"knowledgeBase"`
	FileName      string `json:"fileName"`
}

type RagGetDocSegmentResp struct {
	RagCommonResp
	Data *ContentListResp `json:"data"`
}

type ContentListResp struct {
	List []FileSplitContent `json:"content_list"`
}

type FileSplitContent struct {
	Content   string          `json:"content"`
	Order     int             `json:"order"`
	Status    bool            `json:"status"`
	MetaData  ContentMetaData `json:"meta_data"`
	ContentId string          `json:"content_id"`
	UserId    string          `json:"userId"`
	KbName    string          `json:"kb_name"`
	FileName  string          `json:"file_name"`
}

type ContentMetaData struct {
	FileName        string `json:"file_name"`
	ChunkLen        int    `json:"chunk_len"`
	ChunkCurrentNum int    `json:"chunk_current_num"`
	ChunkTotalNum   int    `json:"chunk_total_num"`
}

type DocSegmentStatusUpdateParams struct {
	UserId        string `json:"userId"`
	KnowledgeName string `json:"knowledgeBase"`
	FileName      string `json:"fileName"`
	ContentId     string `json:"content_id"`
	Status        bool   `json:"status"`
}

type DocSegmentStatusUpdateAllParams struct {
	DocSegmentStatusUpdateParams
	All bool `json:"on_off_switch"`
}

type DocUrlParams struct {
	Url string `json:"url"`
}

type DocUrlResp struct {
	Url          string        `json:"url"`
	OldName      string        `json:"old_name"`
	FileName     string        `json:"file_name"`
	FileSize     float64       `json:"file_size"`
	ResponseInfo RagCommonResp `json:"response_info"`
}

type DocUrlRespSafeArray struct {
	data []*DocUrlResp
	mu   sync.Mutex
}

func (sa *DocUrlRespSafeArray) Append(value *DocUrlResp) {
	sa.mu.Lock()
	defer sa.mu.Unlock()
	sa.data = append(sa.data, value)
}

func (sa *DocUrlRespSafeArray) Get(index int) interface{} {
	sa.mu.Lock()
	defer sa.mu.Unlock()
	if index < 0 || index >= len(sa.data) {
		return nil
	}
	return sa.data[index]
}

func (sa *DocUrlRespSafeArray) Len() int {
	sa.mu.Lock()
	defer sa.mu.Unlock()
	return len(sa.data)
}

// RagImportDoc 导入具体文档
func RagImportDoc(ctx context.Context, ragImportDocParams *RagImportDocParams) error {
	return mq.SendMessage(&RagOperationParams{
		Operation: "add",
		Type:      "doc",
		Doc:       ragImportDocParams,
	}, config.GetConfig().Kafka.Topic)
}

// RagImportUrlDoc 导入url文档
func RagImportUrlDoc(ctx context.Context, ragImportDocParams *RagImportUrlDocParams) error {
	ragServer := config.GetConfig().RagServer
	url := ragServer.UrlImportEndpoint + ragServer.DocUrlImportUri
	paramsByte, err := json.Marshal(ragImportDocParams)
	if err != nil {
		return err
	}
	result, err := http.GetClient().PostJson(ctx, &http_client.HttpRequestParams{
		Url:        url,
		Body:       paramsByte,
		Timeout:    time.Duration(ragServer.Timeout) * time.Second,
		MonitorKey: "rag_doc_url_import",
		LogLevel:   http_client.LogAll,
	})
	if err != nil {
		return err
	}
	var resp RagCommonResp
	if err = json.Unmarshal(result, &resp); err != nil {
		log.Errorf(err.Error())
		return err
	}
	if resp.Code != successCode {
		if strings.Contains(resp.Message, "文档不存在") {
			return nil
		}
		return errors.New(resp.Message)
	}
	return nil
}

// RagDeleteDoc 删除具体文档
func RagDeleteDoc(ctx context.Context, ragDeleteDocParams *RagDeleteDocParams) error {
	ragServer := config.GetConfig().RagServer
	url := ragServer.Endpoint + ragServer.DocDeleteUri
	paramsByte, err := json.Marshal(ragDeleteDocParams)
	if err != nil {
		return err
	}
	result, err := http.GetClient().PostJson(ctx, &http_client.HttpRequestParams{
		Url:        url,
		Body:       paramsByte,
		Timeout:    time.Duration(ragServer.Timeout) * time.Second,
		MonitorKey: "rag_doc_delete",
		LogLevel:   http_client.LogAll,
	})
	if err != nil {
		return err
	}
	var resp RagCommonResp
	if err := json.Unmarshal(result, &resp); err != nil {
		log.Errorf(err.Error())
		return err
	}
	if resp.Code != successCode {
		if strings.Contains(resp.Message, "文档不存在") {
			return nil
		}
		return errors.New(resp.Message)
	}
	return nil
}

// RagGetDocSegmentList rag获取知识库文档分片
func RagGetDocSegmentList(ctx context.Context, ragGetDocSegmentParams *RagGetDocSegmentParams) (*ContentListResp, error) {
	ragServer := config.GetConfig().RagServer
	url := ragServer.Endpoint + ragServer.GetDocSegmentUri
	paramsByte, err := json.Marshal(ragGetDocSegmentParams)
	if err != nil {
		return nil, err
	}
	result, err := http.GetClient().PostJson(ctx, &http_client.HttpRequestParams{
		Url:        url,
		Body:       paramsByte,
		Timeout:    time.Duration(ragServer.Timeout) * time.Second,
		MonitorKey: "rag_get_doc_segment",
		LogLevel:   http_client.LogAll,
	})
	if err != nil {
		return nil, err
	}
	var resp RagGetDocSegmentResp
	if err := json.Unmarshal(result, &resp); err != nil {
		log.Errorf(err.Error())
		return nil, err
	}
	if resp.Code != successCode {
		return nil, errors.New(resp.Message)
	}
	if resp.Data == nil || len(resp.Data.List) == 0 {
		return nil, errors.New("doc segment response is empty")
	}
	return resp.Data, nil
}

// RagDocUpdateDocSegmentStatus 更新文档切片状态
func RagDocUpdateDocSegmentStatus(ctx context.Context, docSegmentStatusUpdateParams interface{}) error {
	ragServer := config.GetConfig().RagServer
	url := ragServer.Endpoint + ragServer.DocSegmentUpdateStatusUri
	paramsByte, err := json.Marshal(docSegmentStatusUpdateParams)
	if err != nil {
		return err
	}
	result, err := http.GetClient().PostJson(ctx, &http_client.HttpRequestParams{
		Url:        url,
		Body:       paramsByte,
		Timeout:    time.Duration(ragServer.Timeout) * time.Second,
		MonitorKey: "rag_doc_segment_update_status",
		LogLevel:   http_client.LogAll,
	})
	if err != nil {
		return err
	}
	var resp RagCommonResp
	if err := json.Unmarshal(result, &resp); err != nil {
		log.Errorf(err.Error())
		return err
	}
	if resp.Code != successCode {
		return errors.New(resp.Message)
	}
	return nil
}

func BatchRagDocUrlAnalysis(ctx context.Context, urlList []string) ([]*DocUrlResp, error) {
	var wg = &sync.WaitGroup{}
	var resultArray = DocUrlRespSafeArray{}
	for _, url := range urlList {
		wg.Add(1)
		go func() {
			defer wg.Done()
			analysis, err := RagDocUrlAnalysis(ctx, &DocUrlParams{
				Url: url,
			})
			if err != nil {
				log.Errorf(err.Error())
				return
			}
			resultArray.Append(analysis)
		}()
	}
	wg.Wait()
	if resultArray.Len() == 0 {
		return nil, errors.New("解析url失败")
	}
	return resultArray.data, nil
}

// RagDocUrlAnalysis 文档url解析
func RagDocUrlAnalysis(ctx context.Context, docUrlParams *DocUrlParams) (*DocUrlResp, error) {
	ragServer := config.GetConfig().RagServer
	url := ragServer.UrlAnalysisEndpoint + ragServer.DocUrlAnalysisUri
	paramsByte, err := json.Marshal(docUrlParams)
	if err != nil {
		return nil, err
	}
	result, err := http.GetClient().PostJson(ctx, &http_client.HttpRequestParams{
		Url:        url,
		Body:       paramsByte,
		Timeout:    time.Duration(ragServer.Timeout) * time.Second,
		MonitorKey: "rag_doc_analysis_uri",
		LogLevel:   http_client.LogAll,
	})
	if err != nil {
		return nil, err
	}
	var resp = &DocUrlResp{}
	if err := json.Unmarshal(result, resp); err != nil {
		log.Errorf(err.Error())
		return nil, err
	}
	if resp.ResponseInfo.Code != successCode {
		return nil, errors.New(resp.ResponseInfo.Message)
	}
	if len(resp.FileName) == 0 {
		return nil, errors.New("解析文件失败")
	}
	resp.Url = docUrlParams.Url
	return resp, nil
}

// RebuildSegmentType 转换分段类型
func RebuildSegmentType(segmentType string) string {
	if segmentType == "0" {
		return SplitByDefault
	}
	return SplitByDesign
}

func RebuildFileName(docId, docType, docName string) string {
	if docType == "url" {
		return docId + ".txt"
	}
	return docName
}

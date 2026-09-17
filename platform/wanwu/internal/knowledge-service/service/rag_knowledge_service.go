package service

import (
	"context"
	"encoding/json"
	"errors"
	"strings"
	"time"

	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/config"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/http"
	http_client "github.com/UnicomAI/wanwu/pkg/http-client"
	"github.com/UnicomAI/wanwu/pkg/log"
)

const (
	successCode = 0
)

type RagCreateParams struct {
	UserId           string `json:"userId"`
	Name             string `json:"knowledgeBase"`
	KnowledgeBaseId  string `json:"kb_id"`
	EmbeddingModelId string `json:"embedding_model_id"`
}

type RagCommonResp struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type RagUpdateParams struct {
	UserId          string `json:"userId"`
	KnowledgeBaseId string `json:"kb_id"`
	OldKbName       string `json:"old_kb_name"`
	NewKbName       string `json:"new_kb_name"`
}

type RagDeleteParams struct {
	UserId            string `json:"userId"`
	KnowledgeBaseName string `json:"knowledgeBase"`
}

// RagKnowledgeCreate rag创建知识库
func RagKnowledgeCreate(ctx context.Context, ragCreateParams *RagCreateParams) error {
	ragServer := config.GetConfig().RagServer
	url := ragServer.Endpoint + ragServer.InitKnowledgeUri
	paramsByte, err := json.Marshal(ragCreateParams)
	if err != nil {
		return err
	}
	result, err := http.GetClient().PostJson(ctx, &http_client.HttpRequestParams{
		Url:        url,
		Body:       paramsByte,
		Timeout:    time.Duration(ragServer.Timeout) * time.Second,
		MonitorKey: "rag_knowledge_create",
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

// RagKnowledgeUpdate rag更新知识库
func RagKnowledgeUpdate(ctx context.Context, ragUpdateParams *RagUpdateParams) error {
	ragServer := config.GetConfig().RagServer
	url := ragServer.Endpoint + ragServer.UpdateKnowledgeUri
	paramsByte, err := json.Marshal(ragUpdateParams)
	if err != nil {
		return err
	}
	result, err := http.GetClient().PostJson(ctx, &http_client.HttpRequestParams{
		Url:        url,
		Body:       paramsByte,
		Timeout:    time.Duration(ragServer.Timeout) * time.Second,
		MonitorKey: "rag_knowledge_update",
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

// RagKnowledgeDelete rag更新知识库删除
func RagKnowledgeDelete(ctx context.Context, ragDeleteParams *RagDeleteParams) error {
	ragServer := config.GetConfig().RagServer
	url := ragServer.Endpoint + ragServer.DeleteKnowledgeUri
	paramsByte, err := json.Marshal(ragDeleteParams)
	if err != nil {
		return err
	}
	result, err := http.GetClient().PostJson(ctx, &http_client.HttpRequestParams{
		Url:        url,
		Body:       paramsByte,
		Timeout:    time.Duration(ragServer.Timeout) * time.Second,
		MonitorKey: "rag_knowledge_delete",
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

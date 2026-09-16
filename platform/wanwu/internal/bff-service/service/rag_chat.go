package service

import (
	"fmt"
	"io"
	"strings"

	rag_service "github.com/UnicomAI/wanwu/api/proto/rag-service"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	"github.com/UnicomAI/wanwu/pkg/log"
	sse_util "github.com/UnicomAI/wanwu/pkg/sse-util"
	"github.com/UnicomAI/wanwu/pkg/util"
	"github.com/gin-gonic/gin"
)

// ChatRagStream rag私域问答
func ChatRagStream(ctx *gin.Context, userId, orgId string, req request.ChatRagRequest) error {
	//1. CallRagChatStream
	chatCh, err := CallRagChatStream(ctx, userId, orgId, req)
	if err != nil {
		return err
	}
	// 2. 流式返回结果
	_ = sse_util.NewSSEWriter(ctx, fmt.Sprintf("[RAG] %v user %v org %v", req.RagID, userId, orgId), sse_util.DONE_MSG).
		WriteStream(chatCh, nil, buildRagChatRespLineProcessor(), nil)
	return nil
}

// CallRagChatStream 调用rag对话
func CallRagChatStream(ctx *gin.Context, userId, orgId string, req request.ChatRagRequest) (<-chan string, error) {
	stream, err := rag.ChatRag(ctx, &rag_service.ChatRagReq{
		RagId:    req.RagID,
		Question: req.Question,
		Identity: &rag_service.Identity{
			UserId: userId,
			OrgId:  orgId,
		},
	})
	if err != nil {
		return nil, err
	}

	ret := make(chan string, 128)
	go func() {
		defer util.PrintPanicStack()
		defer close(ret)
		log.Infof("[RAG] %v user %v org %v start, query: %s", req.RagID, userId, orgId, req.Question)
		for {
			s, err := stream.Recv()
			if err == io.EOF {
				log.Infof("[RAG] %v user %v org %v stop", req.RagID, userId, orgId)
				break
			}
			if err != nil {
				log.Errorf("[RAG] %v user %v org %v recv err: %v", req.RagID, userId, orgId, err)
				break
			}
			ret <- s.Content
		}
	}()
	return ret, nil
}

// buildRagChatRespLineProcessor 构造rag对话结果行处理器
func buildRagChatRespLineProcessor() func(*gin.Context, string, interface{}) (string, bool, error) {
	return func(c *gin.Context, lineText string, params interface{}) (string, bool, error) {
		if strings.HasPrefix(lineText, "error:") {
			errorText := fmt.Sprintf("data: {\"code\": \"-1\", \"msg\": \"%s\"}\n\n", strings.TrimPrefix(lineText, "error:"))
			return errorText, false, nil
		}
		if strings.HasPrefix(lineText, "data:") {
			return lineText + "\n\n", false, nil
		}
		return lineText + "\n\n", false, nil
	}
}

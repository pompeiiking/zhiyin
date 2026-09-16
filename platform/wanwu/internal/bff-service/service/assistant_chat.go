package service

import (
	"fmt"
	"io"
	"strings"

	app_service "github.com/UnicomAI/wanwu/api/proto/app-service"
	assistant_service "github.com/UnicomAI/wanwu/api/proto/assistant-service"
	"github.com/UnicomAI/wanwu/internal/bff-service/model/request"
	"github.com/UnicomAI/wanwu/pkg/log"
	sse_util "github.com/UnicomAI/wanwu/pkg/sse-util"
	"github.com/UnicomAI/wanwu/pkg/util"
	"github.com/gin-gonic/gin"
)

func CallAssistantConversationStream(ctx *gin.Context, userId, orgId string, req request.ConversionStreamRequest) (<-chan string, error) {
	appList, err := app.GetAppListByIds(ctx.Request.Context(), &app_service.GetAppListByIdsReq{
		AppIdsList: []string{req.AssistantId},
	})
	if err != nil {
		return nil, err
	}

	var publishType string
	if len(appList.Infos) > 0 {
		publishType = appList.Infos[0].PublishType
	}

	stream, err := assistant.AssistantConversionStream(ctx.Request.Context(), &assistant_service.AssistantConversionStreamReq{
		AssistantId:    req.AssistantId,
		ConversationId: req.ConversationId,
		FileInfo: &assistant_service.ConversionStreamFile{
			FileName: req.FileInfo.FileName,
			FileSize: req.FileInfo.FileSize,
			FileUrl:  req.FileInfo.FileUrl,
		},
		Trial:          req.Trial,
		Prompt:         req.Prompt,
		AppPublishType: publishType,
		Identity: &assistant_service.Identity{
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
		log.Infof("[Agent] %v conversation %v user %v org %v start, query: %s", req.AssistantId, req.ConversationId, userId, orgId, req.Prompt)
		for {
			s, err := stream.Recv()
			if err == io.EOF {
				log.Infof("[Agent] %v conversation %v user %v org %v stop", req.AssistantId, req.ConversationId, userId, orgId)
				break
			}
			if err != nil {
				log.Errorf("[Agent] %v conversation %v user %v org %v recv err: %v", req.AssistantId, req.ConversationId, userId, orgId, err)
				break
			}
			ret <- s.Content
		}
	}()
	return ret, nil
}

func AssistantConversionStream(ctx *gin.Context, userId, orgId string, req request.ConversionStreamRequest) error {
	// 1. CallAssistantConversationStream
	chatCh, err := CallAssistantConversationStream(ctx, userId, orgId, req)
	if err != nil {
		return err
	}
	// 2. 流式返回结果
	_ = sse_util.NewSSEWriter(ctx, fmt.Sprintf("[Agent] %v conversation %v user %v org %v recv", req.AssistantId, req.ConversationId, userId, orgId), sse_util.DONE_MSG).
		WriteStream(chatCh, nil, buildAgentChatRespLineProcessor(), nil)
	return nil
}

// buildAgentChatRespLineProcessor 构造agent对话结果行处理器
func buildAgentChatRespLineProcessor() func(*gin.Context, string, interface{}) (string, bool, error) {
	return func(c *gin.Context, lineText string, params interface{}) (string, bool, error) {
		if strings.HasPrefix(lineText, "error:") {
			errorText := fmt.Sprintf("data: {\"code\": \"-1\", \"msg\": \"%s\"}\n\n", strings.TrimPrefix(lineText, "error:"))
			return errorText, false, nil
		}
		if strings.HasPrefix(lineText, "data:") {
			return lineText + "\n\n", false, nil
		}
		return "data:" + lineText + "\n\n", false, nil
	}
}

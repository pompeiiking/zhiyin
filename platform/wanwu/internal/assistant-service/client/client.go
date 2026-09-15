package client

import (
	"context"

	err_code "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/assistant-service/client/model"
)

type IClient interface {
	//================Assistant================
	CreateAssistant(ctx context.Context, assistant *model.Assistant) *err_code.Status
	UpdateAssistant(ctx context.Context, assistant *model.Assistant) *err_code.Status
	DeleteAssistant(ctx context.Context, assistantID uint32) *err_code.Status
	GetAssistant(ctx context.Context, assistantID uint32) (*model.Assistant, *err_code.Status)
	GetAssistantsByIDs(ctx context.Context, assistantIDs []uint32) ([]*model.Assistant, *err_code.Status)
	GetAssistantList(ctx context.Context, userID, orgID string, name string) ([]*model.Assistant, int64, *err_code.Status)
	CheckSameAssistantName(ctx context.Context, userID, orgID, name string) *err_code.Status

	//================AssistantAction================
	CreateAssistantAction(ctx context.Context, action *model.AssistantAction) *err_code.Status
	DeleteAssistantAction(ctx context.Context, actionID uint32) *err_code.Status
	UpdateAssistantAction(ctx context.Context, action *model.AssistantAction) *err_code.Status
	GetAssistantAction(ctx context.Context, actionID uint32) (*model.AssistantAction, *err_code.Status)
	GetAssistantActionsByAssistantID(ctx context.Context, assistantID string) ([]*model.AssistantAction, *err_code.Status)

	//================AssistantWorkflow================
	CreateAssistantWorkflow(ctx context.Context, workflow *model.AssistantWorkflow) *err_code.Status
	DeleteAssistantWorkflow(ctx context.Context, workflowID uint32) *err_code.Status
	UpdateAssistantWorkflow(ctx context.Context, workflow *model.AssistantWorkflow) *err_code.Status
	GetAssistantWorkflow(ctx context.Context, workflowID uint32) (*model.AssistantWorkflow, *err_code.Status)
	GetAssistantWorkflowsByAssistantID(ctx context.Context, assistantID string) ([]*model.AssistantWorkflow, *err_code.Status)

	//================Conversation================
	CreateConversation(ctx context.Context, conversation *model.Conversation) *err_code.Status
	UpdateConversation(ctx context.Context, conversation *model.Conversation) *err_code.Status
	DeleteConversation(ctx context.Context, conversationID uint32) *err_code.Status
	GetConversation(ctx context.Context, conversationID uint32) (*model.Conversation, *err_code.Status)
	GetConversationList(ctx context.Context, assistantID, userID, orgID string, offset, limit int32) ([]*model.Conversation, int64, *err_code.Status)
}

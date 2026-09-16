package client

import (
	"context"

	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/mcp-service/client/model"
)

type IClient interface {
	CheckMCPExist(ctx context.Context, orgID, userID, mcpSquareID string) (bool, *errs.Status)
	GetMCP(ctx context.Context, mcpID uint32) (*model.MCPClient, *errs.Status)
	CreateMCP(ctx context.Context, mcp *model.MCPClient) *errs.Status
	DeleteMCP(ctx context.Context, mcpID uint32) *errs.Status
	ListMCPs(ctx context.Context, orgID, userID, name string) ([]*model.MCPClient, *errs.Status)
}

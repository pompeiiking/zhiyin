package config

import (
	"fmt"
	"os"
	"path/filepath"
)

const (
	ConfigDir = "configs/microservice/mcp-service/configs/"
	MCPLogo   = "mcp.png"
)

type McpConfig struct {
	McpSquareId string          `json:"mcp_square_id" mapstructure:"mcp_square_id"`
	Name        string          `json:"name" mapstructure:"name"`
	Category    string          `json:"category" mapstructure:"category"`
	Desc        string          `json:"desc" mapstructure:"desc"`
	From        string          `json:"from" mapstructure:"from"`
	AvatarPath  string          `json:"avatar_path" mapstructure:"avatar_path"`
	DetailPath  string          `json:"detail_path" mapstructure:"detail_path"`
	Detail      string          `json:"-" mapstructure:"-"`
	Feature     string          `json:"feature" mapstructure:"feature"`
	Manual      string          `json:"manual" mapstructure:"manual"`
	Scenario    string          `json:"scenario" mapstructure:"scenario"`
	SseUrl      string          `json:"sse_url" mapstructure:"sse_url"`
	Summary     string          `json:"summary" mapstructure:"summary"`
	Tools       []McpToolConfig `json:"tools" mapstructure:"tools"`
}

type McpToolConfig struct {
	Name        string               `json:"name" mapstructure:"name"`
	Description string               `json:"description" mapstructure:"description"`
	InputSchema McpInputSchemaConfig `json:"input_schema" mapstructure:"input_schema"`
}

type McpInputSchemaConfig struct {
	Type       string                `json:"type" mapstructure:"type"`
	Required   []string              `json:"required" mapstructure:"required"`
	Properties []McpPropertiesConfig `json:"properties" mapstructure:"properties"`
}

type McpPropertiesConfig struct {
	Field       string `json:"field" mapstructure:"field"`
	Type        string `json:"type" mapstructure:"type"`
	Description string `json:"description" mapstructure:"description"`
}

func (mcp *McpConfig) load() error {
	detailPath := filepath.Join(ConfigDir, mcp.DetailPath)
	b, err := os.ReadFile(detailPath)
	if err != nil {
		return fmt.Errorf("load mcp %v detail path %v err: %v", mcp.McpSquareId, detailPath, err)
	}
	mcp.Detail = string(b)
	avatarPath := filepath.Join(ConfigDir, mcp.AvatarPath)
	if _, err = os.ReadFile(avatarPath); err != nil {
		return fmt.Errorf("load mcp %v avatar path %v err: %v", mcp.McpSquareId, avatarPath, err)
	}
	return nil
}

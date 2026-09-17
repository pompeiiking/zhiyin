package config

import (
	"github.com/UnicomAI/wanwu/pkg/db"
	"github.com/UnicomAI/wanwu/pkg/log"
	"github.com/UnicomAI/wanwu/pkg/util"
)

var (
	_c *Config
)

type Config struct {
	Server ServerConfig `json:"server" mapstructure:"server"`
	Log    LogConfig    `json:"log" mapstructure:"log"`
	DB     db.Config    `json:"db" mapstructure:"db"`
	Mcps   []*McpConfig `json:"mcps" mapstructure:"mcps"`
}

type ServerConfig struct {
	GrpcEndpoint   string `json:"grpc_endpoint" mapstructure:"grpc_endpoint"`
	MaxRecvMsgSize int    `json:"max_recv_msg_size" mapstructure:"max_recv_msg_size"`
}

type LogConfig struct {
	Std   bool         `json:"std" mapstructure:"std"`
	Level string       `json:"level" mapstructure:"level"`
	Logs  []log.Config `json:"logs" mapstructure:"logs"`
}

func LoadConfig(in string) error {
	_c = &Config{}
	if err := util.LoadConfig(in, _c); err != nil {
		return err
	}
	for _, mcp := range _c.Mcps {
		if err := mcp.load(); err != nil {
			return err
		}
	}
	return nil
}

func Cfg() *Config {
	if _c == nil {
		log.Panicf("cfg nil")
	}
	return _c
}

func (c *Config) MCP(mcpSquareID string) (McpConfig, bool) {
	for _, mcp := range c.Mcps {
		if mcp.McpSquareId == mcpSquareID {
			return *mcp, true
		}
	}
	return McpConfig{}, false
}

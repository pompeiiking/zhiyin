package tool_init

import (
	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg"
	"github.com/UnicomAI/wanwu/pkg/util"
)

var toolInit = ToolInit{}

type ToolInit struct {
}

func init() {
	pkg.AddContainer(toolInit)
}

func (c ToolInit) LoadType() string {
	return "toolInit"
}

func (c ToolInit) Load() error {
	err := util.InitTimeLocal()
	if err != nil {
		return err
	}
	return nil
}

func (c ToolInit) StopPriority() int {
	return pkg.DefaultPriority
}

func (c ToolInit) Stop() error {
	return nil
}

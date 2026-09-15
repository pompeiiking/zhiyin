package async_task

import (
	"context"
)

const (
	KnowledgeDeleteTaskType = 1 //知识库删除
	DocDeleteTaskType       = 2 // 文档列表删除
	DocImportTaskType       = 3 // 文档导入
)

type KnowledgeDeleteParams struct {
	KnowledgeId string `json:"knowledgeId"`
}

type DocDeleteParams struct {
	DocIdList []uint32 `json:"docIdList"`
}

type DocImportTaskParams struct {
	TaskId string `json:"taskId"`
}

type BusinessTaskService interface {
	BuildServiceType() uint32
	//InitTask 初始化任务
	InitTask() error
	//SubmitTask 提交任务
	SubmitTask(ctx context.Context, params interface{}) error
}

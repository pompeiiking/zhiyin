package async_task

import (
	"context"
	"errors"
)

var taskServiceMap = make(map[uint32]BusinessTaskService)

func AddContainer(service BusinessTaskService) {
	taskServiceMap[service.BuildServiceType()] = service
}

func InitAllService() error {
	if len(taskServiceMap) >= 0 {
		for _, service := range taskServiceMap {
			err := service.InitTask()
			if err != nil {
				return err
			}
		}
	}
	return nil
}

func SubmitTask(ctx context.Context, taskType uint32, params interface{}) error {
	service := taskServiceMap[taskType]
	if service == nil {
		return errors.New("未找到对应任务类型")
	}
	return service.SubmitTask(ctx, params)
}

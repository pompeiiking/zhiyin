package orm

import (
	"context"
	"time"

	err_code "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/assistant-service/client/model"
	"github.com/UnicomAI/wanwu/internal/assistant-service/client/orm/sqlopt"
	"gorm.io/gorm"
)

func (c *Client) UpdateAssistantWorkflow(ctx context.Context, workflow *model.AssistantWorkflow) *err_code.Status {
	if workflow.ID == 0 {
		return toErrStatus("assistant_workflow_update", "update assistant workflow but id 0")
	}
	return c.transaction(ctx, func(tx *gorm.DB) *err_code.Status {
		if err := tx.Model(workflow).Updates(map[string]interface{}{
			"enable":     workflow.Enable,
			"updated_at": time.Now().UnixMilli(),
		}).Error; err != nil {
			return toErrStatus("assistant_workflow_update", err.Error())
		}
		return nil
	})
}

func (c *Client) GetAssistantWorkflow(ctx context.Context, workflowID uint32) (*model.AssistantWorkflow, *err_code.Status) {
	var workflow *model.AssistantWorkflow
	return workflow, c.transaction(ctx, func(tx *gorm.DB) *err_code.Status {
		workflow = &model.AssistantWorkflow{}
		if err := sqlopt.WithID(workflowID).Apply(tx).First(workflow).Error; err != nil {
			return toErrStatus("assistant_workflow_get", err.Error())
		}
		return nil
	})
}

func (c *Client) GetAssistantWorkflowsByAssistantID(ctx context.Context, assistantID string) ([]*model.AssistantWorkflow, *err_code.Status) {
	var workflows []*model.AssistantWorkflow
	return workflows, c.transaction(ctx, func(tx *gorm.DB) *err_code.Status {
		if err := tx.Where("assistant_id = ?", assistantID).Find(&workflows).Error; err != nil {
			return toErrStatus("assistant_workflows_get_by_assistant_id", err.Error())
		}
		return nil
	})
}

func (c *Client) CreateAssistantWorkflow(ctx context.Context, workflow *model.AssistantWorkflow) *err_code.Status {
	if workflow.ID != 0 {
		return toErrStatus("assistant_workflow_create", "create assistant workflow but id not 0")
	}
	return c.transaction(ctx, func(tx *gorm.DB) *err_code.Status {
		// 创建Workflow
		if err := tx.Create(workflow).Error; err != nil {
			return toErrStatus("assistant_workflow_create", err.Error())
		}

		// 获取Assistant
		assistant := &model.Assistant{}
		if err := sqlopt.WithID(workflow.AssistantId).Apply(tx).First(assistant).Error; err != nil {
			return toErrStatus("assistant_get", err.Error())
		}

		// 更新HasWorkflow字段
		if !assistant.HasWorkflow {
			assistant.HasWorkflow = true
			if err := tx.Model(assistant).Updates(map[string]interface{}{
				"has_workflow": assistant.HasWorkflow,
			}).Error; err != nil {
				return toErrStatus("assistant_update", err.Error())
			}
		}

		return nil
	})
}

func (c *Client) DeleteAssistantWorkflow(ctx context.Context, workflowID uint32) *err_code.Status {
	return c.transaction(ctx, func(tx *gorm.DB) *err_code.Status {
		// 获取Workflow以获得AssistantId
		workflow := &model.AssistantWorkflow{}
		if err := sqlopt.WithID(workflowID).Apply(tx).First(workflow).Error; err != nil {
			return toErrStatus("assistant_workflow_get", err.Error())
		}
		assistantId := workflow.AssistantId

		// 删除Workflow
		if err := sqlopt.WithID(workflowID).Apply(tx).Delete(&model.AssistantWorkflow{}).Error; err != nil {
			return toErrStatus("assistant_workflow_delete", err.Error())
		}

		// 查询是否还有其他Workflow
		var count int64
		if err := tx.Where("assistant_id = ?", assistantId).Model(&model.AssistantWorkflow{}).Count(&count).Error; err != nil {
			return toErrStatus("assistant_workflows_count", err.Error())
		}

		// 如果没有其他Workflow，更新Assistant的HasWorkflow字段
		if count == 0 {
			assistant := &model.Assistant{}
			if err := sqlopt.WithID(assistantId).Apply(tx).First(assistant).Error; err != nil {
				return toErrStatus("assistant_get", err.Error())
			}
			assistant.HasWorkflow = false
			if err := tx.Model(assistant).Updates(map[string]interface{}{
				"has_workflow": assistant.HasWorkflow,
			}).Error; err != nil {
				return toErrStatus("assistant_update", err.Error())
			}
		}

		return nil
	})
}

package orm

import (
	"context"
	"time"

	err_code "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/assistant-service/client/model"
	"github.com/UnicomAI/wanwu/internal/assistant-service/client/orm/sqlopt"
	"gorm.io/gorm"
)

func (c *Client) UpdateAssistantAction(ctx context.Context, action *model.AssistantAction) *err_code.Status {
	if action.ID == 0 {
		return toErrStatus("assistant_action_update", "update assistant action but id 0")
	}
	return c.transaction(ctx, func(tx *gorm.DB) *err_code.Status {
		if err := tx.Model(action).Updates(map[string]interface{}{
			"action_name":        action.ActionName,
			"api_schema":         action.APISchema,
			"api_auth":           action.APIAuth,
			"name":               action.Name,
			"method":             action.Method,
			"path":               action.Path,
			"api_key":            action.APIKey,
			"custom_header_name": action.CustomHeaderName,
			"auth_type":          action.AuthType,
			"type":               action.Type,
			"enable":             action.Enable,
			"updated_at":         time.Now().UnixMilli(),
		}).Error; err != nil {
			return toErrStatus("assistant_action_update", err.Error())
		}
		return nil
	})
}

func (c *Client) GetAssistantAction(ctx context.Context, actionID uint32) (*model.AssistantAction, *err_code.Status) {
	var action *model.AssistantAction
	return action, c.transaction(ctx, func(tx *gorm.DB) *err_code.Status {
		action = &model.AssistantAction{}
		if err := sqlopt.WithID(actionID).Apply(tx).First(action).Error; err != nil {
			return toErrStatus("assistant_action_get", err.Error())
		}
		return nil
	})
}

func (c *Client) GetAssistantActionsByAssistantID(ctx context.Context, assistantID string) ([]*model.AssistantAction, *err_code.Status) {
	var actions []*model.AssistantAction
	return actions, c.transaction(ctx, func(tx *gorm.DB) *err_code.Status {
		if err := tx.Where("assistant_id = ?", assistantID).Find(&actions).Error; err != nil {
			return toErrStatus("assistant_actions_get_by_assistant_id", err.Error())
		}
		return nil
	})
}

func (c *Client) CreateAssistantAction(ctx context.Context, action *model.AssistantAction) *err_code.Status {
	if action.ID != 0 {
		return toErrStatus("assistant_action_create", "create assistant action but id not 0")
	}
	return c.transaction(ctx, func(tx *gorm.DB) *err_code.Status {
		// 创建Action
		if err := tx.Create(action).Error; err != nil {
			return toErrStatus("assistant_action_create", err.Error())
		}

		// 获取Assistant
		assistant := &model.Assistant{}
		if err := sqlopt.WithID(action.AssistantId).Apply(tx).First(assistant).Error; err != nil {
			return toErrStatus("assistant_get", err.Error())
		}

		// 更新HasAction字段
		if !assistant.HasAction {
			assistant.HasAction = true
			if err := tx.Model(assistant).Updates(map[string]interface{}{
				"has_action": assistant.HasAction,
			}).Error; err != nil {
				return toErrStatus("assistant_update", err.Error())
			}
		}

		return nil
	})
}

func (c *Client) DeleteAssistantAction(ctx context.Context, actionID uint32) *err_code.Status {
	return c.transaction(ctx, func(tx *gorm.DB) *err_code.Status {
		// 获取Action以获得AssistantId
		action := &model.AssistantAction{}
		if err := sqlopt.WithID(actionID).Apply(tx).First(action).Error; err != nil {
			return toErrStatus("assistant_action_get", err.Error())
		}
		assistantId := action.AssistantId

		// 删除Action
		if err := sqlopt.WithID(actionID).Apply(tx).Delete(&model.AssistantAction{}).Error; err != nil {
			return toErrStatus("assistant_action_delete", err.Error())
		}

		// 查询是否还有其他Action
		var count int64
		if err := tx.Where("assistant_id = ?", assistantId).Model(&model.AssistantAction{}).Count(&count).Error; err != nil {
			return toErrStatus("assistant_actions_count", err.Error())
		}

		// 如果没有其他Action，更新Assistant的HasAction字段
		if count == 0 {
			assistant := &model.Assistant{}
			if err := sqlopt.WithID(assistantId).Apply(tx).First(assistant).Error; err != nil {
				return toErrStatus("assistant_get", err.Error())
			}
			assistant.HasAction = false
			if err := tx.Model(assistant).Updates(map[string]interface{}{
				"has_action": assistant.HasAction,
			}).Error; err != nil {
				return toErrStatus("assistant_update", err.Error())
			}
		}

		return nil
	})
}

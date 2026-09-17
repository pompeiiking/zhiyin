package orm

import (
	"context"
	"errors"
	"time"

	errs "github.com/UnicomAI/wanwu/api/proto/err-code"
	"github.com/UnicomAI/wanwu/internal/app-service/client/model"
	"github.com/UnicomAI/wanwu/internal/app-service/client/orm/sqlopt"
	"gorm.io/gorm"
)

func (c *Client) GetExplorationAppList(ctx context.Context, userId, name, appType, searchType string) ([]*ExplorationAppInfo, *errs.Status) {
	var apps []*model.App
	var ret []*ExplorationAppInfo
	var favoriteApps []*model.AppFavorite
	if err := sqlopt.SQLOptions(
		sqlopt.WithUserID(userId),
		sqlopt.WithAppType(appType),
	).Apply(c.db.WithContext(ctx)).Find(&favoriteApps).Error; err != nil {
		return nil, toErrStatus("app_explore_favorite_apps_get", err.Error())
	}
	switch searchType {
	case "", "all", "private":
		query := sqlopt.SQLOptions(
			sqlopt.WithAppType(appType),
			sqlopt.WithSearchType(userId, searchType),
		).Apply(c.db.WithContext(ctx))
		if err := query.Order("id DESC").Find(&apps).Error; err != nil {
			return nil, toErrStatus("app_explore_apps_get", err.Error())
		}
		for _, app := range apps {
			appInfo := &ExplorationAppInfo{
				AppId:       app.AppID,
				AppType:     app.AppType,
				CreatedAt:   app.CreatedAt,
				UpdatedAt:   app.UpdatedAt,
				IsFavorite:  false,
				PublishType: app.PublishType,
			}
			for _, favoriteApp := range favoriteApps {
				if favoriteApp.AppID == app.AppID && favoriteApp.AppType == app.AppType {
					appInfo.IsFavorite = true
					break
				}
			}
			ret = append(ret, appInfo)
		}
		return ret, nil
	case "favorite":
		for _, app := range favoriteApps {
			ret = append(ret, &ExplorationAppInfo{
				AppId:       app.AppID,
				AppType:     app.AppType,
				CreatedAt:   app.CreatedAt,
				UpdatedAt:   app.UpdatedAt,
				IsFavorite:  true,
				PublishType: "",
			})
		}
	case "history":
		var historyApps []*model.AppHistory
		oneMonthAgo := time.Now().AddDate(0, -1, 0).UnixMilli()
		if err := sqlopt.SQLOptions(
			sqlopt.WithUserID(userId),
			sqlopt.WithAppType(appType),
			sqlopt.StartUpdatedAt(oneMonthAgo),
		).Apply(c.db.WithContext(ctx)).
			Order("updated_at DESC").Find(&historyApps).Error; err != nil {
			return nil, toErrStatus("app_history_apps_get", err.Error())
		}
		for _, historyApp := range historyApps {
			appInfo := &ExplorationAppInfo{
				AppId:      historyApp.AppID,
				AppType:    historyApp.AppType,
				CreatedAt:  historyApp.CreatedAt,
				UpdatedAt:  historyApp.UpdatedAt,
				IsFavorite: false,
			}
			for _, favoriteApp := range favoriteApps {
				if favoriteApp.AppID == historyApp.AppID && favoriteApp.AppType == historyApp.AppType {
					appInfo.IsFavorite = true
					break
				}
			}
			ret = append(ret, appInfo)
		}
		return ret, nil

	}
	return ret, nil
}

func (c *Client) ChangeExplorationAppFavorite(ctx context.Context, userId, orgId, appId, appType string, isFavorite bool) *errs.Status {
	var existingApp model.AppFavorite
	if isFavorite {
		err := sqlopt.SQLOptions(
			sqlopt.WithUserID(userId),
			sqlopt.WithAppID(appId),
			sqlopt.WithAppType(appType),
		).Apply(c.db.WithContext(ctx)).First(&existingApp).Error
		if err != nil {
			if errors.Is(err, gorm.ErrRecordNotFound) {
				newApp := model.AppFavorite{
					UserID:  userId,
					AppID:   appId,
					AppType: appType,
				}
				if err := c.db.WithContext(ctx).Create(&newApp).Error; err != nil {
					return toErrStatus("app_favorite_app_create", appId, err.Error())
				}
				return nil
			}
			return toErrStatus("app_favorite_app_query", appId, err.Error())
		}
		return nil
	}
	if err := sqlopt.SQLOptions(
		sqlopt.WithAppID(appId),
		sqlopt.WithUserID(userId),
		sqlopt.WithAppType(appType),
	).Apply(c.db.WithContext(ctx)).Delete(&existingApp).Error; err != nil {
		return toErrStatus("app_favorite_app_delete", appId, err.Error())
	}
	return nil
}

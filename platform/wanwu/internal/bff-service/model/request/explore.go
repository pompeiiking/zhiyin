package request

type GetExplorationAppListRequest struct {
	Name       string `form:"name" json:"name"`             // 应用名称
	AppType    string `form:"appType" json:"appType"`       // 应用类型
	SearchType string `form:"searchType" json:"searchType"` // 搜索类型(all(全部),favorite(显示收藏的),private(显示私密发布的),history(历史应用))
}

func (g GetExplorationAppListRequest) Check() error {
	return nil
}

type ChangeExplorationAppFavoriteRequest struct {
	AppId      string `json:"appId" validate:"required"`   // 应用id
	AppType    string `json:"appType" validate:"required"` // 应用类型
	IsFavorite bool   `json:"isFavorite"`                  // 是否收藏
}

func (c ChangeExplorationAppFavoriteRequest) Check() error {
	return nil
}

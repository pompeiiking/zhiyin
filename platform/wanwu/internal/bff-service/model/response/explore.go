package response

type ExplorationAppInfo struct {
	AppBriefInfo
	IsFavorite bool `json:"isFavorite"` // 收藏标签
}

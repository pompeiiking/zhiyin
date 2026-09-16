package response

import "github.com/UnicomAI/wanwu/internal/bff-service/model/request"

type AppBriefInfo struct {
	AppId       string         `json:"appId"`       // 应用id
	AppType     string         `json:"appType"`     // 应用类型
	Avatar      request.Avatar `json:"avatar"`      // 应用图标
	Name        string         `json:"name"`        // 应用名称
	Desc        string         `json:"desc"`        // 应用描述
	CreatedAt   string         `json:"createdAt"`   // 应用创建时间
	UpdatedAt   string         `json:"updatedAt"`   // 应用更新时间(用于历史记录排序)
	PublishType string         `json:"publishType"` // 发布类型(public:公开发布,private:私密发布)
}

type WorkFlowInfo struct {
	Id           string `json:"id"`           // 应用id
	ConfigDesc   string `json:"configDesc"`   // 应用简介
	ConfigENName string `json:"configENName"` // 应用英文名称
	ConfigName   string `json:"configName"`   // 应用名称
	ExampleFlag  int    `json:"example_flag"` // 示例标识
	IsStream     int    `json:"is_stream"`    // 流式标识
	OrgID        string `json:"orgID"`        // 组织ID
	Status       string `json:"status"`       // 应用状态
	UpdatedTime  string `json:"updatedTime"`  // 应用更新时间
	UserID       string `json:"userID"`       // 用户ID
}

type WorkFlowListResp struct {
	Code    int                 `json:"code"`
	Message string              `json:"msg"`
	Data    *WorkFlowResultResp `json:"data"`
}

type WorkFlowResultResp struct {
	List     []WorkFlowInfo `json:"list"`
	Total    int64          `json:"total"`
	PageNo   int            `json:"pageNo"`
	PageSize int            `json:"pageSize"`
}

type DeleteWorkFlowResp struct {
	Code    int    `json:"code"`
	Message string `json:"msg"`
}

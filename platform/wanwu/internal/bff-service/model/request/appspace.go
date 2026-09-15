package request

type DeleteAppSpaceAppRequest struct {
	AppId   string `json:"appId" validate:"required"`   // 应用ID
	AppType string `json:"appType" validate:"required"` // 应用类型
}

func (req DeleteAppSpaceAppRequest) Check() error {
	return nil
}

type GetAppSpaceAppListRequest struct {
	Name    string `form:"name" json:"name"`
	AppType string `form:"appType" json:"appType"`
}

type PublishAppRequest struct {
	AppId       string `json:"appId"`       // 应用ID
	AppType     string `json:"appType"`     // 应用类型
	PublishType string `json:"publishType"` // 发布类型(public:公开发布,private:私密发布)
}

func (req PublishAppRequest) Check() error {
	return nil
}

type GetApiBaseUrlRequest struct {
	AppId   string `form:"appId" json:"appId" validate:"required"`     // 应用ID
	AppType string `form:"appType" json:"appType" validate:"required"` // 应用类型
}

func (req GetApiBaseUrlRequest) Check() error {
	return nil
}

func (o *GetAppSpaceAppListRequest) Check() error {
	return nil
}

type DeleteWorkFlowRequest struct {
	AppId string `form:"workflowID" json:"workflowID" validate:"required"` // 应用ID
}

func (o *DeleteWorkFlowRequest) Check() error {
	return nil
}

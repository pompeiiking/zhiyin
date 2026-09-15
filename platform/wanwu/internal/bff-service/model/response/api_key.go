package response

type ApiResponse struct {
	ApiID     string `json:"apiId" `    // ApiID
	ApiKey    string `json:"apiKey"`    // 生成的ApiKey
	CreatedAt string `json:"createdAt"` // 创建ApiKey的时间
}

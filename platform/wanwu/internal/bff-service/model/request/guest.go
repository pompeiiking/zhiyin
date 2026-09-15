package request

// Login 登录请求的参数
type Login struct {
	Username string `json:"username" validate:"required"` // 用户名
	Password string `json:"password" validate:"required"` // 密码
	Key      string `json:"key" validate:"required"`      // 客户端key
	Code     string `json:"code" validate:"required"`     // 验证码
}

func (l *Login) Check() error {
	return nil
}

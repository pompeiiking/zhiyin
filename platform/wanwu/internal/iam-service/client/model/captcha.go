package model

// Captcha 验证码
type Captcha struct {
	// 客户端key
	ID string `gorm:"primaryKey"`
	// 验证码
	Code string
	// 本次验证码交互开始时间，并不是当前验证码的创建时间
	StartAt int64
	// 当前验证码的创建时间
	RefreshAt int64
	// 从start_at开始的刷新次数
	RefreshCnt int32
}

package response

type Login struct {
	UID           string            `json:"uid"`
	Username      string            `json:"username"`
	Token         string            `json:"token"`
	ExpiresAt     int64             `json:"expiresAt"`
	ExpireIn      string            `json:"expireIn"`
	Nickname      string            `json:"nickname"`
	OrgPermission UserOrgPermission `json:"orgPermission"` // 用户所在组织权限
	Orgs          []IDName          `json:"orgs"`          // 用户所在组织列表
	Language      Language          `json:"language"`      // 语言
}

type Captcha struct {
	Key string `json:"key"` // 客户端key
	B64 string `json:"b64"` // 验证码png图片base64字符串
}

type LogoCustomInfo struct {
	Version string      `json:"version"` // 版本
	Login   CustomLogin `json:"login"`   // 登录页标题信息
	Home    CustomHome  `json:"home"`    // 首页标题信息
	Tab     CustomTab   `json:"tab"`     // 标签页信息
}

type CustomLogin struct {
	BackgroundPath   string `json:"backgroundPath"`   // 登录页背景图路径
	LoginButtonColor string `json:"loginButtonColor"` // 登录按钮颜色
	WelcomeText      string `json:"welcomeText"`      // 登录页欢迎标词
}

type CustomHome struct {
	LogoPath string `json:"logoPath"` // 首页logo路径，例如/v1/static/logo/title_logo.png
	Title    string `json:"title"`    // 首页标题
}

type CustomTab struct {
	LogoPath string `json:"logoPath"` //标签页图标路径
	Title    string `json:"title"`    //标签页标题
}

type LanguageSelect struct {
	Languages       []Language `json:"languages"`
	DefaultLanguage Language   `json:"defaultLanguage"`
}

type Language struct {
	Code string `json:"code"` // 语言代码
	Name string `json:"name"` // 语言名称
}

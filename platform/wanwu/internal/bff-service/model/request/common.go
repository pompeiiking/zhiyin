package request

type CommonCheck struct {
}

type PageSearch struct {
	PageSize int `json:"pageSize" form:"pageSize" validate:"required"`
	PageNo   int `json:"pageNo" form:"pageNo"`
}

func (c *CommonCheck) Check() error {
	return nil
}

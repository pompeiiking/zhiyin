package response

type OrgID struct {
	OrgID string `json:"orgId"`
}

type OrgInfo struct {
	OrgID     string `json:"orgId"`
	Name      string `json:"name"`
	Remark    string `json:"remark"`
	CreatedAt string `json:"createdAt"`
	Creator   IDName `json:"creator"`
	Status    bool   `json:"status"`
}

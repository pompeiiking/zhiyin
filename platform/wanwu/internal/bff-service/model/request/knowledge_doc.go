package request

type DocListReq struct {
	KnowledgeId string `json:"knowledgeId" form:"knowledgeId" validate:"required"`
	DocName     string `json:"docName" form:"docName"`
	Status      int    `json:"status" form:"status"` // 当前状态  -1-全部， 0-待处理， 1- 处理完成， 2-正在审核中，3-正在解析中，4-审核未通过，5-解析失败
	PageSearch
	CommonCheck
}

type DocImportReq struct {
	KnowledgeId   string      `json:"knowledgeId" validate:"required"` //知识库id
	DocImportType int         `json:"docImportType"`                   //文档导入类型，0：文件上传，1：url上传，2.批量url上传
	DocInfo       []*DocInfo  `json:"docInfoList" validate:"required"` //上传文档列表
	DocSegment    *DocSegment `json:"docSegment" validate:"required"`  //文档分段配置
	DocAnalyzer   []string    `json:"docAnalyzer" validate:"required"` //文档解析类型
	CommonCheck
}

type DocInfo struct {
	DocId   string `json:"docId"`   //文档id
	DocName string `json:"docName"` //文档名称
	DocUrl  string `json:"docUrl"`  //文档url
	DocType string `json:"docType"` // 文档类型
	DocSize int64  `json:"docSize"` // 文档类型
}

type DocSegment struct {
	SegmentType string   `json:"segmentType" validate:"required"` //分段方式 0：自动分段；1：自定义分段
	Splitter    []string `json:"splitter"`                        // 分隔符（只有自定义分段必填）
	MaxSplitter int      `json:"maxSplitter"`                     // 可分隔最大值（只有自定义分段必填）
	Overlap     float32  `json:"overlap"`                         // 可重叠值（只有自定义分段必填）
}

type QueryKnowledgeReq struct {
	KnowledgeId string `json:"knowledgeId" form:"knowledgeId" validate:"required"`
	CommonCheck
}

type DeleteDocReq struct {
	DocIdList []string `json:"docIdList"  validate:"required"`
	CommonCheck
}

type DocSegmentListReq struct {
	DocId string `json:"docId" form:"docId" validate:"required"`
	PageSearch
	CommonCheck
}

type UpdateDocSegmentStatusReq struct {
	DocId         string `json:"docId" validate:"required"`
	ContentId     string `json:"contentId"`
	ContentStatus string `json:"contentStatus" validate:"required"`
	ALL           bool   `json:"all" ` // all 代表全部启用，此时将忽略contentId
	CommonCheck
}

type AnalysisUrlDocReq struct {
	KnowledgeId string   `json:"knowledgeId"   validate:"required"`
	UrlList     []string `json:"urlList"   validate:"required"`
	CommonCheck
}

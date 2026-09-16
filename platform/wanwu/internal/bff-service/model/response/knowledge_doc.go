package response

type ListDocResp struct {
	DocId       string `json:"docId"`
	DocName     string `json:"docName"`     //文档名称
	DocType     string `json:"docType"`     //文档类型
	KnowledgeId string `json:"knowledgeId"` //知识库id
	UploadTime  string `json:"uploadTime"`  //上传时间
	Status      int    `json:"status"`      //处理状态
	ErrorMsg    string `json:"errorMsg"`    //解析错误信息，预留
	FileSize    string `json:"fileSize"`    //文件大小，预留
}

type DocImportTipResp struct {
	Message       string `json:"msg"`
	UploadStatus  int32  `json:"uploadstatus"`  //上传状态
	KnowledgeId   string `json:"knowledgeId"`   //知识库id
	KnowledgeName string `json:"knowledgeName"` //知识库名称
}

type DocSegmentResp struct {
	FileName           string            `json:"fileName"`        //名称
	PageTotal          int               `json:"pageTotal"`       //总页数
	SegmentTotalNum    int               `json:"segmentTotalNum"` //分段数量
	MaxSegmentSize     int               `json:"maxSegmentSize"`  //设置最大长度
	SegmentType        string            `json:"segmentType"`     //分段方式 0自动分段 1自定义分段
	UploadTime         string            `json:"uploadTime"`      //上传时间
	Splitter           string            `json:"splitter"`        // 分隔符（只有自定义分段必填）
	SegmentContentList []*SegmentContent `json:"contentList"`     //内容
}

type SegmentContent struct {
	Content    string `json:"content"`
	Len        int    `json:"len"`
	Available  bool   `json:"available"`
	ContentId  string `json:"contentId"`
	ContentNum int    `json:"contentNum"`
}

type AnalysisDocUrlResp struct {
	UrlList []*Url `json:"urlList"`
}

type Url struct {
	Url      string `json:"url"`
	FileName string `json:"fileName"`
	FileSize int    `json:"fileSize"`
}

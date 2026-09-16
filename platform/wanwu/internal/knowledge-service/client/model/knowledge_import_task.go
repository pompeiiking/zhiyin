package model

const (
	KnowledgeImportAnalyze = 1 //知识库任务解析中
	KnowledgeImportSubmit  = 2 //知识库任务已提交
	KnowledgeImportFinish  = 3 //知识库任务导入完成
	KnowledgeImportError   = 4 //知识库任务导入失败
	FileImportType         = 0 //文件上传
	UrlImportType          = 1 //url上传
	UrlFileImportType      = 2 //2.批量url上传
)

type SegmentConfig struct {
	SegmentType string   `json:"segmentType" validate:"required"` //分段方式 0：自定分段；1：自定义分段
	Splitter    []string `json:"splitter"`                        // 分隔符（只有自定义分段必填）
	MaxSplitter int      `json:"maxSplitter"`                     // 可分隔最大值（只有自定义分段必填）
	Overlap     float32  `json:"overlap"`                         // 可重叠值（只有自定义分段必填）
}

type DocAnalyzer struct {
	AnalyzerList []string `json:"analyzerList"` //文档解析方式，ocr等
}

type DocImportInfo struct {
	DocInfoList []*DocInfo `json:"docInfoList"`
}

type DocInfo struct {
	DocId   string `json:"docId"`   //文档id
	DocName string `json:"docName"` //文档名称
	DocUrl  string `json:"docUrl"`  //文档url
	DocType string `json:"docType"` // 文档类型
	DocSize int64  `json:"docSie"`  // 文档大小
}

type KnowledgeImportTask struct {
	Id            uint32 `gorm:"column:id;primary_key;type:bigint(20) auto_increment;not null;comment:'id';" json:"id"`
	ImportId      string `gorm:"uniqueIndex:idx_unique_import_id;column:import_id;type:varchar(64)" json:"importId"` // Business Primary Key
	KnowledgeId   string `gorm:"column:knowledge_id;type:varchar(64);not null;index:idx_knowledge_id" json:"knowledgeId"`
	ImportType    int    `gorm:"column:import_type;type:tinyint(1);not null;" json:"importType"`
	Status        int    `gorm:"column:status;type:tinyint(1);not null;comment:'0-任务待处理；1-任务解析中 ；2-任务提交算法完成；3-任务完成；4-任务失败" json:"status"`
	ErrorMsg      string `gorm:"column:error_msg;type:longtext;not null;comment:'解析的错误信息'" json:"errorMsg"`
	DocInfo       string `gorm:"column:doc_info;type:longtext;not null;comment:'文件信息'" json:"docInfo"`
	SegmentConfig string `gorm:"column:segment_config;type:text;not null;comment:'分段配置信息'" json:"segmentConfig"`
	DocAnalyzer   string `gorm:"column:doc_analyzer;type:text;not null;comment:'文档解析配置'" json:"docAnalyzer"`
	CreatedAt     int64  `gorm:"column:create_at;type:bigint(20);not null;" json:"createAt"` // Create Time
	UpdatedAt     int64  `gorm:"column:update_at;type:bigint(20);not null;" json:"updateAt"` // Update Time
	UserId        string `gorm:"column:user_id;type:varchar(64);not null;default:'';" json:"userId"`
	OrgId         string `gorm:"column:org_id;type:varchar(64);not null;default:''" json:"orgId"`
}

func (KnowledgeImportTask) TableName() string {
	return "knowledge_import_task"
}

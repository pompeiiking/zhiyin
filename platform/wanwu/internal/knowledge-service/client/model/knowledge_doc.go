package model

const (
	DocWaitingForUpload = -2 //文档待上传
	DocInit             = 0  //文档待处理
	DocProcessing       = 3  //文档处理中
	DocFail             = 5  //文档待处理
)

type KnowledgeDoc struct {
	Id           uint32 `json:"id" gorm:"primary_key;type:bigint(20) auto_increment;not null;comment:'id';"` // Primary Key
	DocId        string `gorm:"uniqueIndex:idx_unique_doc_id;column:doc_id;type:varchar(64)" json:"docId"`   // Business Primary Key
	ImportTaskId string `gorm:"column:batch_id;type:varchar(64);not null;default:'';comment:'导入的任务id'" json:"importTaskId"`
	KnowledgeId  string `gorm:"column:knowledge_id;index:idx_user_id_knowledge_id_name,priority:2;type:varchar(64);not null;default:''" json:"knowledgeId"`
	FilePathMd5  string `gorm:"column:file_path_md5;type:varchar(64);not null;default:'';comment:'文件的md5值'" json:"filePathMd5"`
	FilePath     string `gorm:"column:file_path;type:text;not null" json:"filePath"`
	Name         string `gorm:"column:name;index:idx_user_id_knowledge_id_name,priority:3;type:varchar(256);not null;default:''" json:"name"`
	FileType     string `gorm:"column:file_type;type:varchar(20);not null;default:''" json:"fileType"`
	FileSize     int64  `gorm:"column:file_size;type:bigint(20);COMMENT:'文件大小，单位byte'" json:"fileSize"`
	Status       int    `gorm:"column:status;type:tinyint(1);not null;comment:'0-待处理， 1- 处理完成， 2-正在审核中(目前没有)，3-正在解析中，4-审核未通过（目前没有），5-解析失败';" json:"status"`
	ErrorMsg     string `gorm:"column:error_msg;type:longtext;not null;comment:'解析的错误信息'" json:"errorMsg"`
	CreatedAt    int64  `gorm:"column:create_at;type:bigint(20);not null;" json:"createAt"` // Create Time
	UpdatedAt    int64  `gorm:"column:update_at;type:bigint(20);not null;" json:"updateAt"` // Update Time
	UserId       string `gorm:"column:user_id;index:idx_user_id_knowledge_id_name,priority:1;type:varchar(64);not null;default:'';" json:"userId"`
	OrgId        string `gorm:"column:org_id;type:varchar(64);not null;default:''" json:"orgId"`
	Deleted      int    `gorm:"column:deleted;type:tinyint(1);not null;default:0;comment:'是否逻辑删除';" json:"deleted"`
}

func (KnowledgeDoc) TableName() string {
	return "knowledge_doc"
}

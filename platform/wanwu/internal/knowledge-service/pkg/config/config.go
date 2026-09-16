package config

import (
	"strings"

	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg"
	"github.com/UnicomAI/wanwu/pkg/db"
	"github.com/UnicomAI/wanwu/pkg/log"
	"github.com/spf13/viper"
)

var config = Config{}

func init() {
	pkg.AddContainer(config)
}

func GetConfig() *Config {
	return &config
}

func (c Config) LoadType() string {
	return "configs"
}

func (c Config) Load() error {
	viper.SetConfigFile("configs/microservice/knowledge-service/configs/config.yaml")
	viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_", "-", "_"))
	viper.AutomaticEnv()
	viper.AllowEmptyEnv(true)
	if err := viper.ReadInConfig(); err != nil {
		return err
	}
	var cfg Config
	if err := viper.Unmarshal(&cfg); err != nil {
		return err
	}
	config = cfg
	return nil
}

func (c Config) StopPriority() int {
	return pkg.DefaultPriority
}

func (c Config) Stop() error {
	return nil
}

// 系统配置，对应yml
// viper内置了mapstructure, yml文件用"-"区分单词, 转为驼峰方便

// 需要详细自定义配置项目
// 主要集中在系统配置、log配置、mysql、请求权限控制、请求速率限制
// 全局配置变量

type Config struct {
	Server             *Server             `mapstructure:"server" json:"server"`
	Log                LogConfig           `json:"log" mapstructure:"log"`
	AccessLog          LogConfig           `mapstructure:"access-log" json:"access-log" yaml:"access-log"`
	RpcLog             LogConfig           `mapstructure:"rpc-log" json:"rpc-log" yaml:"rpc-log"`
	DB                 db.Config           `json:"db" mapstructure:"db"`
	Minio              *MinioConfig        `mapstructure:"minio" json:"minio"`
	Kafka              *KafkaConfig        `mapstructure:"kafka" json:"kafka"`
	UsageLimit         *UsageLimitConfig   `mapstructure:"usage-limit" json:"usageLimit"`
	RagServer          *RagServerConfig    `mapstructure:"rag-server" json:"ragServer"`
	KnowledgeDocConfig *KnowledgeDocConfig `json:"knowledge-doc-config" mapstructure:"knowledge-doc-config"`
}

type Server struct {
	GrpcEndpoint   string `mapstructure:"grpc-endpoint" json:"grpcEndpoint"`
	MaxRecvMsgSize int    `mapstructure:"max-recv-msg-size" json:"maxRecvMsgSize"`
}

type LogConfig struct {
	Std   bool         `json:"std" mapstructure:"std"`
	Level string       `json:"level" mapstructure:"level"`
	Logs  []log.Config `json:"logs" mapstructure:"logs"`
}

type MinioConfig struct {
	EndPoint        string `json:"endpoint" mapstructure:"endpoint"`
	KnowledgeDir    string `mapstructure:"knowledge-dir" json:"knowledge-dir"`
	User            string `mapstructure:"user" json:"user"`
	Password        string `mapstructure:"password" json:"password"`
	Bucket          string `mapstructure:"bucket" json:"bucket"`
	PublicRagBucket string `mapstructure:"public-rag-bucket" json:"public-rag-bucket"`
}

type KafkaConfig struct {
	Addr                string `mapstructure:"addr" json:"addr"`
	User                string `mapstructure:"user" json:"user"`
	Password            string `mapstructure:"password" json:"password"`
	UrlAnalysisTopic    string `mapstructure:"url-analysis-topic" json:"url-analysis-topic"`
	UrlImportTopic      string `mapstructure:"url-import-topic" json:"url-import-topic"`
	Topic               string `mapstructure:"topic" json:"topic"`
	DefaultPartitionNum int32  `mapstructure:"default-partition-num" json:"defaultPartitionNum"`
}

type UsageLimitConfig struct {
	DocTotal                     int64  `mapstructure:"doc-total" json:"docTotal"`
	FileTypes                    string `mapstructure:"file-types" json:"fileTypes"`
	MaxFileSize                  int64  `mapstructure:"max-file-size" json:"maxFileSize"` //单位：字节
	CompressedFileType           string `mapstructure:"compressed-file-type" json:"compressedFileType"`
	MaxNumberOfFilesInCompressed int64  `mapstructure:"max-number-of-files-in-compressed" json:"maxNumberOfFilesInCompressed"`
	FileSizeLimit                int64  `mapstructure:"file-size-limit" json:"fileSizeLimit"`
	TxtSizeLimit                 int64  `mapstructure:"txt-size-limit" json:"txtSizeLimit"`
	DocxSizeLimit                int64  `mapstructure:"docx-size-limit" json:"docxSizeLimit"`
	PdfSizeLimit                 int64  `mapstructure:"pdf-size-limit" json:"pdfSizeLimit"`
	ExcelSizeLimit               int64  `mapstructure:"excel-size-limit" json:"excelSizeLimit"`
	CsvSizeLimit                 int64  `mapstructure:"csv-size-limit" json:"csvSizeLimit"`
	PptxSizeLimit                int64  `mapstructure:"pptx-size-limit" json:"pptxSizeLimit"`
	HtmlSizeLimit                int64  `mapstructure:"html-size-limit" json:"htmlSizeLimit"`
	CompressedSizeLimit          int64  `mapstructure:"compressed-size-limit" json:"compressedSizeLimit"`
	UploadConcurrentLimit        int64  `mapstructure:"upload-concurrent-limit" json:"uploadConcurrentLimit"`
}

type KnowledgeDocConfig struct {
	DocLocalFilePath string `mapstructure:"doc-local-file-path" json:"doc-local-file-path"`
}

type RagServerConfig struct {
	Endpoint                  string `mapstructure:"endpoint" json:"endpoint"`
	UrlImportEndpoint         string `mapstructure:"url-import-endpoint" json:"url-import-endpoint"`
	UrlAnalysisEndpoint       string `mapstructure:"url-analysis-endpoint" json:"url-analysis-endpoint"`
	InitKnowledgeUri          string `mapstructure:"init-knowledge-uri" json:"init-knowledge-uri"`
	UpdateKnowledgeUri        string `mapstructure:"update-knowledge-uri" json:"update-knowledge-uri"`
	DeleteKnowledgeUri        string `mapstructure:"delete-knowledge-uri" json:"delete-knowledge-uri"`
	GetDocSegmentUri          string `mapstructure:"get-doc-segment-uri" json:"get-doc-segment-uri"`
	DocSegmentUpdateStatusUri string `mapstructure:"doc-segment-update-status-uri" json:"doc-segment-update-status-uri"`
	DocDeleteUri              string `mapstructure:"doc-delete-uri" json:"doc-delete-uri"`
	DocUrlImportUri           string `mapstructure:"doc-url-import-uri" json:"doc-url-import-uri"`
	DocUrlAnalysisUri         string `mapstructure:"doc-url-analysis-uri" json:"doc-url-analysis-uri"`
	Timeout                   int64  `mapstructure:"timeout" json:"timeout"`
}

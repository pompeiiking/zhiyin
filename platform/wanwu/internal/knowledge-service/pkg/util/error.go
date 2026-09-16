package util

import (
	err_code "github.com/UnicomAI/wanwu/api/proto/err-code"
	grpc_util "github.com/UnicomAI/wanwu/pkg/grpc-util"
)

const (
	KnowledgeImportFileFormatErr    = "know_doc_unsupported_file_format"
	KnowledgeImportFileSizeErr      = "know_doc_file_size_exceed"
	KnowledgeImportSameNameErr      = "know_same_name_validation_fail"
	KnowledgeDocLastFailureErr      = "know_doc_last_failure_info"
	KnowledgeDocParsingServiceErr   = "know_doc_parsing_service_error"
	KnowledgeDocEmptyFileContentErr = "know_doc_empty_file_content"
	KnowledgeDocFileUnUsableErr     = "know_doc_file_unusable"
)

func ErrCode(code err_code.Code) error {
	return grpc_util.ErrorStatusWithKey(code, "")
}

func ErrStatus(code err_code.Code, status *err_code.Status) error {
	return grpc_util.ErrorStatusWithKey(code, status.TextKey, status.Args...)
}

func ToErrStatus(key string, args ...string) *err_code.Status {
	return &err_code.Status{
		TextKey: key,
		Args:    args,
	}
}

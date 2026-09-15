package grpc_util

import (
	err_code "github.com/UnicomAI/wanwu/api/proto/err-code"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func ErrorStatus(code err_code.Code, args ...string) error {
	return ErrorStatusWithKey(code, "", args...)
}

func ErrorStatusWithKey(code err_code.Code, textKey string, args ...string) error {
	return ErrorStatusWithMsgAndKey(code, "", textKey, args...)
}

func ErrorStatusWithMsgAndKey(code err_code.Code, msg, textKey string, args ...string) error {
	st := status.New(codes.Code(code), msg)
	detail, err := st.WithDetails(&err_code.Status{
		TextKey: textKey,
		Args:    args,
	})
	if err != nil {
		return st.Err()
	}
	return detail.Err()
}

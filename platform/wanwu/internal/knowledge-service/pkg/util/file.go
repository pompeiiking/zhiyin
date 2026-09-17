package util

import (
	"errors"
	uuid "github.com/satori/go.uuid"
	"io"
	"strings"
)

func FileEOF(err error) bool {
	return errors.Is(err, io.EOF) || (err != nil && err.Error() == "EOF")
}

func BuildFilePath(fileDir, fileExt string) string {
	return fileDir + uuid.NewV4().String() + fileExt
}

func ReplaceLast(s, old, new string) string {
	i := strings.LastIndex(s, old)
	if i == -1 {
		return s
	}
	return s[:i] + new + s[i+len(old):]
}

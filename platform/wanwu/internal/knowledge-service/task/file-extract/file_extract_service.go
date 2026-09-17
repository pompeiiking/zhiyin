package file_extract

import (
	"context"
)

type FileExtractService interface {
	ExtractFileType() string
	ExtractFile(ctx context.Context, localFilePath string, destDir string) (extractDir string, err error)
}

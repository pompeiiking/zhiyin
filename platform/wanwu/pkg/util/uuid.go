package util

import (
	"fmt"
	"strings"

	"github.com/google/uuid"
)

func GenUUID() string {
	return uuid.New().String()
}

func GenApiUUID() string {
	return fmt.Sprintf("ww-%s", strings.Replace(uuid.New().String(), "-", "", -1))
}

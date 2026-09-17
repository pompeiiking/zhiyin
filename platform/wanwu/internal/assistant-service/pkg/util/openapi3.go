package util

import (
	"context"

	"github.com/UnicomAI/wanwu/pkg/log"
	"github.com/getkin/kin-openapi/openapi3"
)

// 验证openapi schema
func ValidateOpenAPISchema(schema string) (*openapi3.T, error) {
	ctx := context.Background()
	loader := &openapi3.Loader{Context: ctx, IsExternalRefsAllowed: true}

	doc, err := loader.LoadFromData([]byte(schema))
	if err != nil {
		log.Errorf(err.Error(), schema)
		return nil, err
	}
	return doc, nil
}

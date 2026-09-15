package minio

import (
	"context"
	"fmt"
)

var (
	BucketCustom = "custom-upload"
	// BucketAAA = "aaa-upload"
	// BucketBBB = "bbb-upload"
)

var (
	_minioCustom *client
	// _minioAAA *client
	// _minioBBB *client
)

func InitCustom(ctx context.Context, cfg Config) error {
	if _minioCustom != nil {
		return fmt.Errorf("minio custom client already init")
	}
	c, err := newClient(cfg)
	if err != nil {
		return err
	}
	_minioCustom = c
	if err = _minioCustom.CreateBucketIfNotExist(ctx, BucketCustom); err != nil {
		return err
	}
	return err
}

func Custom() *client {
	return _minioCustom
}

package minio

import (
	"context"
)

var (
	_minioKnowledge *client
)

func InitKnowledge(ctx context.Context, cfg Config, initBucketName string, public bool) error {
	if _minioKnowledge == nil {
		c, err := newClient(cfg)
		if err != nil {
			return err
		}
		_minioKnowledge = c
	}

	if err := _minioKnowledge.CreateBucketIfNotExist(ctx, initBucketName); err != nil {
		return err
	}
	if public {
		if err := _minioKnowledge.SetBucketPublic(ctx, initBucketName); err != nil {
			return err
		}
	}
	return nil
}

func Knowledge() *client {
	return _minioKnowledge
}

package redis

import (
	"context"
	"fmt"
)

const (
	_dbIAM = 4
)

var (
	_redisIAM *client
)

func InitIAM(ctx context.Context, cfg Config) error {
	if _redisIAM != nil {
		return fmt.Errorf("redis iam client already init")
	}
	c, err := newClient(ctx, cfg, _dbIAM)
	if err != nil {
		return err
	}
	_redisIAM = c
	return nil
}

func StopIAM() {
	if _redisIAM != nil {
		_redisIAM.Stop()
		_redisIAM = nil
	}
}

func IAM() *client {
	return _redisIAM
}

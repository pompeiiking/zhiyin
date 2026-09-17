package redis

import (
	"context"
	"fmt"
)

const (
	_dbSys = 0
)

var (
	_redisSys *client
)

func InitSys(ctx context.Context, cfg Config) error {
	if _redisSys != nil {
		return fmt.Errorf("redis sys client already init")
	}
	c, err := newClient(ctx, cfg, _dbSys)
	if err != nil {
		return err
	}
	_redisSys = c
	return nil
}

func StopSys() {
	if _redisSys != nil {
		_redisSys.Stop()
		_redisSys = nil
	}
}

func Sys() *client {
	return _redisSys
}

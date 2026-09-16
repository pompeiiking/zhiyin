package minio

import (
	"bytes"
	"context"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"github.com/minio/minio-go/v7/pkg/lifecycle"
	"io"
)

type Config struct {
	Endpoint string `json:"endpoint" mapstructure:"endpoint"`
	User     string `json:"user" mapstructure:"user"`
	Password string `json:"password" mapstructure:"password"`
}

type client struct {
	cli    *minio.Client
	config Config
}

func newClient(cfg Config) (*client, error) {
	cli, err := minio.New(cfg.Endpoint, &minio.Options{
		Creds: credentials.NewStaticV4(cfg.User, cfg.Password, ""),
	})
	if err != nil {
		return nil, err
	}
	return &client{
		cli:    cli,
		config: cfg,
	}, nil
}

func (c *client) Cli() *minio.Client {
	return c.cli
}

func (c *client) PutObject(ctx context.Context, bucket, name string, data []byte) (minio.UploadInfo, error) {
	return c.cli.PutObject(ctx, bucket, name, bytes.NewReader(data), int64(len(data)), minio.PutObjectOptions{})
}

func (c *client) GetObject(ctx context.Context, bucketName, objectName string) ([]byte, error) {
	obj, err := c.cli.GetObject(ctx, bucketName, objectName, minio.GetObjectOptions{})
	if err != nil {
		return nil, err
	}
	return io.ReadAll(obj)
}

func (c *client) DeleteObject(ctx context.Context, bucketName, objectName string) error {
	return c.cli.RemoveObject(ctx, bucketName, objectName, minio.RemoveObjectOptions{
		ForceDelete: false,
	})
}

func (c *client) ListObjects(ctx context.Context, bucketName, prefix string) <-chan minio.ObjectInfo {
	return c.cli.ListObjects(ctx, bucketName, minio.ListObjectsOptions{
		Prefix:    prefix,
		Recursive: true,
	})
}

func (c *client) CreateBucketIfNotExist(ctx context.Context, bucketName string) error {
	exist, err := c.cli.BucketExists(ctx, bucketName)
	if err != nil {
		return err
	}
	if exist {
		return nil
	}
	return c.cli.MakeBucket(ctx, bucketName, minio.MakeBucketOptions{})
}

func (c *client) SetPathExpireByDay(ctx context.Context, bucketName string, path string, days int) error {
	expiration := lifecycle.Expiration{Days: lifecycle.ExpirationDays(days)}
	filter := lifecycle.Filter{Prefix: path}
	rules := []lifecycle.Rule{
		{
			ID:         "delete-after-days",
			Status:     "Enabled",
			RuleFilter: filter,
			Expiration: expiration,
		},
	}
	err := c.cli.SetBucketLifecycle(ctx, bucketName, &lifecycle.Configuration{
		Rules: rules,
	})
	return err
}

func (c *client) SetBucketPublic(ctx context.Context, bucketName string) error {
	policy := `{
		"Version": "2012-10-17",
		"Statement": [
			{
				"Effect": "Allow",
				"Principal": {"AWS": ["*"]},
				"Action": ["s3:GetObject"],
				"Resource": ["arn:aws:s3:::` + bucketName + `/*"]
			}
		]
	}`
	return c.cli.SetBucketPolicy(ctx, bucketName, policy)
}

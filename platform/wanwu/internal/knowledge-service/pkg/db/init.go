package db

import (
	"context"
	"fmt"

	"github.com/UnicomAI/wanwu/internal/knowledge-service/client/model"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg"
	"github.com/UnicomAI/wanwu/internal/knowledge-service/pkg/config"
	"github.com/UnicomAI/wanwu/pkg/db"
	"github.com/UnicomAI/wanwu/pkg/log"
	"gorm.io/gorm"
)

const (
	knowledgeDBName = "knowledge_base_service"
)

var dbClient = DataBaseClient{}

type DataBaseClient struct {
	DB *gorm.DB
}

func init() {
	pkg.AddContainer(dbClient)
}

func GetClient() DataBaseClient {
	return dbClient
}

func GetHandle(ctx context.Context) *gorm.DB {
	return GetClient().DB.WithContext(ctx)
}

func (c DataBaseClient) LoadType() string {
	return "dbClient"
}

func (c DataBaseClient) Load() error {
	dbHandle, err := db.New(config.GetConfig().DB)
	if err != nil {
		log.Errorf("init knowledge_base_service db err: %v", err)
		return err
	}
	//创建数据库配置
	err = createDB(dbHandle)
	if err != nil {
		return err
	}
	//注册表配置
	err = registerTables(dbHandle)
	if err != nil {
		return err
	}
	dbClient.DB = dbHandle
	return nil
}

func (c DataBaseClient) StopPriority() int {
	return pkg.DBPriority
}

func (c DataBaseClient) Stop() error {
	if dbClient.DB == nil {
		return nil
	}
	dbHandle, err := dbClient.DB.DB()
	if err != nil {
		return err
	}
	err = dbHandle.Close()
	return err
}

// 创建db
func createDB(dbClient *gorm.DB) error {
	err := dbClient.Exec(fmt.Sprintf("CREATE DATABASE IF NOT EXISTS %s DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;", knowledgeDBName)).Error
	if err != nil {
		log.Errorf("MySQL创建数据库%s异常: %v", knowledgeDBName, err)
		return err
	}
	log.Infof("MySQL创建数据库成功: %s", knowledgeDBName)
	return nil
}

// 注册表信息
func registerTables(dbClient *gorm.DB) error {
	err := dbClient.AutoMigrate(
		model.KnowledgeDoc{},
		model.KnowledgeBase{},
		model.KnowledgeImportTask{},
	)
	if err != nil {
		fmt.Printf("register knowledge tables failed: %v", err)
		return err
	}
	fmt.Printf("register knowledge tables table success")
	return nil
}

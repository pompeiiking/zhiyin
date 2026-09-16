package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"runtime"
	"syscall"

	"github.com/UnicomAI/wanwu/internal/bff-service/config"
	"github.com/UnicomAI/wanwu/internal/bff-service/pkg/i18n"
	"github.com/UnicomAI/wanwu/internal/bff-service/server/http/handler"
	http_client "github.com/UnicomAI/wanwu/pkg/http-client"
	"github.com/UnicomAI/wanwu/pkg/log"
	"github.com/UnicomAI/wanwu/pkg/minio"
	mp "github.com/UnicomAI/wanwu/pkg/model-provider"
	"github.com/UnicomAI/wanwu/pkg/util"
)

var (
	configFile string
	isVersion  bool

	buildTime    string //编译时间
	buildVersion string //编译版本
	gitCommitID  string //git的commit id
	gitBranch    string //git branch
	builder      string //构建者
)

func main() {
	flag.StringVar(&configFile, "config", "configs/microservice/bff-service/configs/config.yaml", "conf yaml file")
	flag.BoolVar(&isVersion, "v", false, "build message")
	flag.Parse()

	if isVersion {
		versionPrint()
		return
	}

	ctx := context.Background()

	// config
	flag.Parse()
	if err := config.LoadConfig(configFile); err != nil {
		log.Fatalf("init cfg err: %v", err)
	}

	// init log
	if err := log.InitLog(config.Cfg().Log.Std, config.Cfg().Log.Level, config.Cfg().Log.Logs...); err != nil {
		log.Fatalf("init log err: %v", err)
	}

	// init time local
	if err := util.InitTimeLocal(); err != nil {
		log.Fatalf("init time local UTC8 err: %v", err)
	}

	// init i18n
	if err := i18n.Init(config.Cfg().I18n); err != nil {
		log.Fatalf("init i18n err: %v", err)
	}

	// init minio: custom
	if err := minio.InitCustom(ctx, config.Cfg().Minio); err != nil {
		log.Fatalf("init minio err: %v", err)
	}

	// init minio: fileupload
	if err := minio.InitFileUpload(ctx, config.Cfg().Minio); err != nil {
		log.Fatalf("init minio err: %v", err)
	}

	// init workflow http client
	if err := http_client.InitWorkflow(); err != nil {
		log.Fatalf("init http client err: %v", err)
	}

	// init proxy minio http client
	if err := http_client.InitProxyMinio(); err != nil {
		log.Fatalf("init http client err: %v", err)
	}

	// init model provider
	mp.Init(config.Cfg().Server.CallbackUrl)

	// start http handler
	handler.Start(ctx)

	// shutdown
	sc := make(chan os.Signal, 1)
	signal.Notify(sc, syscall.SIGINT, syscall.SIGTERM)
	<-sc

	// stop http handler
	handler.Stop(ctx)
}

func versionPrint() {
	fmt.Printf("build_time: %s\n", buildTime)
	fmt.Printf("build_version: %s\n", buildVersion)
	fmt.Printf("git_commit_id: %s\n", gitCommitID)
	fmt.Printf("git branch: %s\n", gitBranch)
	fmt.Printf("runtime version: %s\n", runtime.Version())
	fmt.Printf("builder: %s\n", builder)
}

package handler

import (
	"context"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"

	"github.com/UnicomAI/wanwu/internal/bff-service/config"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	"github.com/UnicomAI/wanwu/internal/bff-service/server/http/handler/router/callback"
	"github.com/UnicomAI/wanwu/internal/bff-service/server/http/handler/router/openapi"
	v1 "github.com/UnicomAI/wanwu/internal/bff-service/server/http/handler/router/v1"
	"github.com/UnicomAI/wanwu/internal/bff-service/server/http/middleware"
	"github.com/UnicomAI/wanwu/internal/bff-service/service"
	"github.com/UnicomAI/wanwu/pkg/log"
)

var (
	httpServ *http.Server
)

func Start(ctx context.Context) {

	// middleware
	middleware.Init()

	// validator
	if err := gin_util.InitValidator(); err != nil {
		log.Fatalf("init gin validator err: %v", err)
	}

	// router
	gin.ForceConsoleColor()
	r := gin.Default()
	// v1
	v1.Register(r.Group("/v1"))
	// v2
	// v3
	// ..
	// openapi v1
	openapi.Register(r.Group("/openapi/v1"))
	// callback v1
	callback.Register(r.Group("/callback/v1"))

	// service
	if err := service.Init(); err != nil {
		log.Fatalf("init service err: %v", err)
	}

	// start http server
	httpServ = &http.Server{
		Addr:    ":" + strconv.Itoa(config.Cfg().Server.Port),
		Handler: r,
	}
	go func() {
		if err := httpServ.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server fatal: %v", err)
		}
	}()
	log.Infof("server listen on: %v", config.Cfg().Server.Port)

}

func Stop(ctx context.Context) {
	log.Infof("closing http server...")
	// stop http server
	cancelCtx, cancel := context.WithTimeout(ctx, time.Minute)
	defer cancel()
	if err := httpServ.Shutdown(cancelCtx); err != nil {
		log.Fatalf("server forced to shutdown: %v", err)
	} else {
		log.Infof("close http server gracefully")
	}
}

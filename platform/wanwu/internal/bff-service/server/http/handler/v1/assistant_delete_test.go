package v1

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/UnicomAI/wanwu/internal/bff-service/config"
	gin_util "github.com/UnicomAI/wanwu/internal/bff-service/pkg/gin-util"
	"github.com/UnicomAI/wanwu/pkg/constant"
	"github.com/gin-gonic/gin"
)

func TestDeleteAssistant(t *testing.T) {
	if err := gin_util.InitValidator(); err != nil {
		t.Fatalf("initialize request validator: %v", err)
	}
	gin.SetMode(gin.TestMode)

	t.Run("deletes the requested assistant as an agent", func(t *testing.T) {
		recorder := httptest.NewRecorder()
		ctx, _ := gin.CreateTestContext(recorder)
		ctx.Request = httptest.NewRequest(http.MethodDelete, "/assistant", strings.NewReader(`{"assistantId":"99"}`))
		ctx.Request.Header.Set("Content-Type", "application/json")
		ctx.Request.Header.Set(config.X_LANGUAGE, "zh")
		ctx.Request.Header.Set(config.X_ORG_ID, "org-1")
		ctx.Set(config.USER_ID, "user-1")

		var got []string
		deleteAssistant(ctx, func(_ *gin.Context, userID, orgID, assistantID, appType string) error {
			got = []string{userID, orgID, assistantID, appType}
			return nil
		})

		want := []string{"user-1", "org-1", "99", constant.AppTypeAgent}
		if len(got) != len(want) {
			t.Fatalf("delete call = %v, want %v", got, want)
		}
		for i := range want {
			if got[i] != want[i] {
				t.Fatalf("delete argument %d = %q, want %q", i, got[i], want[i])
			}
		}
	})

	t.Run("rejects an empty assistant id without deleting", func(t *testing.T) {
		recorder := httptest.NewRecorder()
		ctx, _ := gin.CreateTestContext(recorder)
		ctx.Request = httptest.NewRequest(http.MethodDelete, "/assistant", strings.NewReader(`{"assistantId":""}`))
		ctx.Request.Header.Set("Content-Type", "application/json")
		ctx.Request.Header.Set(config.X_LANGUAGE, "zh")

		called := false
		deleteAssistant(ctx, func(_ *gin.Context, _, _, _, _ string) error {
			called = true
			return nil
		})

		if called {
			t.Fatal("delete was called for an empty assistant id")
		}
		if recorder.Code != http.StatusBadRequest {
			t.Fatalf("status = %d, want %d", recorder.Code, http.StatusBadRequest)
		}
	})
}

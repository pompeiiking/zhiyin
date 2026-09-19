package middleware

import (
	"encoding/json"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestRequestBodyRedactsNestedSecrets(t *testing.T) {
	gin.SetMode(gin.TestMode)
	ctx, _ := gin.CreateTestContext(httptest.NewRecorder())
	ctx.Request = httptest.NewRequest(
		"POST",
		"/v1/model",
		strings.NewReader(`{"model":"embedding-model","password":"login-secret","config":{"apiKey":"provider-secret","endpointUrl":"https://example.com"}}`),
	)
	ctx.Request.Header.Set("Content-Type", "application/json")

	body, err := requestBody(ctx)
	if err != nil {
		t.Fatalf("requestBody() error = %v", err)
	}
	if strings.Contains(body, "login-secret") || strings.Contains(body, "provider-secret") {
		t.Fatalf("requestBody() leaked a secret: %s", body)
	}

	var logged map[string]interface{}
	if err := json.Unmarshal([]byte(body), &logged); err != nil {
		t.Fatalf("unmarshal logged body: %v", err)
	}
	if logged["password"] != "[REDACTED]" {
		t.Fatalf("password was not redacted: %#v", logged["password"])
	}
	config := logged["config"].(map[string]interface{})
	if config["apiKey"] != "[REDACTED]" {
		t.Fatalf("nested apiKey was not redacted: %#v", config["apiKey"])
	}
	if logged["model"] != "embedding-model" || config["endpointUrl"] != "https://example.com" {
		t.Fatalf("non-sensitive fields changed: %#v", logged)
	}
}

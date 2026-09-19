package service

import "testing"

func TestEmbeddingRequestForProviderUsesVendorModelName(t *testing.T) {
	original := map[string]interface{}{
		"model":      "pami-internal-model-id",
		"input":      []string{"文本一", "文本二"},
		"dimensions": 1024,
	}

	got := embeddingRequestForProvider(original, "doubao-embedding-text-240715")

	if got["model"] != "doubao-embedding-text-240715" {
		t.Fatalf("model = %v, want vendor model name", got["model"])
	}
	if got["dimensions"] != 1024 {
		t.Fatalf("dimensions = %v, want 1024", got["dimensions"])
	}
	if original["model"] != "pami-internal-model-id" {
		t.Fatalf("input request was mutated: model = %v", original["model"])
	}
}

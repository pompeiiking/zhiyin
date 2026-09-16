package http_client

var workflowHttpClient *HttpClient

func InitWorkflow() error {
	workflowHttpClient = CreateDefault()
	return nil
}

func Workflow() *HttpClient {
	return workflowHttpClient
}

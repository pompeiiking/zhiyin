package http_client

var proxyMinioHttpClient *HttpClient

func InitProxyMinio() error {
	proxyMinioHttpClient = CreateDefault()
	return nil
}

func ProxyMinio() *HttpClient {
	return proxyMinioHttpClient
}

import requests
import json

# Flask 服务的地址
url = "http://127.0.0.1:1990/net_search"

# 要测试的请求数据
payload = {
    "query": "OpenAI 最新进展",
    "model":"yuanjing-70b-chat",
    "model_url":"https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1"
}

headers = {
    "Content-Type": "application/json"
}

# 发送 POST 请求
response = requests.post(url, headers=headers, data=json.dumps(payload),stream=True)
response.encoding = 'utf-8'

# 逐行读取响应内容
for line in response.iter_lines(decode_unicode=True):
    if line:
        print(line)
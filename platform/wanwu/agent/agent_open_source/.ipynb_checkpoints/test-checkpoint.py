import requests
import json

url = "http://192.168.0.126:7258/agent"

#question = "京东下场发展外卖最近情况是什么"
#question = "联通股价最近咋样"
question = " 半监督学习种类较多，其中应用较广的是？"
#question = "联通股价咋样啊最近"
#question='北京故宫附近的川菜馆'
#question='什么是智能体agent'
#question='帮我写个冒泡排序代码'
#question = "北京天气怎么样"


access_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjAwYWM5NjJkLTMxNDItNGYxNy05YjAxLWJkMDQ2MjRhZmI1MCIsInVzZXJuYW1lIjoid2FuZ3l5NjAzIiwibmlja25hbWUiOiLnjovoibPpmLMiLCJ1c2VyVHlwZSI6MCwiYnVmZmVyVGltZSI6MTc0NjUzMTA0MywiZXhwIjoxNzQ5MTE1ODQzLCJqdGkiOiIzMGU1MjY4ZTY1ZjQ0ZTE3YmEwM2ZhYTViMzZhZWZjZSIsImlhdCI6MTc0NjUyMzcyMywiaXNzIjoiMDBhYzk2MmQtMzE0Mi00ZjE3LTliMDEtYmQwNDYyNGFmYjUwIiwibmJmIjoxNzQ2NTIzNzIzLCJzdWIiOiJrb25nIn0.Q472cDPizQom8rhv8QLEip5CYinMBgXvL-1HtchI5UQ'



headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {access_token}"
}

'''

headers = {
    "Content-Type": "application/json"
}
'''
plugin_list = [
    {
        "api_schema": {
            "info": {
                "description": "根据用户输入的地点和美食，做出推荐",
                "title": "test001 API",
                "version": "1.0.0"
            },
            "openapi": "3.0.0",
            "paths": {
                "/run_for_bigmodel/731a5fuu-0ab7-4431-b0d3-f6807fba5s999/test001": {
                    "post": {
                        "description": "根据用户输入的地点和美食，做出推荐, ",
                        "operationId": "action_test001",
                        "parameters": [
                            {
                                "in": "header",
                                "name": "content-type",
                                "required": True,
                                "schema": {
                                    "example": "application/json",
                                    "type": "string"
                                }
                            }
                        ],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "properties": {
                                            "food": {
                                                "description": "美食名词，例如烤鸭、咖啡馆等",
                                                "type": "string"
                                            },
                                            "location": {
                                                "description": "地点名词，例如北京、海淀区、和平街道等",
                                                "type": "string"
                                            }
                                        },
                                        "required": [
                                            "location",
                                            "food"
                                        ],
                                        "type": "object"
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object"
                                        }
                                    }
                                },
                                "description": "成功获取查询结果"
                            },
                            "default": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object"
                                        }
                                    }
                                },
                                "description": "请求失败时的错误信息"
                            }
                        },
                        "summary": "测试1, test001"
                    }
                }
            },
            "servers": [
                {
                    "url": "https://maas.ai-yuanjing.com/plugin/api"
                }
            ]
        }
    }
]


response = requests.post(
    url,

    json={"input": question,"plugin_list":plugin_list,"function_call":False,"stream":True,"model":'deepseek-v3',"model-url":'https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1',"use_code":False,"use_search":True,"use_know":True,"do_sample":False,"temperature":0.01,"repetition_penalty":1.1,"auto citation":False,"need_search_list":True,"bing_top_k":15,"bing_target_success":10,"bing time out":3.0,"upload_file_url":'',"kn_params":{'knowledgeBase':'123','threshold':0.7,'topk':3}},

    #json={"input": question,"plugin_list":[],"function_call":False,"stream":True,"model":'deepseek-v3',"model-url":'https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1',"use_code":False,"use_search":False,"do_sample":False,"temperature":0.01,"repetition_penalty":1.1,"auto citation":False,"need_search_list":True,"bing_top_k":15,"bing_target_success":10,"bing time out":3.0,"upload_file_url":''},
    stream=True,
    headers=headers
)





print("\n💬 答案开始：\n")

try:
    for line in response.iter_lines(decode_unicode=True):
        if line:
            print(line)
            '''
            
            if line.startswith('data: '):
                line = line.removeprefix('data: ').strip()  # 移除前缀 "data: "
                if line:
                    #data = json.loads(line)  # 解析成Python对象
                    print(line)
                    '''
except KeyboardInterrupt:
    print("\n⏹️ 用户中断")

print("\n\n✅ 测试完成")

import requests
import json

url = "http://172.17.0.1:7258/agent"

question = "京东下场发展外卖最近情况是什么"
question = "帮我搜索评分较高的西安凉皮店铺"
#question = " 半监督学习种类较多，其中应用较广的是？"
#question = "联通股价咋样啊最近"
#question='北京故宫附近的川菜馆'
#question='什么是智能体agent'
#question='帮我写个冒泡排序代码'
#question = "北京天气怎么样"
#question = '上传的这篇文章写的什么总结一下'


headers = {
    "Content-Type": "application/json",
    "X-uid":"123"
}




response = requests.post(
    url,

    json={"input": question,"plugin_list":[],"search_url":"https://api.bochaai.com/v1/web-search","search_rerank_id":'11',"search_key":"sk-e698027f1ad34c3a8a8d405f9c0f5ec4","upload_file_url":"","function_call":False,"stream":True,"model":'deepseek-v3',"model_url":'http://172.17.0.1:6668/callback/v1/model/1',"use_code":False,"use_search":True,"use_know":False,"do_sample":False,"temperature":0.01,"repetition_penalty":1.1,"auto citation":False,"need_search_list":True,"kn_params":{'knowledgeBase':'123','threshold':0.7,'topk':3,'rerank_id':'','model':'','model_url':''}},
    stream=True,
    headers=headers
)





print("\n💬 答案开始：\n")

try:
    for line in response.iter_lines(decode_unicode=True):
        if line:
            print(line)

except KeyboardInterrupt:
    print("\n⏹️ 用户中断")

print("\n\n✅ 测试完成")

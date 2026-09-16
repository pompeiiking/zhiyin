from flask import Flask, request, jsonify
from flask import Response, stream_with_context
import asyncio
from bing_plus import *
import configparser
import os
from openai import OpenAI
from datetime import datetime


from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

config = configparser.ConfigParser()
config.read('config.ini',encoding='utf-8')

BING_DAYS_LIMIT =  float(config["BING"]["BING_DAYS_LIMIT"])
BING_RESULT_LEN =  int(config["BING"]["BING_RESULT_LEN"])
BING_TOP_K =  int(config["BING"]["BING_TOP_K"])
BING_THRESHOLD =  float(config["BING"]["BING_THRESHOLD"])
BING_SENTENCE_SIZE =  int(config["BING"]["BING_SENTENCE_SIZE"])
BING_TIME_OUT =  float(config["BING"]["BING_TIME_OUT"])
TARGET_SUCCESS = int(config["BING"]["TARGET_SUCCESS"])
LLM_MODEL_NAME = config["MODELS"]["default_llm"]


app = Flask(__name__)


def get_access_token():
    
    APP_ID = '2eee328bec434b26bd730247e652cd32'  
    API_KEY = '9ddf3d1cf32d4611ae9c2c4fbeba8a92'
    SECRET_KEY = '6b2dc478ac37473783e10e99e32810d6'
    """
    使用 API Key，Secret Key 获取access_token，替换下列示例中的应用API Key、应用Secret Key
    """
    url = f"https://maas-api.ai-yuanjing.com/openapi/service/v1/oauth/{APP_ID}/token"

    payload = json.dumps("")
    headers = {
        "Content-Type": "application/json",
    }
    payload = json.dumps(
        {
            "grant_type": "client_credentials",
            "client_id": API_KEY,
            "client_secret": SECRET_KEY,
        }
    )

    response = requests.request(
        "POST", url, headers=headers, data=payload, verify=False
    )
    return response.json().get("data")["access_token"]



        
@app.route('/net_search', methods=['POST'])
def net_search_service():
    data = request.get_json()
    print("接收到请求数据：", data)

    query = data.get("query")
    model = data.get("model")
    model_url = data.get("model_url")
    bing_top_k = BING_TOP_K
    bing_time_out = BING_TIME_OUT
    auto_citation = False

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    days_limit = BING_DAYS_LIMIT
    bing_result_len = BING_RESULT_LEN
    model = LLM_MODEL_NAME
    bing_target_success = 10

    try:
        task = start_async_search(
            loop, query, bing_top_k, bing_time_out,
            bing_target_success, bing_result_len,
            model, days_limit, auto_citation
        )
        result = loop.run_until_complete(task)
        bing_prompt, bing_search_list = result
        print('输出是:',bing_search_list)
        #result_str = ' '.join([str(element) for element in bing_search_list])
        context = "".join(item["snippet"] for item in bing_search_list)
        print('上下文是:',context)
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        ACCESS_TOKEN = get_access_token()
        TOOL_PROMPT_TEMPLATE = '''你是一个实时联网的智能问答助手，目前位于中国，今天是{cur_date}。你的主要任务是参考下列从互联网搜索到的网页信息回答用户问题。

## 参考信息
```
{context}
```

## 用户问题
```
{question}
```



## 输出要求
```
- 答案中不要出现"根据您提供的信息"、"根据提供的信息"、"根据参考信息"等之类的话术。
- 回答必须紧扣用户问题，回答要完整详细，必要时给出分析过程。
- 结合用户问题情况，不能遗漏对于当前问题的关键信息，例如针对天气类问题，需要给出天气状态、温度等关键信息。
- 涉及计算的，请给出分析过程。
- 如果参考信息没有找到答案，直接基于自身知识回答，优先回答用户的问题，但是不要编造答案。
- 不要输出与用户问题无关的内容。
- 要注意区分开始日期、结束日期和当前日期，如果结束日期早于当前日期，说明已经结束了。
-  答案正文中不要解释为什么使用哪些参考信息。

```'''
        prompt = TOOL_PROMPT_TEMPLATE.format(question=query,context=context[:3000],cur_date=date_str)
        llm = ChatOpenAI(
            model=model,
            api_key=ACCESS_TOKEN,
            base_url=model_url,
            temperature=0.7,
            streaming=True
        )

        # 构造消息
        messages = [
            HumanMessage(content=prompt)
        ]

        @stream_with_context
        def generate():

            for chunk in llm.stream(messages):
                if chunk.content:
                    response = {'response':chunk.content,'search_list':[]}
                    print('输出是:',response)
                    # 每次发送一条 SSE 消息
                    yield f"{json.dumps(response,ensure_ascii=False)}\n"
                    
            response = {'response':'','search_list':bing_search_list}
            yield f"{json.dumps(response,ensure_ascii=False)}\n"


        return Response(generate(), content_type='text/event-stream;charset=utf-8')

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        loop.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1990)

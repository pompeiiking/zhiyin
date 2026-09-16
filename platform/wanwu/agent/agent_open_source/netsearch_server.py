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


# netsearch_server.py
import logging
import os

log_dir = "./logs"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler(f"{log_dir}/net_search.log", encoding='utf-8'),
        logging.StreamHandler()  # 输出到控制台
    ]
)

logger = logging.getLogger(__name__)

logger.info("主服务启动")

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





        
@app.route('/net_search', methods=['POST'])
def net_search_service():
    data = request.get_json()
    print("接收到请求数据：",data,flush=True)

    query = data.get("query")
    search_url = data.get("search_url")
    search_key = data.get("search_key")
    search_rerank_id = data.get("search_rerank_id")
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
            model, days_limit, auto_citation,search_url,search_key,search_rerank_id
        )
        result = loop.run_until_complete(task)
        bing_prompt, bing_search_list = result
        #context = "".join(item["snippet"] for item in bing_search_list)
        result = '，'.join([f'参考信息{i+1}：{item}' for i, item in enumerate(bing_search_list)])
        context = '请根据以下网络搜索出来的参考信息回答用户问题'+result
        print('context:',context,flush=True)
        return context


    except Exception as e:
        print('错误:',str(e))
        return jsonify({"error": str(e)}), 500
    finally:
        loop.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1990)

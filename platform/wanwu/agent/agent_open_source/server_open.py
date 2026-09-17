import requests
import json
import os
import anyio
from openai import OpenAI

from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph,END,START
from typing import List, Dict, Optional,Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import ToolMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
import io
from datetime import datetime
from flask import  stream_with_context, Response, request,jsonify
from flask import Flask
from flask_cors import CORS
from logging_config import setup_logging
from bing_plus import *
import configparser
from langchain.requests import RequestsWrapper
from agent_plugin.sse_protocol import consume_action_event


logger_name = 'agent'
app_name = os.getenv("LOG_FILE")
logger = setup_logging(app_name, logger_name)
logger.info(logger_name + '---------LOG_FILE：' + repr(app_name))


def agent_error_event(message):
    return {
        "code": 1,
        "message": message or "Action 执行失败",
        "response": "",
        "finish": 1,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "search_list": [],
        "gen_file_url_list": [],
    }


app = Flask(__name__)
CORS(app, supports_credentials=True)



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







os.environ["ARK_API_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjAwYWM5NjJkLTMxNDItNGYxNy05YjAxLWJkMDQ2MjRhZmI1MCIsInRlbmFudElEcyI6bnVsbCwidXNlclR5cGUiOjAsInVzZXJuYW1lIjoid2FuZ3l5NjAzIiwibmlja25hbWUiOiLnjovoibPpmLMiLCJidWZmZXJUaW1lIjoxNzQ4MzQ5MDE5LCJleHAiOjIzNzkwNjE4MTksImp0aSI6IjMxNjU0ZjdiMmFhZjQ2NDI5Mzc0MzFkN2Q4NThhNWJiIiwiaWF0IjoxNzQ4MzQxNTE5LCJpc3MiOiIwMGFjOTYyZC0zMTQyLTRmMTctOWIwMS1iZDA0NjI0YWZiNTAiLCJuYmYiOjE3NDgzNDE1MTksInN1YiI6ImtvbmcifQ.w1cMbQWTQZIbxrz7DYt14xFSAt8BQCpyjFFhUO6JrwY"




@app.route("/agent",methods=['POST'])
def agent_start():
    @stream_with_context
    def generate():
        try:

            data = request.get_json()
            logger.info('入参是request_params: '+ json.dumps(data, ensure_ascii=False))
            #基本参数
            question = data.get("input")
            stream = data.get("stream",True)
            history = data.get("history",[])
            userId = request.headers.get('X-Uid')
            function_call = data.get("function_call",False)
            logger.info('user_id是:'+userId)
            



            #大模型参数
            model = data.get("model")
            model_url = data.get("model_url")
            system_role = data.get("system_role",'')
            model_id = data.get("model_id")
            
            do_sample = data.get("do_sample",False)
            temperature = data.get("temperature",0.7)
            repetition_penalty = data.get("repetition_penalty",1)
            frequency_penalty = data.get("frequency_penalty",0)
            presence_penalty = data.get("presence_penalty",0)
            top_p = data.get("top_p",0.7)
            top_k = data.get("top_k",50)
            max_tokens = data.get("max_tokens",1024)
            enable_thinking = data.get("enable_thinking",False)

            #搜索参数
            auto_citation = data.get("auto_citation",True)
            use_search = data.get("use_search",False)
            need_search_list = data.get("need_search_list",True)
            search_url = data.get("search_url",'')
            search_key = data.get("search_key",'')
            search_rerank_id = data.get("search_rerank_id",'11')



            #代码解释器参数
            use_code = data.get("use_code",False)
            file_name = data.get("file_name")
            upload_file_url = data.get("upload_file_url",'')


            #rag参数
            chitchat = data.get("chitchat",False)
            kn_params = data.get("kn_params",{})
            use_know = data.get("use_know",False)

            #其他插件参数
            plugin_list = data.get("plugin_list",[])

            if kn_params:
                knowledgebase_name = kn_params.get('knowledgeBase')
                threshold = kn_params.get('threshold',0.4)
                topk = kn_params.get('topk',5)
                rerank_id = kn_params.get('rerank_id')
            


            used_rag = False
            #如果传参有知识库 则先走rag
            if use_know:
                print('-----------先走知识库回答')
                url = "http://172.17.0.1:10891/rag/knowledge/stream/search" 

                payload = {
                    "knowledgeBase": knowledgebase_name,
                    "question": question,
                    "threshold": threshold,
                    "topK": topk,
                    "stream": True,
                    "chitchat": False,
                    "history": [],
                    "auto_citation":auto_citation,
                    "rerank_model_id":rerank_id,
                    "custom_model_info":{"llm_model_id":model_id}
                }


                headers = {
                    "Content-Type": "application/json",
                    "X-uid": userId
                }
                logger.info('rag:'+json.dumps(payload))
                # 发送POST请求
                response = requests.post(url, headers=headers, data=json.dumps(payload),stream=True,verify=False)
                if response.status_code == 200:
                    first_line_checked = False
                    for line in response.iter_lines():
                        if line:
                            try:
                                decoded_line = line.decode("utf-8").strip()
                                if decoded_line.startswith("data:"):
                                    decoded_line = decoded_line[len("data:"):].strip()
                                data = json.loads(decoded_line)
                                if not first_line_checked:
                                    first_line_checked = True
                                    if data["data"]["searchList"]:
                                        print('知识库可回答')
                                        used_rag = True
                                    print('知识库无法回答')
                                if used_rag:
                                    answer = {
                "code": 0,
                "message": "success",
                "response": "",
                "gen_file_url_list": [

                ],
                "history": [],
                "finish": 0,
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                },
                "search_list": [],
                "qa_type":1
                }
                                    answer['response']=data["data"]["output"]
                                    answer['code']=data["code"]
                                    answer['finish']=data["finish"]
                                    answer['message']=data["message"]
                                    answer['search_list']=data["data"]["searchList"]
                                    answer['history']=data["history"]
                                    
                                    yield f"data: {json.dumps(answer, ensure_ascii=False)}\n\n"
                            except Exception as e:
                                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            if not used_rag:
                print('------------走action')
                action_url = "http://172.17.0.1:1992/agent/action"
                headers = {
                    "Content-Type": "application/json"
                }

                netsearch_schema =         {
        "api_schema": {
            "info": {
                "description": "用于通过网络查询搜索实时问题的相关信息来回答用户的问题",
                "title": "网络搜索",
                "version": "1.0.0"
            },
            "openapi": "3.0.0",
            "paths": {
                "/net_search": {
                    "post": {
                        "description": "用于通过网络查询搜索实时问题的相关信息来回答用户的问题",
                        "summary":"netsearch",
                        "operationId": "netsearch",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "properties": {
                                            "query": {
                                                "description": "用户提出的问题",
                                                "type": "string"
                                            },
                                            "search_url":{
                                                "description":"联网搜索使用的浏览器的url",
                                                "type":"string"
                                                },
                                            "search_key":{
                                                "description": "联网搜索使用的浏览器url对应的key",
                                                "type":"string"
                                            },
                                            "search_rerank_id":{
                                                "description":"联网搜索内容使用的排序模型id",
                                                "type":"string"
                                                }
                                        },
                                        "required": [
                                            "query",
                                            "search_url",
                                            "search_key",
                                            "search_rerank_id"
                                        ],
                                        "type": "object"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "servers": [
                {
                    "url": "http://172.17.0.1:1990"
                }
            ]
        }
    }
                
                
                chatdoc_schema =         {
        "api_schema": {
            "info": {
                "description": "用于解析并回答用户上传的docx、txt、xlsx各种类型文件内容的问题",
                "title": "chatdoc",
                "version": "1.0.0"
            },
            "openapi": "3.0.0",
            "paths": {
                "/doc_pra": {
                    "post": {
                        "description": "用于解析并回答用户上传的docx、txt、xlsx各种类型文件内容的问题",
                        "summary":"chatdoc",
                        "operationId": "chatdoc",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "properties": {
                                            "query": {
                                                "description": "用户提出的问题",
                                                "type": "string"
                                            },
                                            "upload_file_url":{
                                                "description":"文件下载链接",
                                                "type":"string"
                                                }                                               
                                        },
                                        "required": [
                                            "query",
                                            "upload_file_url"
                                        ],
                                        "type": "object"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "servers": [
                {
                    "url": "http://172.17.0.1:1991"
                }
            ]
        }
    }

                if use_search:
                    plugin_list.append(netsearch_schema)
                if upload_file_url:
                    plugin_list.append(chatdoc_schema)
                if plugin_list:

                    question = '问题是:'+question+'\n'+'以下是部分插件可能用到的参数：'+'upload_file_url:'+upload_file_url+'\n'+'search_url:'+search_url+'\n'+'search_key:'+search_key+'\n'+'search_rerank_id:'+search_rerank_id

                    print('送入action问题是:',question)
                    print('plugin_list是什么:',plugin_list)
                    if function_call:
                        payload = {
                            "input":question,
                            "plugin_list":plugin_list,
                            "action_type": "function_call",
                            "model_name":model,
                            "model_url":model_url
                        }
                    else:
                        payload = {
                            "input":question,
                            "plugin_list":plugin_list,
                            "action_type": "action_agent",
                            "model_name":model,
                            "model_url":model_url
                        }
                    response = requests.post(action_url, headers=headers, data=json.dumps(payload),stream=True,verify=False)
                    if response:
                        answer = {
    "code": 0,
    "message": "success",
    "response": "",
    "gen_file_url_list": [

    ],
    "history": [],
    "finish": 0,
    "usage": {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    },
    "search_list": [],
    "qa_type":20
}

                        for line in response.iter_lines(decode_unicode=True):
                            print('action输出是什么:',line)
                            if not line:
                                continue
                            answer, terminal = consume_action_event(line, answer, agent_error_event)
                            if answer is None:
                                continue
                            yield f"data:{json.dumps(answer,ensure_ascii=False)}\n"
                            if terminal:
                                break

                    else:

                        print('------没命中任何工具纯大模型回答')
                        llm = ChatOpenAI(
                            model_name=model,
                            streaming=True,
                            top_p = top_p,
                            max_tokens = max_tokens,
                            temperature = temperature,
                            frequency_penalty = frequency_penalty,
                            presence_penalty = presence_penalty,
                            base_url=model_url,
                            openai_api_key=os.environ["ARK_API_KEY"],
                        )
                        answer = {
    "code": 0,
    "message": "success",
    "response": "",
    "gen_file_url_list": [],
    "history": [],
    "finish": 0,
    "usage": {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    },
    "search_list": [],
    "qa_type":0
}
                        for chunk in llm.stream(question):
                            if hasattr(chunk, "content"):
                                print('大模型输出是:',chunk)
                                answer['response'] = chunk.content
                            if hasattr(chunk, "response_metadata"):
                                if 'finish_reason' in chunk.response_metadata and chunk.response_metadata['finish_reason']=='stop':
                                    answer['finish']=1
                            if hasattr(chunk, "usage_metadata") and chunk.usage_metadata is not None:
                                answer['usage']['prompt_tokens'] = chunk.usage_metadata['input_tokens'] if 'input_tokens' in chunk.usage_metadata else 0
                                answer['usage']['completion_tokens'] = chunk.usage_metadata['output_tokens'] if 'output_tokens' in chunk.usage_metadata else 0
                                answer['usage']['total_tokens'] = chunk.usage_metadata['total_tokens'] if 'total_tokens' in chunk.usage_metadata else 0
                            yield f"data:{json.dumps(answer,ensure_ascii=False)}\n"




                else:
                    print('------未配置任何工具纯大模型回答')
                    llm = ChatOpenAI(
                        model_name=model,
                        streaming=True,
                        top_p = top_p,
                        max_tokens = max_tokens,
                        temperature = temperature,
                        frequency_penalty = frequency_penalty,
                        presence_penalty = presence_penalty,
                        base_url=model_url,
                        openai_api_key=os.environ["ARK_API_KEY"],
                    )
                    answer = {
"code": 0,
"message": "success",
"response": "",
"gen_file_url_list": [],
"history": [],
"finish": 0,
"usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
},
"search_list": [],
"qa_type":0
}
                    for chunk in llm.stream(question):
                        if hasattr(chunk, "content"):
                            print('大模型输出是:',chunk)
                            answer['response'] = chunk.content


                            if hasattr(chunk, "response_metadata"):
                                if 'finish_reason' in chunk.response_metadata and chunk.response_metadata['finish_reason']=='stop':
                                    answer['finish']=1
                            if hasattr(chunk, "usage_metadata") and chunk.usage_metadata is not None:
                                answer['usage']['prompt_tokens'] = chunk.usage_metadata['input_tokens'] if 'input_tokens' in chunk.usage_metadata else 0
                                answer['usage']['completion_tokens'] = chunk.usage_metadata['output_tokens'] if 'output_tokens' in chunk.usage_metadata else 0
                                answer['usage']['total_tokens'] = chunk.usage_metadata['total_tokens'] if 'total_tokens' in chunk.usage_metadata else 0
                            yield f"data:{json.dumps(answer,ensure_ascii=False)}\n"



                    
        except Exception as e:
            logger.exception("❌ 处理请求失败：")
            error_data = {
                "code": 1,
                "message": str(e),
                "response": "",
                "finish": 1
            }
            yield f"data:{json.dumps(error_data, ensure_ascii=False)}\n"

    return Response(generate(), mimetype="text/event-stream")
    
    
    
if __name__ == '__main__':
    logger.info("agent_server start")
    app.run(host='0.0.0.0', port=7258, threaded=False,debug=False)

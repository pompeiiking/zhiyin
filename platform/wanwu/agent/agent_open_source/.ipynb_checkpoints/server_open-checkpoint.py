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
#from langchain.tools.openapi.utils.openapi_utils import OpenAPISpec,openapi_spec_to_tools
#from langchain.utilities.openapi import OpenAPISpec
#from langchain.chains.openai_functions.openapi import openapi_spec_to_tools

#from langchain.tools.openapi import OpenAPISpec, openapi_spec_to_tools

logger_name = 'agent'
app_name = os.getenv("LOG_FILE")
logger = setup_logging(app_name, logger_name)
logger.info(logger_name + '---------LOG_FILE：' + repr(app_name))


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
CODE_SCHEMA = config["CODE"]["CODE_SCHEMA"]




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





os.environ["ARK_API_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjAwYWM5NjJkLTMxNDItNGYxNy05YjAxLWJkMDQ2MjRhZmI1MCIsInRlbmFudElEcyI6bnVsbCwidXNlclR5cGUiOjAsInVzZXJuYW1lIjoid2FuZ3l5NjAzIiwibmlja25hbWUiOiLnjovoibPpmLMiLCJidWZmZXJUaW1lIjoxNzQ4MzQ5MDE5LCJleHAiOjIzNzkwNjE4MTksImp0aSI6IjMxNjU0ZjdiMmFhZjQ2NDI5Mzc0MzFkN2Q4NThhNWJiIiwiaWF0IjoxNzQ4MzQxNTE5LCJpc3MiOiIwMGFjOTYyZC0zMTQyLTRmMTctOWIwMS1iZDA0NjI0YWZiNTAiLCJuYmYiOjE3NDgzNDE1MTksInN1YiI6ImtvbmcifQ.w1cMbQWTQZIbxrz7DYt14xFSAt8BQCpyjFFhUO6JrwY"



os.environ["TAVILY_API_KEY"] = '************'


# 定义自己的大模型
class MyChatModel:
    def __init__(self, api_key, model="yuanjing-70b-functioncall", temperature=0):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.headers = {
            "Content-Type":"application/json",
            "Authorization":f"Bearer {api_key}"
        }
        self.api_url = "https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1/chat/completions"
        
        
    def bind_tools(self, tools):
        """绑定工具到模型"""
        self.tools = tools
        return self

    def chat(self, messages):
        # 系统提示词
        system_prompt = """你是一个智能助手，可以使用工具来回答用户问题。
    请遵循以下规则：
    1. 如果用户问题可以通过工具（如获取天气、搜索实时信息）更好地回答，请调用相应工具
    2. 如果用户问题不需要工具就能回答，请直接给出答案
    3. 工具调用必须遵循提供的工具规范
    4. 避免不必要的工具调用，只有在确实需要时才使用工具
    可用工具：
    - get_weather: 获取指定城市的当前天气
    - search: 搜索实时信息，适用于回答需要最新数据的问题"""

        messages_list = []
        for message in messages:
            if isinstance(message, HumanMessage):
                role = "user"
            else:
                role = "assistant"
            if message.content != "":
                messages_list.append({"role": role, "content": message.content})
        messages = [{"role": "system", "content": system_prompt}] + messages_list

        # 发送聊天请求
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "tools": self.tools if hasattr(self, 'tools') else []
        }
        try:
            response = requests.post(
                self.api_url,
                headers = self.headers,
                data=json.dumps(data)
            )
            response.raise_for_status()
            response = response.json()
            print('大模型回答：',response)
            return response["choices"][0]["message"]
        except requests.exceptions.RequestException as e:
            print(f"Error:{e}")
            return None


# 定义状态类型
class AgentState(TypedDict):
    # 历史消息列表
    messages: Annotated[list, add_messages]



# 配置会话id
config_fun = {"configurable": {"thread_id": "1"}}


@app.route("/agent",methods=['POST'])
def agent_start():
    @stream_with_context
    def generate():
        try:

            data = request.get_json()
            logger.info('入参是request_params: '+ json.dumps(data, ensure_ascii=False))
            #基本参数
            question = data.get("input")
            stream = data.get("stream")
            history = data.get("history")
            auth_header = request.headers.get('Authorization')
            userId = request.headers.get('X-Uid')
            function_call = data.get("function_call",False)


            #大模型参数
            model = data.get("model")
            model_url = data.get("model-url")
            system_role = data.get("system_role")
            
            
            do_sample = data.get("do_sample")
            temperature = data.get("temperature")
            repetition_penalty = data.get("repetition_penalty")
            frequency_penalty = data.get("frequency_penalty")
            top_p = data.get("top_p")
            top_k = data.get("top_k")
            max_tokens = data.get("max_tokens")
            do_think = data.get("do_think")

            #搜索参数
            auto_citation = data.get("auto_citation",True)
            use_search = data.get("use_search")
            need_search_list = data.get("need_search_list")
            #bing_top_k = data.get("bing_top_k")
            #bing_target_success = data.get("bing_target_success",10)
            #bing_time_out = data.get("bing_time_out",3.0)


            #代码解释器参数
            use_code = data.get("use_code")
            file_name = data.get("file_name")
            upload_file_url = data.get("upload_file_url")


            #rag参数
            #chitchat = data.get("chitchat",True)
            kn_params = data.get("kn_params",{})
            use_know = data.get("use_know")

            #其他插件参数
            plugin_list = data.get("plugin_list")
            #extend_params = data.get("extend_params")

            knowledgebase_name = ''
            if kn_params:
                knowledgebase_name = kn_params['knowledgeBase']
                threshold = kn_params['threshold']
                topk = kn_params['topk']


            used_rag = False
            #如果传参有知识库 则先走rag
            if use_know:
                print('-----------先走知识库回答')
                url = "https://maas-api.ai-yuanjing.com/openapi/knowledge/stream/search" 

                payload = {
                    "knowledgeBase": knowledgebase_name,
                    "question": question,
                    "threshold": threshold,
                    "topK": topk,
                    "stream": True,
                    "chitchat": False,
                    "history": [],
                    "auto_citation":auto_citation
                }
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
                #print('token是:',token)
                access_token = token

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}"
                }

                # 发送POST请求
                response = requests.post(url, headers=headers, data=json.dumps(payload),stream=True)
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
                                    print('知识库回答不了')
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
                    "prompt_tokens": 3272,
                    "completion_tokens": 79,
                    "total_tokens": 3351
                },
                "search_list": []
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

                if function_call:

                    print('---------走function_call模式')


                    #1.定义搜索插件
                    def net_search(query: str,model:str,model_url:str) -> str:
                        """Answer with some knowledge that can be searched online"""
                        try:
                            loop = None
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            days_limit = BING_DAYS_LIMIT
                            bing_top_k = BING_TOP_K
                            bing_time_out = BING_TIME_OUT
                            bing_target_success = 10
                            bing_result_len = BING_RESULT_LEN
                            auto_citation = False
                            model = LLM_MODEL_NAME
                            task = start_async_search(loop, query,bing_top_k,bing_time_out,bing_target_success,bing_result_len, model,days_limit, auto_citation)                     
                            result = loop.run_until_complete(task)
                            bing_prompt, bing_search_list, = result
                            context = "".join(item["snippet"] for item in bing_search_list)

                            print('上下文是:',context)
                            #now = datetime.now()
                            #date_str = now.strftime("%Y-%m-%d")
                            ACCESS_TOKEN = get_access_token()
                            TOOL_PROMPT_TEMPLATE = '''你是一个实时联网的智能问答助手，目前位于中国，你的主要任务是参考下列从互联网搜索到的网页信息回答用户问题。

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
                            prompt = TOOL_PROMPT_TEMPLATE.format(question=query,context=context[:3000])
                            llm = ChatOpenAI(
                                model=model,
                                api_key=ACCESS_TOKEN,
                                base_url=model_url,
                                temperature=0.7,
                                streaming=False
                            )

                            # 构造消息
                            messages = [
                                HumanMessage(content=prompt)
                            ]
                            response = llm(messages)
                            return response
                        finally:
                            loop.close()

                    #2.定义code插件
                    def code(query: str,upload_file_url:str) -> str:
                        """Used for code generation or code execution to solve problems."""
                        url = "http://192.168.0.172:7257/api/cal"
                        if upload_file_url:
                            need_file = True
                        else:
                            need_file = False
                        payload = {
                            "input": query,
                            "need_file": need_file,  # Change this based on your requirements
                            "history": [],
                            "upload_file_url": upload_file_url,
                            "language":"中文",
                            "stream":False
                        }

                        headers = {
                            "Content-Type": "application/json"
                        }

                        # 发送POST请求
                        #response = requests.post(url, headers=headers, data=json.dumps(payload))
                        response = requests.post(url, data=json.dumps(payload), headers=headers)
                        if response.status_code == 200:
                            data = json.loads(response.text)
                            content = data["data"]["choices"][0]["message"]["content"]
                            return content
                        else:
                            print(f"请求失败，状态码: {response.status_code}")
                            print(response.text)

                    #3.天气插件                
                    def get_weather(city: str) -> str:
                        if city == "北京":
                            return f"{city}天气晴朗，温度28度。"
                        return f"{city}天气多云，微风。"


                    #spec = OpenAPISpec.from_file("amp.json")
                    #requests_wrapper = RequestsWrapper()
                    #tools_plugin = openapi_spec_to_tools(spec, requests_wrapper=requests_wrapper)


                    # 定义工具的json-schema描述
                    tools = [
                        {
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "city": {"type": "string", "description": "城市名称"}
                                    },
                                    "required": ["city"]
                                },
                                "description": "获取指定城市的当前天气"
                            }
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "net_search",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "需要搜索的内容"}
                                    },
                                    "required": ["query","model","model_url"]
                                },
                                "description": "搜索实时信息，适用于回答需要最新数据的问题"
                            }
                    }
                    ]
                    llm = MyChatModel(api_key=os.environ["ARK_API_KEY"], model=model,temperature=0).bind_tools(tools)

                    #tools.extend(tools_plugin)
                    print('tools有哪些:',tools)
                    # 添加Agent节点
                    def run_agent(state: AgentState):
                        message = state["messages"][-1]
                        if not isinstance(message, HumanMessage) and message.content != "":
                            return
                        return {"messages": [llm.chat(state["messages"])]}



                    def run_tool(state: AgentState):
                        message = state["messages"][-1]
                        outputs = []
                        if hasattr(message, "tool_calls") and len(message.tool_calls) > 0:
                            for tool_call in message.tool_calls:
                                name = tool_call["name"]
                                args = tool_call["args"]
                                # 根据工具的名字调用不同的工具
                                if name == "get_weather":
                                    function = get_weather
                                if name == "net_search":
                                    function = net_search
                                # 执行工具函数
                                observation = function(**args)
                                outputs.append(
                                    ToolMessage(
                                        content=observation,
                                        name=name,
                                        tool_call_id=tool_call["id"],
                                    )
                                )
                        return {"messages": outputs}





                    # 创建图结构
                    workflow = StateGraph(AgentState)

                    # 添加节点
                    workflow.add_node("agent", run_agent)
                    workflow.add_node("tool", run_tool)
                    workflow.set_entry_point("agent")  # 正确设置入口节点


                    # 路由函数，根据是否包含工具调用判断
                    def route(state: AgentState):
                        messages = state["messages"][-1]
                        if hasattr(messages, "tool_calls") and len(messages.tool_calls) > 0:
                            return "tool"
                        return "end"

                    # 添加条件边
                    workflow.add_conditional_edges(
                        "agent",
                        route,
                        {
                            "tool": "tool",
                            "end": END
                        }
                    )
                    # 添加普通边
                    workflow.add_edge("tool", "agent")

                    # 初始化记忆模块
                    memory = MemorySaver()

                    # 编译图
                    #graph = workflow.compile(checkpointer=memory)
                    graph = workflow.compile()

                    # 初始化大模型并绑定工具

                    question = '问题是:'+question+'\n'+'以下是插件可能用到的参数：'+'\n'+'model:'+model+'\n'+'model_url:'+model_url+'\n'+'upload_file_url:'+upload_file_url
                    answer = {
"code": 0,
"message": "success",
"response": "",
"gen_file_url_list": [],
"history": [],
"finish": 0,
"usage": {
    "prompt_tokens": 3272,
    "completion_tokens": 79,
    "total_tokens": 3351
},
"search_list": []

}
                    initial_state = {
    "input": question,
    "messages": [HumanMessage(content=question)],
    # 如使用 checkpoint，还可以传入 "thread_id" 等
}                
                    
                    
                    for event in graph.stream(initial_state):                        
                        print("🔹 Event:", event)
                        
                        if "agent" in event and "messages" in event["agent"]:
                            message = event["agent"]["messages"][-1]
                            if hasattr(message, "tool_calls"):
                                for call in message.tool_calls:
                                    tool_name = call["name"]
                                    print(f"🛠️ Agent决定调用工具：{tool_name}")
                                    yield f"[Agent 调用工具]: {tool_name}"
                        if "tool" in event and "messages" in event["tool"] and event["tool"]["messages"]: 
                            content = event["tool"]["messages"][-1].content
                            match = re.search(r"content='(.*?)'", content)
                            content = match.group(1)
                            print('tool的输出:',content)
                            yield content
                            
                            #print(event["messages"][-1]["content"])
                            #yield event["messages"][-1]["content"]
                    #result = graph.invoke({"messages": [{"role": "user", "content": question}]}, config_fun)
                    #for output in graph.stream({"messages": [HumanMessage(content=question)]},config=config_fun):
                        #yield f"data:{json.dumps(output, ensure_ascii=False)}\n\n"
                        
                        
                    
                    #response = result["messages"][-1].content
                    #yield response
                else:
                    #走非function call流程，action逻辑，所有功能均为工具传入action一并输出
                    print('------------走action')
                    action_url = "http://localhost:4802/agent/action"
                    headers = {
                        "Content-Type": "application/json"
                    }
                    code_schema =         {
            "api_schema": {
                "info": {
                    "description": "用于生成代码、跑代码、通过编写代码处理文件",
                    "title": "代码解释器API",
                    "version": "1.0.0"
                },
                "openapi": "3.0.0",
                "paths": {
                    "/api/cal": {
                        "post": {
                            "description": "用于回答用户的代码类问题，例如生成代码、跑代码、通过编写代码处理文件 ",
                            "summary":"生成代码跑代码处理文件",
                            "operationId": "CodeGeneration",
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "properties": {
                                                "input": {
                                                    "description": "用户提出的问题",
                                                    "type": "string"
                                                },
                                                "upload_file_url": {
                                                    "description": "文件下载链接",
                                                    "type": "string"
                                                },
                                                "is_use_api_output":{
                                                    "description":"是否直接使用api结果进行输出，默认为True",
                                                    "type":"string"
                                                },
                                                "stream":{
                                                    "description":"是否流式回答,默认为True",
                                                    "type":"string"
                                                }   
                                            },
                                            "required": [
                                                "input",
                                                "is_use_api_output",
                                                "stream"
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
                        "url": "http://192.168.0.172:7257"
                    }
                ]
            }
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
                            "summary":"网络搜索信息",
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
                                                "model": {
                                                    "description": "选择的模型名称",
                                                    "type": "string"
                                                },
                                                "is_use_api_output":{
                                                    "description":"是否直接使用api结果进行输出，默认为True",
                                                    "type":"string"
                                                },
                                                "model_url":{
                                                    "description":"模型调用url",
                                                    "type":"string"
                                                },
                                                "stream":{
                                                    "description":"是否流式回答,默认为True",
                                                    "type":"string"
                                                }                                                
                                            },
                                            "required": [
                                                "query",
                                                "is_use_api_output",
                                                "model",
                                                "model_url",
                                                "stream"
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
                        "url": "http://192.168.0.126:1990"
                    }
                ]
            }
        }
                    
                    
                    if use_code:
                        plugin_list.append(code_schema)
                    if use_search:
                        plugin_list.append(netsearch_schema)
                    if plugin_list:
                        
                        question = '问题是:'+question+'\n'+'以下是插件可能用到的参数：'+'\n'+'model:'+model+'\n'+'model_url:'+model_url+'\n'+'upload_file_url:'+upload_file_url

                        print('plugin_list是什么:',plugin_list)
                        payload = {
                            "input":question,
                            "plugin_list":plugin_list,
                            "action_type": "qwen_agent",
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
            "prompt_tokens": 3272,
            "completion_tokens": 79,
            "total_tokens": 3351
        },
        "search_list": []
    }

                            for line in response.iter_lines(decode_unicode=True):
                                print('action输出是什么:',line)
                                if line.startswith("data:"):
                                    line = line[5:]
                                    datajson = json.loads(line)
                                    answer['code'] = datajson['code']
                                    answer['message'] = datajson['msg']
                                    content_str = datajson['data']['choices'][0]['message']['content']
                                    if isinstance(content_str, dict):
                                        if "search_list" in content_str:
                                            answer['search_list'] = content_str.get('search_list')
                                        if "gen_file_url_list" in content_str:
                                            answer['gen_file_url_list'] = content_str.get('gen_file_url_list')

                                        answer['response'] = content_str.get('response')
                                    else:
                                        answer['response'] = datajson['data']['choices'][0]['message']['content']
                                    if datajson["data"]["choices"][0]["finish_reason"] == '':
                                        answer['finish']=0
                                    else:
                                        answer['finish']=1



                                    answer['usage']['completion_tokens'] = datajson["data"]["usage"]['completion_tokens']
                                    answer['usage']['prompt_tokens'] = datajson["data"]["usage"]['prompt_tokens']
                                    answer['usage']['total_tokens'] = datajson["data"]["usage"]['total_tokens']


                                    yield f"data:{json.dumps(answer,ensure_ascii=False)}\n"

                        else:
                            
                            print('------没命中任何工具走纯大模型回答')
                            llm = ChatOpenAI(
                                model_name=model,
                                streaming=True,
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
        "search_list": []
    }
                            for chunk in llm.stream(question):
                                # chunk 是一个 AIMessageChunk 或 ChatMessageChunk，要转成字符串
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
                            #answer["finish"] = 1
                            #yield f"data:{json.dumps(answer, ensure_ascii=False)}\n"

                            


                    else:
                        print('------未配置任何工具走纯大模型回答')
                        llm = ChatOpenAI(
                            model_name=model,
                            streaming=True,
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
        "prompt_tokens": 3272,
        "completion_tokens": 79,
        "total_tokens": 3351
    },
    "search_list": []
}
                        for chunk in llm.stream(question):
                            # chunk 是一个 AIMessageChunk 或 ChatMessageChunk，要转成字符串
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
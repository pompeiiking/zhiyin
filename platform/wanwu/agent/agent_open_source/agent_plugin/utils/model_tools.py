import uuid
import os
import requests
import json
import re
import base64
import io
import logging
import requests
from typing import Any, Dict, List,Union

import requests
import datetime,time

from utils.auth import AccessTokenManager
from utils.langchain_unicomai import ChatUnicomAI
from langchain_openai import ChatOpenAI 
from openai import RateLimitError  # 新的导入方式
from langchain_openai import ChatOpenAI 
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
)
from openai import RateLimitError  # 新的导入方式

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import configparser

config = configparser.ConfigParser()
config.read('config.ini')

HISTORY_TURNS_NUM =10

logger = logging.getLogger(__name__)

# 实例化对象
token_manager = AccessTokenManager()

# MODEL_NAME = "unicom-72b-chat-ali"
# MODEL_NAME = "unicom-34b-chat"


MODEL_NAME_CONFIG = config["MODELS"]["default_llm"]
env_value_model = os.getenv('CUAI_DEFAULT_LLM_MODEL_ID')
MODEL_NAME = MODEL_NAME_CONFIG if env_value_model is None or env_value_model.strip() == "" else env_value_model

OPENAI_BASE_URL = config["MODELS"]["openai_base_url"]
DEFAULT_TEMPERATURE = config["MODELS"]["default_llm_param_temperature"]

MODEL_URL_CONFIG = config["MODELS"]["model_url"]
env_value_model_url = os.getenv('CUAI_DEFAULT_LLM_MODEL_URL')
MODEL_URL = MODEL_URL_CONFIG if env_value_model_url is None or env_value_model_url.strip() == "" else env_value_model_url

# DEPLOY_MODE = config["DEPLOY"]["DEPLOY_MODE"]
# MODEL_NAME = "qwen-14b-chat"

'''
# 元景语言大模型服务封装,支持流式和非流式
# 可用模型：unicom-7b-chat, unicom-13b-chat, unicom-34b-chat,unicom-13b-special(多轮query改写、系统提示词、会议纪要/摘要、纪委约谈),unicom-16b-math,unicom-70b-chat
def req_unicom_llm_chat(messages:List, stream=True, model_name=MODEL_NAME, do_sample=False,temperature=0.00001,repetition_penalty=1.1,stop_words =  ['Observation:', 'Observation:\n','Observation: ','Observation: \n']):    
    # logger.info(f"调用大模型的prompt为：{messages}")
    # logger.info(f"调用大模型的prompt为：{messages}")
    # if model_name == "unicom-70b-chat":
    #     url = config["MODELS"]["unicom_70b_url"]
    #     access_token = "Mzg5NmZmMWUwNTYyZGVlNjZkNjYwZjdmYTQxM2U0MGM1MzMzMmNkZA=="   
    # elif model_name == "unicom-16b-math":
    #     url = "http://1654416620085582.cn-wulanchabu.pai-eas.aliyuncs.com/api/predict/code_v2_16b/v1/coder/generate"               
    #     access_token = "NjcxZmVhNDYyZjIzMWJhNjZmMDFkOWVmZWZkNjQ5MTI4NmFmYmFiZA=="
    # elif model_name == "unicom-70b-math":
    #     url = "http://1654416620085582.cn-wulanchabu.pai-eas.aliyuncs.com/api/predict/llm_math_72b/v1/chat/completions"               
    #     access_token = "YmU0YWI0OGUzMWY4MjIxNDhkN2U5ODg4YzMzZGY2MzU3MmI5YWZiNA=="
    # else:
    base_url = config["MODELS"]["unicom_base_url"]
    url = base_url + model_name
    access_token = token_manager.get_access_token()  # 获取 token

    data = {
    	"stream": stream,
        # "max_new_tokens": 8192,
        "temperature":temperature,
        "do_sample":do_sample,
        "repetition_penalty": repetition_penalty,
    	"messages": messages        
    }
    
    # logger.info(f"req_unicom_llm_chat data:{data}")

    
    headers = {"Content-Type": "application/json","Authorization": f"Bearer {access_token}"}
    # logger.info(f"req_unicom_llm_chat param:{json.dumps(data,ensure_ascii=False,indent=4)}")
    # logger.info(f"req_unicom_llm_chat param:{json.dumps(data,ensure_ascii=False,indent=4)}")

    try:
        response = requests.post(url,json =data, headers = headers, verify=False, stream=stream)
        # logger.info(f"req_unicom_llm_chat response:{response.text}")
        # logger.info(f"req_unicom_llm_chat response:{response.text}")
        # logger.info(f"req_unicom_llm_chat response:{json.dumps(response.json(),ensure_ascii=False,indent=4)}")
        return response

    except requests.RequestException as e:
        logger.error("LLM API error: %s", e)  # 记录错误日志
        return "No answer found due to LLM API error"
'''

def parse_error_to_dict(error) -> Dict[str, Any]:
    """将错误信息转换为字典类型"""
    try:
        # 从错误信息中提取 JSON 部分
        error_str = str(error)
        # 使用正则表达式匹配 '-' 后面的 JSON 字符串
        match = re.search(r'-\s*(\{.*\})', error_str)
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        # 如果没有匹配到 JSON 格式，返回基本错误信息
        return {
            "error": {
                "message": str(error),
                "type": type(error).__name__,
                "code": getattr(error, 'code', 'unknown')
            }
        }
    except Exception as e:
        # 确保总是返回一个有效的错误字典
        return {
            "error": {
                "message": str(error),
                "parse_error": str(e),
                "type": "error_parse_failed"
            }
        }

def req_unicom_llm_chat(messages: List, 
                       stream: bool = True,
                       model_name: str = MODEL_NAME, 
                       model_url = "",
                       do_sample: bool = False,
                       repetition_penalty: float = 1.1,
                       temperature: float = DEFAULT_TEMPERATURE
                    ) -> Union[Any, Dict[str, Any]]:
    # logger.info(f"model_tools req_unicom_llm_chat messages:{messages} ")

    if model_url and model_name.lower() not in model_url:
        base_url = model_url
    elif model_name.lower() in model_url:
        base_url, _, model_name = model_url.rpartition('/')
    elif model_name and not model_url:
        base_url, _, _ = MODEL_URL.rpartition('/')
    else:
        base_url, _, model_name = MODEL_URL.rpartition('/')

    logger.info(f"model_tools req_unicom_llm_chat base_url:{base_url} model_name:{model_name}")

    llm = ChatOpenAI(
        model=model_name,
        temperature=0.6,  #deepseek系列模型写死
        base_url=base_url,

        api_key = token_manager.get_access_token()
    )
    # logger.info(f"llm:{llm}")
    try:

        if stream:
            result = llm.stream(messages)  
            # print(result)
            return result 
        else:
            return llm.invoke(messages)
            
    except RateLimitError as e:
        error_dict = parse_error_to_dict(e)
        print(f"\n限速错误: {json.dumps(error_dict, indent=2, ensure_ascii=False)}")
        return None
        
    except Exception as e:
        error_dict = parse_error_to_dict(e)
        print(f"\n意外错误: {json.dumps(error_dict, indent=2, ensure_ascii=False)}")
        return None

def req_unicom_llm_chat_plus(messages:List, stop_words =  ['REASON'], model_name="",model_url = "",temperature=0.1):    
    def check_words_in_string(input_string,stop_words):
        for word in stop_words:
            if word in input_string:
                return True
        return False

    # logger.info(f"model_tools req_unicom_llm_chat_plus messages:{messages} ")
    if model_url and model_name.lower() not in model_url:
        base_url = model_url
    elif model_name.lower() in model_url:
        base_url, _, model_name = model_url.rpartition('/')
    elif model_name and not model_url:
        base_url, _, _ = MODEL_URL.rpartition('/')
    else:
        base_url, _, model_name = MODEL_URL.rpartition('/')

    logger.info(f"model_tools req_unicom_llm_chat_plus  base_url:{base_url}  model_name:{model_name}")
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.6,  #deepseek系列模型写死
        base_url=base_url,
        api_key = token_manager.get_access_token()
    )
        
    # logger.info(f"llm:{llm}")

    try:
        # print(messages)
        response = llm.stream(messages)
        complete_content=""
        for chunk in response:
            incremental_content = chunk.content
            complete_content += incremental_content
            if check_words_in_string(complete_content,stop_words):
                break
        
        # logger.info(f"chat_plus result:{complete_content}")
        return complete_content
    except RateLimitError as e:
        error_dict = parse_error_to_dict(e)
        logger.info(f"\n限速错误: {json.dumps(error_dict, indent=2, ensure_ascii=False)}")
        return complete_content
        
    except Exception as e:
        error_dict = parse_error_to_dict(e)
        logger.info(f"\n意外错误: {json.dumps(error_dict, indent=2, ensure_ascii=False)}")
        return complete_content

def can_answer_question(question, kb_result_str,model_name = MODEL_NAME,model_url = ""):
#     flag = False
#     KN_USED_PROMPT_TEMPLATE = '''文本内容：
#         {context} 
#        根据上述文本内容，判断是否可以回答用户的问题。\n\n用户问题是：{question}。\n\n如果完全无法从中得到答案，请回答 “否”。如果可以从中得到答案或者部分答案，请回答“是”。 \n\n现在请回答'''

#     prompt = KN_USED_PROMPT_TEMPLATE.format(context=kb_result_str, question=question)
    
#     messages = []
#     subjson = {}
#     subjson["role"] = "user"
#     subjson["content"] = prompt
#     messages.append(subjson)
    
    
#     response = req_unicom_llm_chat(messages, stream=False,model_name = MODEL_NAME)
#     # logger.info(f"can_answer_question的response: {response.content}")
#     result = response.content
#     # result = response.json()["data"]["choices"][0]["message"]["content"]
#     # logger.info(f"can_answer_question的question: {question}")
#     # logger.info(f"can_answer_question的kb_result_str: {kb_result_str}")
#     logger.info(f"can_answer_question: {result}")
#     if result.find('是') >= 0:
#         flag = True 
#     return flag

    KN_USED_PROMPT_TEMPLATE = '''根据下面参考信息，判断是否可以回答用户问题
    
    【参考信息】：
    ```
     {context} 
    ```   

     【用户问题】
     ```
     {question}
     ```
     
     输出要求：
     ## 如果无法从中得到答案，请回答 "0",并说明原因。如果可以从中得到答案，请回答"1"。
     ## 请用json格式回答，key为TYPE和REASON。'''

    prompt = KN_USED_PROMPT_TEMPLATE.format(context=kb_result_str, question=question)
    messages = []
    subjson = {}
    subjson["role"] = "user"
    subjson["content"] = prompt
    messages.append(subjson)
    # model_name = model_name if  DEPLOY_MODE =="PRIVATE" else MODEL_NAME
    response = req_unicom_llm_chat_plus(messages, ["REASON"],model_name,model_url)
    pattern = r',\s*"?REASON.*'
    result = re.sub(pattern, '}', response)
    
    result_json = extract_json(result)
    logger.info(f"can_answer_question  response: {result_json}")

    flag = int(result_json.get("TYPE",0))
    return flag

def extract_json(text):
        # 使用正则表达式查找第一个包含在大括号之间的内容，并包括大括号本身
        match = re.search(r'\{.*?\}', text, re.DOTALL)
        if match:
            json_content = match.group(0)
            try:
                # 尝试将提取的内容解析为JSON
                json_data = json.loads(json_content)
                return json_data
            except json.JSONDecodeError as e:
                logger.error("is_answer_additional_remarks--extract_json error: %s", str(e))  # 记录错误日志:
                json_data = {"flag":0,"reason": f"{str(e)}"}
                return json_data
        else:
            json_data = {"flag":0,"reason": f"大模型生成内容不规范，无法回答：{text}"}
            return json_data

def is_answer_additional_remarks(question, final_answer,model_name = MODEL_NAME,model_url = ""):
    flag = False
    KN_USED_PROMPT_TEMPLATE = '''请根据以下参考信息进行分析，以判断所提供的句子是否属于以下类别：对用户问题的补充、进一步说明或追问。
              在做出判断时，句子不得是对问题的直接解答、答案假设、预防措施、建议，而应是对问题本身的进一步追问或额外的信息请求。

            【参考信息】：
            ```
             {context} 
            ```   

             【用户问题】
             ```
             {question}
             ```

             输出要求：
             ## 如果是，请回答1，并给出说明。如果不是，请回答0，并阐述原因。
             ## 请直接以纯净的json格式回答，key为flag和reason，不要其他任何信息。
             '''
    prompt = KN_USED_PROMPT_TEMPLATE.format(context=final_answer, question=question)
    
    messages = []
    subjson = {}
    subjson["role"] = "user"
    subjson["content"] = prompt
    messages.append(subjson)
    # model_name = model_name if DEPLOY_MODE == "PRIVATE" else MODEL_NAME
    # response = req_unicom_llm_chat(messages, stream=False,model_name = MODEL_NAME)
    response = req_unicom_llm_chat_plus(messages, ["REASON"],model_name,model_url)
    # result = response.json()["data"]["choices"][0]["message"]["content"]
    result = response
    logger.info(f"is_answer_additional_remarks response: {result}")
    result_json = extract_json(result)
    return result_json


def req_unicom_llm_chat_function_call(messages:List, tools = [],stream=True, model_name="unicom-70b2_function_call_test", do_sample=False,temperature=0,top_p=1e-9,stop_reason= "Observation"):
    url = config["MODELS"]["unicom_70b_function_call_url"]
    # access_token = "ZDhjOTgyYWJiMzFmNmVlNWZhMGViYTYyMmU3NjJjOGU1MzBmYmFjNQ==" 
    access_token = token_manager.get_access_token()
    data = json.dumps({
    	"stream": stream,
        "temperature":temperature,
        "do_sample":do_sample,
    	"messages": messages,
        "tools":tools
    })
    # logger.info(f"data:{data}")
    # logger.info(access_token)
    headers = {"Content-Type": "application/json","Authorization": f"Bearer {access_token}"}
    # logger.info(f"headers:{headers}")

    try:
        response = requests.post(url, data, headers = headers, verify=False, stream=stream)
        return response

    except requests.RequestException as e:
        return "No answer found due to LLM API error"

    
def is_query_sen(query):
    # url = "http://192.168.0.247:1005/check"
    # url配置校验，增加对私有化版本的兼容
    url = config["MODELS"]["sensitive_url"]
  
    contents = []
    contents.append(query)
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "contents": contents
    }

    try:
        response = requests.post(url, json=data, headers=headers, verify=False)
        return response

    except Exception as e:
        return e


def req_action(query,plugin_list = None,function_calls_list = None,action_type = "qwen_agent",history = []):
    url = config["ACTION"]["url"]
    data = {"input":query,
            "plugin_list":plugin_list,
            "function_calls_list":function_calls_list,
            "action_type":action_type,
            "history":history
            }
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=data, verify=False)
        return response

    except Exception as e:
        
        return e

    

    
if __name__ == "__main__":
    question = "帮我查询这个月的销量"
    final_answer = ""
    result = is_answer_additional_remarks(question, final_answer)

    

import configparser
import os
import json
import yaml


def list_all_files(directory):
    """
    递归地列出指定目录及其子目录下的所有文件
    """
    all_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files


###批量配置function
def function_config(act_filepaths) :
    configurations = []
    for i in range(0,len(act_filepaths)):
        if ".yaml" in act_filepaths[i] or ".yml" in act_filepaths[i]:
            with open(act_filepaths[i], 'r', encoding='utf-8') as yaml_file:
                api_schema = yaml.safe_load(yaml_file)
                ##保存为json字符串格式
                api_schema = json.dumps(api_schema,ensure_ascii=False)
                ##json解析为字典格式
                api_schema = json.loads(api_schema)
                #print(api_schema)
                #result = LLMActions(api_schema, api_auth)
                configurations.append(api_schema)

        if ".json" in act_filepaths[i]:
            with open(act_filepaths[i], 'r', encoding='utf-8') as file:
                api_schema = json.load(file)
                configurations.append(api_schema)
    return configurations


tool_list =  list_all_files('action_files')
tools = function_config(tool_list)


func_list =  list_all_files('function_files')
func_tools = function_config(func_list)

# 创建一个ConfigParser对象
config = configparser.ConfigParser()

############## 添加配置项###############

config['DEFAULT'] = {
    'HISTORY_TURNS_NUM': '10',        #历史对话轮数
    'MODEL_NAME': 'unicom-34b-chat',  #调用大模型名称
    'r_stream':True,                  #是否流式输出
    'use_lvm':True,                   #是否启用视觉大模型
    'rag_first':False ,               #是否强制启用RAG
    'use_search':True,                #是否启用bing搜索
    'plugins_enabled': False,         #是否启用插件
    'function_enabled': False,        #是否启用function_call
    'need_search_list':True,          #是否输出查询列表
    'use_know':True,                  #是否启用知识库
    'use_code': True,                 #是否启用代码解释器
    'need_update_file':False,         #是否需要上传文件
    'is_need_rewrite':True,           #是否需要改写
    'is_query_sens':False             #是否涉敏
}

config['qa_types'] = {
    "ORIGINAL": 0,
    "COMMON_SENSE": 1,
    "WEB_SEARCH": 2,
    "TEMP_KB": 3,
    "CODE_INTERPRETER": 4,
    "TXT2IMG": 5,
    "IMG2TXT": 6,
    "ACTION": 7,
    "TXT2VID":8
}


config['RAG'] = {
    'RAG_THRESHOLD': '0.7',
    'BING_TOPK': '1'
}

config['IMAGES'] = {
    'IMAGES_PER_PROMPT': '1'
}


config['KN'] = {
    'kn_name':'Unicom_KB_APP',
    'KN_RAW_TOPK': '10',
    'KN_FINE_TOPK': '3',
    'KN_THRESHOLD': '0.6',
    'KN_EXTEND': '0',
    'KN_EXTENDED_SIZE': '400'
}


config['function'] = {
    'tools': tools,
    'func_tools': func_tools
}


# 写入配置文件
with open('config.ini', 'w') as configfile:
    config.write(configfile)



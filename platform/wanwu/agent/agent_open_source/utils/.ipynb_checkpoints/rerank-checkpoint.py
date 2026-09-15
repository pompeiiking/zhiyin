from re import sub
import requests
import json
import logging
import datetime,time
import logging
import pytz
import math
import concurrent.futures
import traceback
from utils.model_tools import *
from utils.bm25 import rerank_by_bm25
from utils.tokenizers import CustomTokenizer
from utils.llm_tools import format_prompt_template
from utils.auth import AccessTokenManager
# from utils.bing_plus import *



logger = logging.getLogger(__name__)

import configparser

config = configparser.ConfigParser()
config.read('config.ini',encoding='utf-8')

token_manager = AccessTokenManager()


BING_RESULT_LEN =  int(config["BING"]["BING_RESULT_LEN"])
BING_TOP_K =  int(config["BING"]["BING_TOP_K"])
BING_THRESHOLD =  float(config["BING"]["BING_THRESHOLD"])
BING_SENTENCE_SIZE =  int(config["BING"]["BING_SENTENCE_SIZE"])
BING_TIME_OUT =  float(config["BING"]["BING_TIME_OUT"])
TARGET_SUCCESS = int(config["BING"]["TARGET_SUCCESS"])
USE_CHROME = bool(config["BING"]["USE_CHROME"])

BING_WEIGHT =  float(config["BING"]["BING_WEIGHT"])
BOCHA_WEIGHT = float(config["BING"]["BOCHA_WEIGHT"])



MAX_INPUT_TOKENS = int(config["AGENTS"]["MAX_INPUT_TOKENS"])

def rerank_by_emb(query, raw_search_list, top_k=5, threshold = 0.4,model = "bce",sort_enable=True):
    
    if not raw_search_list:
        return {}
    
    if model =="bce":
        url  = config["MODELS"]["default_rerank_url"]
    elif model == "bge":
        url  = config["MODELS"]["rerank_url_bge_default"]
    else:
        url  = config["MODELS"]["default_rerank_url"]
    
    headers = {
        "Content_type": "application/json;charset=utf-8",
        "Authorization": f"Bearer {token_manager.get_access_token()}"
    }
    
    
    # 构造请求数据
    data = {
        "query": query,
        "raw_search_list": raw_search_list,
        "top_k": top_k,
        "threshold": threshold,
        "sort_enable":sort_enable
    }
   
    # logger.info(f"rerank request:{json.dumps(data,ensure_ascii=False)}")

    
    # 发送 POST 请求
    try:
        response = requests.post(url, headers=headers, json=data)  # 直接使用json参数发送JSON数据
        
        # 检查是否成功收到响应
        if response.status_code == 200:
            # logger.info("Request successful!")
            # 检查响应头部以确定内容类型
            if response.headers.get('Content-Type') == 'application/json':
                response_data = response.json()
                # logger.info(f"rerank response:{json.dumps(response_data,ensure_ascii=False)}")
                
                return response_data.get("result", {})
            else:
                logger.error("Response was not JSON as expected.")
                return {}
        else:
            logger.error(f"Request failed with status code: {response.status_code}")
            return {}
            
    except Exception as e:
        logger.error(f"rerank_by_emb  An error occurred: {str(e)}")
        print(str(e))
        # 返回一个空字典，保持返回值类型一致性
        return {}




# 定义并发排序函数
@advanced_timing_decorator(task_name="execute_rerank")
def execute_rerank(query, search_list, top_k=BING_TOP_K, threshold=BING_THRESHOLD, rerank_type = "emb"):
    
    if rerank_type == "emb":
        phase1_model ="bce"
        rerank_begin1 = datetime.datetime.now()
        # sub_result_by_emb =rerank_by_emb(query, results, top_k=int(top_k*1.5), threshold=threshold,model = phase1_model)
        sub_result_by_emb =rerank_by_emb(query, search_list, top_k=top_k, threshold=threshold,model = phase1_model)

        # logger.info(f"rerank_by_emb-{phase1_model}:{json.dumps(sub_result_by_emb,indent=4,ensure_ascii=False)}")
        rerank_end1 = datetime.datetime.now()
        time_difference1 = rerank_end1 - rerank_begin1    

        
        return sub_result_by_emb
    if rerank_type == "bm25":
        # rerank_begin2 = datetime.datetime.now()
        sub_result_by_bm25 = rerank_by_bm25(query, search_list, top_k=int(top_k*4), threshold=threshold)

        
        
        phase2_model ="bge"
        sub_result_by_bm25_emb= rerank_by_emb(query, sub_result_by_bm25.get('sorted_search_list',[]), top_k=top_k, threshold=threshold,model =phase2_model)

        return sub_result_by_bm25_emb



# 新增函数：合并并重排序搜索结果
@advanced_timing_decorator(task_name="hybrid_rerank_results")
def hybrid_rerank_results(query, search_list, top_k=BING_TOP_K, threshold=BING_THRESHOLD):
    """
    对搜索结果进行并行重排序并合并结果
    
    参数:
    query (str): 搜索查询
    sub_results (list): 搜索结果列表
    top_k (int): 返回的结果数量
    threshold (float): 相关性阈值
    
    返回:
    list: 重排序后的结果列表
    """

    # print(f"query:{query}\nsearch_list:{json.dumps(search_list,indent=4,ensure_ascii=False)}")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        try:
            # 并行执行两种重排序方法
            
            rerank_task_emb = executor.submit(execute_rerank, query, search_list, top_k, threshold, rerank_type="emb") 

            
            rerank_task_bm25 = executor.submit(execute_rerank, query, search_list, top_k, threshold, rerank_type="bm25")
    
            # 等待任务完成并获取结果        
            sub_result_by_emb_emb = rerank_task_emb.result()    
            sub_result_by_bm25_emb = rerank_task_bm25.result()   

            # print(f"rerank_task_emb:{json.dumps(sub_result_by_emb_emb,indent=4,ensure_ascii=False)}")

            # print(f"rerank_task_emb:{json.dumps(sub_result_by_bm25_emb,indent=4,ensure_ascii=False)}")

        except Exception as e:
            # 打印异常的详细信息
            logger.info(f"An exception occurred during concurrent execution: {e}")
            traceback.print_exc()
            # 抛出异常以确保调用者知道发生了错误
            raise
   
    # 计算两种方法的权重
    weight_num_bm25 = min(math.ceil(top_k*0.5), len(sub_result_by_bm25_emb.get('sorted_search_list',[])))
    weight_num_emb = math.ceil(top_k*0.9)
    
    # 合并两种方法的结果
    sub_aggregated_results = merge_lists_by_id2(
        sub_result_by_emb_emb.get('sorted_search_list',[])[:weight_num_emb],
        sub_result_by_bm25_emb.get('sorted_search_list',[])[:weight_num_bm25]
    )
    
    return sub_aggregated_results[:top_k] if sub_aggregated_results else []    

def merge_lists_by_id2(list1, list2):
    # 创建一个合并后的列表用于存储结果
    merged_list = []
    # 使用字典来存储已添加的元素，根据 id 去重
    added_ids = set()
    
    merged_list.extend(list1)
    added_ids = {item["link"] for item in list1 }
    # print(added_ids)
    for item in list2:
        # print(item["id"])
        if item["link"] not in added_ids:
            merged_list.append(item)

    return merged_list   



if __name__ == "__main__":
    



    search_list = [
        {
            "id": "62bc33e8057f47f4a4f1c9bb32e3abce",
            "title": "奖牌统计 - 2024年巴黎奥运会奖牌榜 - Olympics.com",
            "snippet": "查看2024年巴黎奥运会的奖牌统计，包括金、银、铜奖牌得主的国家和数量。美利坚合众国、中国、日本等国家领跑奖牌榜，法国、英国、德国等国家也有不错的表现。",
            "link": "https://olympics.com/zh/paris-2024/medals",
            "datePublished": "",
            "dateLastCrawled": "2024-08-28"
        },
        {
            "id": "6d49cfcef74e4c76947fb0fed918b06d",
            "title": "奖牌榜_2024巴黎奥运会_体育_央视网(cctv.com)",
            "snippet": "查看2024年巴黎奥运会的金牌、银牌和铜牌排名，以及各国家和地区的奖牌数量和总数。中国队目前获得了两个金牌，排名第二，法国和日本分别领跑第一和第三。",
            "link": "https://sports.cctv.com/Paris2024/medal_list/index.shtml",
            "datePublished": "",
            "dateLastCrawled": "2024-08-25"
        },
        {
            "id": "e8674b8334a24bdcbc2b0a06be6461c0",
            "title": "2024巴黎奥运会_奖牌榜_网易体育",
            "snippet": "中国奖牌榜 项目奖牌榜 排名 国家/地区 金牌 银牌 铜牌 总数 1 美国 40 44 42 126 2 中国 40 27 24 91 3 日本 20 12 13 45 4 澳大利亚 18 19 16 53 5 法国 16 26 22 64 6 ...",
            "link": "https://sports.163.com/paris2024/medal",
            "datePublished": "",
            "dateLastCrawled": "2024-08-27"
        }
    ]
    query = "巴黎 奥运会 金牌 数量 排名"
    
    # gen_prompt = build_prompt_from_search_list(query,search_list)
    # print(gen_prompt)
#     top_k = 10
#     threshold = 0  # 根据实际情况调整阈值


    results = hybrid_rerank_results(query, search_list)
    print(results)


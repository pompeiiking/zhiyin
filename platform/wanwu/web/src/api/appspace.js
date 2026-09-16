import request from "@/utils/request";
const BASE_URL = '/user/api/v1'

// 生成apikey
export const createApiKey = (data)=>{
    return request({
        url: `${BASE_URL}/appspace/app/key`,
        method: 'post',
        data
    })
};
// 删除apikey
export const delApiKey = (data)=>{
    return request({
        url: `${BASE_URL}/appspace/app/key`,
        method: 'delete',
        data
    })
};
// 获取apikey列表
export const getApiKeyList = (params)=>{
    return request({
        url: `${BASE_URL}/appspace/app/key/list`,
        method: 'get',
        params
    })
};
// 获取apikey根地址
export const getApiKeyRoot = (params)=>{
    return request({
        url: `${BASE_URL}/appspace/app/url`,
        method: 'get',
        params
    })
};

//发布app
export const appPublish = (data)=>{
    return request({
        url: `${BASE_URL}/appspace/app/publish`,
        method: 'post',
        data
    })
};

//统一删除工作室应用接口
export const deleteAPP = (data)=>{
    return request({
        url: `${BASE_URL}/appspace/app`,
        method: 'delete',
        data
    })
};


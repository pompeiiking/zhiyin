import request from "@/utils/request"
const BASE_URL = '/use/model/api/v1'

/*----自定义------*/
//mcp列表
export const getList = (data)=>{
    return request({
        url: `${BASE_URL}/mcp/list`,
        method: 'get',
        params: data
    })
};

export const getDetail = (data)=>{
    return request({
        url: `${BASE_URL}/mcp`,
        method: 'get',
        params: data
    })
};

export const setDelete = (data)=>{
    return request({
        url: `${BASE_URL}/mcp`,
        method: 'delete',
        data: data
    })
};

export const getTools = (data)=>{
    return request({
        url: `${BASE_URL}/mcp/tool/list`,
        method: 'get',
        params: data
    })
};

export const setCreate = (data)=>{
    return request({
        url: `${BASE_URL}/mcp`,
        method: 'post',
        data: data
    })
};

/*---第三方mcp广场---*/
export const getPublicMcpList = (data)=>{
    return request({
        url: `${BASE_URL}/mcp/square/list`,
        method: 'get',
        params: data
    })
};
export const getPublicMcpInfo = (data)=>{
    return request({
        url: `${BASE_URL}/mcp/square`,
        method: 'get',
        params: data
    })
};
export const getRecommendsList = (data)=>{
    return request({
        url: `${BASE_URL}/mcp/square/recommend`,
        method: 'get',
        params: data
    })
};
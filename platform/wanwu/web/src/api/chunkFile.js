import request from "@/utils/request";
const BASE_URL = '/service/api'
export const uploadChunks = (data,config) => {//切片上传
    return request({
        url: `${BASE_URL}/v1/file/upload`,
        method: "post",
        headers: {"Content-Type": "application/x-www-form-urlencoded"},
        data,
        cancelToken: config,
    });
}
export const checkChunks = (data) => {//检测切片
    return request({
        url: `${BASE_URL}/v1/file/check`,
        method: "get",
        params:data,
    });
}
export const mergeChunks = (data) => {//合并切片
    return request({
        url: `${BASE_URL}/v1/file/merge`,
        method: "post",
        data
    });
}
export const clearChunks = (data) => {//清除切片
    return request({
        url: `${BASE_URL}/v1/file/clean`,
        method: "post",
        data
    });
}
export const delfile = (data) => {//清除切片
    return request({
        url: `${BASE_URL}/v1/file/delete`,
        method: "delete",
        data
    });
}
export const continueChunks = (data) => {//断点续传,获取已经上传的切片
    return request({
        url: `${BASE_URL}/v1/file/check/list`,
        method: "get",
        params:data
    });
}


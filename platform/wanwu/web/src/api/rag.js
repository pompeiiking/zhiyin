import service from "@/utils/request"
const BASE_URL = '/user/api/v1'
export const getRagInfo = (params)=>{
    return service({
        url: `${BASE_URL}/appspace/rag`,
        method: 'get',
        params
    })
}
export const updateRag = (data)=>{
    return service({
        url: `${BASE_URL}/appspace/rag`,
        method: 'put',
        data
    })
}
export const updateRagConfig = (data)=>{
    return service({
        url: `${BASE_URL}/appspace/rag/config`,
        method: 'put',
        data
    })
}
export const createRag = (data)=>{
    return service({
        url: `${BASE_URL}/appspace/rag`,
        method: 'post',
        data
    })
}
export const delRag = (data)=>{
    return service({
        url: `${BASE_URL}/appspace/rag`,
        method: 'delete',
        data
    })
}
export const ragChat = (data)=>{
    return service({
        url: `${BASE_URL}/rag/chat`,
        method: 'post',
        data
    })
}
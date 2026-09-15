import service from "@/utils/request"
const BASE_URL = '/user/api/v1'
export const createAgent = (data)=>{
    return service({
        url: `${BASE_URL}/assistant`,
        method: 'post',
        data
    })
}

export const updateAgent = (data)=>{
    return service({
        url: `${BASE_URL}/assistant`,
        method: 'put',
        data
    })
}
export const delAgent = (data)=>{
    return service({
        url: `${BASE_URL}/assistant`,
        method: 'delete',
        data
    })
}
export const getAgentInfo = (params)=>{
    return service({
        url: `${BASE_URL}/assistant`,
        method: 'get',
        params
    })
}
export const putAgentInfo = (data)=>{
    return service({
        url: `${BASE_URL}/assistant/config`,
        method: 'put',
        data
    })
}
export const createConversation = (data)=>{
    return service({
        url: `${BASE_URL}/assistant/conversation`,
        method: 'post',
        data
    })
}
export const delConversation = (data)=>{
    return service({
        url: `${BASE_URL}/assistant/conversation`,
        method: 'delete',
        data
    })
}
export const getConversationHistory = (params)=>{
    return service({
        url: `${BASE_URL}/assistant/conversation/detail`,
        method: 'get',
        params
    })
}
export const getConversationlist = (params)=>{
    return service({
        url: `${BASE_URL}/assistant/conversation/list`,
        method: 'get',
        params
    })
}
export const getActionInfo = (params)=>{
    return service({
        url: `${BASE_URL}/assistant/action`,
        method: 'get',
        params
    })
}
export const editActionInfo = (data)=>{
    return service({
        url: `${BASE_URL}/assistant/action`,
        method: 'put',
        data
    })
}
export const addActionInfo = (data)=>{
    return service({
        url: `${BASE_URL}/assistant/action`,
        method: 'post',
        data
    })
}
export const delActionInfo = (data)=>{
    return service({
        url: `${BASE_URL}/assistant/action`,
        method: 'delete',
        data
    })
}
export const enableAction = (data)=>{
    return service({
        url: `${BASE_URL}/assistant/action/enable`,
        method: 'put',
        data
    })
}
export const addWorkFlowInfo = (data)=>{
    return service({
        url: `${BASE_URL}/assistant/workflow`,
        method: 'post',
        data
    })
}
export const delWorkFlowInfo = (data)=>{
    return service({
        url: `${BASE_URL}/assistant/workflow`,
        method: 'delete',
        data
    })
}
export const enableWorkFlow = (data)=>{
    return service({
        url: `${BASE_URL}/assistant/workflow/enable`,
        method: 'put',
        data
    })
}
export const agentStream = (data)=>{
    return service({
        url: `${BASE_URL}/assistant/stream`,
        method: 'post',
        data
    })
}
export const agentTestStream = (data)=>{
    return service({
        url: `${BASE_URL}/assistant/test/stream`,
        method: 'post',
        data
    })
}
export const getAgentList = (params)=>{
    return service({
        url: `${BASE_URL}/assistant/list`,
        method: 'get',
        params
    })
}
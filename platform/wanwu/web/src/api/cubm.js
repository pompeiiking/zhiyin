import request from "@/utils/request";

/*----元景------*/
//对话列表
export const getConversationList = (data)=>{
    return request({
        url: '/use/model/api/v1/chatllm/conversation/list',
        method: 'get',
        params: data
    })
};
//创建对话
export const createConversation = (data)=>{
    return request({
        url: '/use/model/api/v1/chatllm/conversation/create',
        method: 'post',
        data
    })
};
//删除对话
export const deleteConversation = (data)=>{
    return request({
        url: '/use/model/api/v1/chatllm/conversation/delete',
        method: 'delete',
        data
    })
};
//对话详情
export const getConversationDetail = (data)=>{
    return request({
        url: '/use/model/api/v1/chatllm/conversation/detail',
        method: 'get',
        params: data
    })
};
export const addAction = (data)=>{
    return request({
        url: '/use/model/api/v1/assistant/action/create',
        method: 'post',
        data
    })
};
export const updateAction = (data)=>{
    return request({
        url: '/use/model/api/v1/assistant/action/update',
        method: 'put',
        data
    })
};
export const deleteAction = (data)=>{
    return request({
        url: '/use/model/api/v1/assistant/action/delete',
        method: 'delete',
        data
    })
};
export const getActionDetail = (data)=>{
    return request({
        url: '/use/model/api/v1/assistant/action/info',
        method: 'get',
        params: data
    })
};
export const deleteConversationHistory = (data)=>{
    return request({
        url: '/use/model/api/v1/assistant/conversation/detail/delete',
        method: 'delete',
        data
    })
};
//获取模型列表
export const getModelList= (data) => {
    return request({
        url: "/datacenter/api/v1/infer/publish/model/select",
        method: "get",
        params:data
    });
}

//AI自动生成原生应用
export const autoCreate= (data) => {
    return request({
        url: "/use/model/api/v1/assistant/auto/create",
        method: "post",
        data
    });
}


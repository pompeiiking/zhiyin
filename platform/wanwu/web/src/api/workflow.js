import request from "@/utils/request";

export const getWorkFlow = (data)=>{
    return request({
        url: '/workflow/api/workflow/get',
        method: 'get',
        params:data
    })
};
export const saveWorkFlow = (data)=>{
    return request({
        url: '/workflow/api/workflow/save',
        method: 'post',
        data
    })
};
export const runWorkFlow = (data)=>{
    return request({
        url: '/workflow/api/workflow/run',
        method: 'post',
        data
    })
};
export const getWorkFlowStatus = (data)=>{
    return request({
        url: '/workflow/api/workflow/status',
        method: 'get',
        params:data
    })
};
export const runNode = (data)=>{
    return request({
        url: '/workflow/api/node/run_api',
        method: 'post',
        data
    })
};
export const runPythonNode = (data)=>{
    return request({
        url: '/workflow/api/node/run_python',
        method: 'post',
        data
    })
};
export const getWorkFlowList = (data)=>{
    return request({
        url: '/workflow/api/workflow/list',
        method: 'get',
        params:data
    })
};
export const createWorkFlow = (data)=>{
    return request({
        url: '/workflow/api/workflow/create',
        method: 'post',
        data
    })
};
export const copyExample = (data)=>{
    return request({
        url: '/workflow/api/workflow/example_clone',
        method: 'post',
        data
    })
};
export const deleteWorkFlow = (data)=>{
    return request({
        url: '/workflow/api/workflow/delete',
        method: 'delete',
        data
    })
};
export const publishWorkFlow = (data)=>{
    return request({
        url: '/workflow/api/plugin/api/publish',
        method: 'post',
        data
    })
};
//复制
export const copyWorkFlow = (data)=>{
    return request({
        url: '/workflow/api/workflow/clone',
        method: 'post',
        data
    })
};
//chakan
export const readWorkFlow = (data)=>{
    return request({
        url: '/workflow/api/workflow/openapi_schema',
        method: 'get',
        params:data
    })
};

export const getModels = (data)=>{
    return request({
        url: '/user/api/v1/model/select/llm',
        method: 'get',
        params: data
    })
};

export const getRerankModels = (data)=>{
    return request({
        url: '/user/api/v1/model/select/rerank',
        method: 'get',
        params: data
    })
};

export const getAppList = (data) => {
    return request({
        url: "/bffservice/v2/app/list",
        method: "get",
        params:data,
    });
};

export const getStaticToken = (data) => {
    return request({
        url: "/workflow/api/workflow/static_token",
        method: "get",
        params:data,
    });
};


export const externalUpload = (data, config) => {
    return request({
        // url: "/proxyupload/upload",
        url:"/service/api/v1/proxy/file/upload",
        method: "post",
        data,
        config,
        isHandleRes: false
    });
};

export const getMcpToolList = (data) => {
    return request({
        url: "/use/model/api/v1/mcp/tool/list",
        method: "get",
        params: data,
    });
};

export const getList = (data)=>{
    return request({
        url: '/use/model/api/v1/mcp/select',
        method: 'get',
        params: data
    })
};
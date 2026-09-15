import service from "@/utils/request";

//获取文档知识分类
// export const getDocList = (data) => {
//     return service({
//         url: `/konwledgeServe/v1/ux/doccategory/list`,
//         method: "get",
//         data: data,
//     });
// };

//新增文档知识分类
export const createDoc = (data) => {
    return service({
        url: "/konwledgeServe/v1/ux/doccategory",
        method: "post",
        data: data,
    });
};

//修改文档知识分类
export const editDoc = (data) => {
    return service({
        url: "/konwledgeServe/v1/ux/doccategory",
        method: "put",
        data: data,
    });
};

//删除文档知识分类
export const removeDoc = (data) => {
    return service({
        url: "/konwledgeServe/v1/ux/doccategory",
        method: "delete",
        data: data,
    });
};

//获取文档列表
export const getList = (data) => {
    return service({
        url: "/konwledgeServe/v1/ux/doc/list",
        method: "post",
        data: data,
    });
};
//编辑文档
export const modifyDoc = (data) => {
    return service({
        url: "/konwledgeServe/v1/ux/doc",
        method: "put",
        data: data,
    });
};
//删除文档
export const deleteDoc = (data) => {
    return service({
        url: "/konwledgeServe/v1/ux/doc",
        method: "delete",
        data: data,
    });
};
//上传文档
export const importDoc = (data,source) => {
    return service({
        url: "/konwledgeServe/v1/ux/doc/import",
        method: "post",
        cancleToken:source,
        data: data,
        headers: {"Content-Type": "multipart/form-data"}
    });
};
//保存上传文档
export const saveImportDoc = (data) => {
    return service({
        url: "/konwledgeServe/v1/ux/doc/save",
        method: "put",
        data: data,
    });
};
//获取文档下载链接
export const getDocLink = (id) => {
    return service({
        url: `/konwledgeServe/v1/ux/doc/download_url?id=${id}`,
        method: "get"
    });
};
//下载文档
export const downDoc = (url) => {
    return service({
        url: `/konwledgeServe${url}`,
        method: "get",
        responseType: 'blob'
    });
};
//命中测试
export const test = (data) => {
    return service({
        url: `/konwledgeServe/v1/ux/chunk/evaluate`,
        method: "post",
        data: data
    });
}
//上传文件删除无效数据
export const deleteInvalid = (data) => {
    return service({
        url: `/konwledgeServe/v1/ux/doc/invalid`,
        method: "delete",
        data: data
    });
}
//从url上传
export const setUploadURL = (data)=>{
    return service({
        url: '/konwledgeServe/v1/ux/doc/importUrl',
        method: 'post',
        data
    })
};
// 解析url
export const analyzeURL = (data)=>{
    return service({
        url: '/konwledgeServe/v1/ux/doc/analysisUrl',
        method: 'post',
        data
    })
};

// 查看分段结果列表
export const getContentList = (data,config)=>{
    return service({
        url: '/konwledgeServe/v1/ux/doc/fileSplit',
        method: 'post',
        data: data,
        // config
    })
};

// 查看分段结果列表
export const setStatus = (data,config)=>{
    return service({
        url: '/konwledgeServe/v1/ux/doc/updateFileStatus',
        method: 'post',
        data: data,
        // config
    })
};

// url上传批量
export const batchurl = (data,source)=>{
    return service({
        url: '/konwledgeServe/v1/ux/doc/analysisBatchUrl',
        method: 'post',
        data: data,
        cancelToken: source,
        headers: {"Content-Type": "multipart/form-data"}
    })
};
export const batchUrlTaskStatus = (data)=>{
    return service({
        url: '/konwledgeServe/v1/ux/doc/batchUrlTaskStatus',
        method: 'get',
        params: data
    })
};
export const importBatchUrl = (data)=>{
    return service({
        url: '/konwledgeServe/v1/ux/doc/importBatchUrl',
        method: 'get',
        params: data
    })
};
export const BatchUrlDemo = ()=>{
    return service({
        url: '/konwledgeServe/v1/ux/doc/downloadDemoFile',
        method: 'get'
    })
};


//new 获取知识库列表
const BASE_URL = '/user/api/v1'
export const getKnowledgeList = (params)=>{
    return service({
        url: `${BASE_URL}/knowledge/select`,
        method: 'get',
        params
    })
};
export const delKnowledgeItem = (data)=>{
    return service({
        url: `${BASE_URL}/knowledge`,
        method: 'delete',
        data
    })
};
export const createKnowledgeItem = (data)=>{
    return service({
        url: `${BASE_URL}/knowledge`,
        method: 'post',
        data
    })
};
export const editKnowledgeItem = (data)=>{
    return service({
        url: `${BASE_URL}/knowledge`,
        method: 'put',
        data
    })
};
export const getDocList = (params)=>{
    return service({
        url: `${BASE_URL}/knowledge/doc/list`,
        method: 'get',
        params
    })
};
export const delDocItem = (data)=>{
    return service({
        url: `${BASE_URL}/knowledge/doc`,
        method: 'delete',
        data
    })
};
// 上传文件提示接口
export const uploadFileTips = (params)=>{
    return service({
        url: `${BASE_URL}/knowledge/doc/import/tip`,
        method: 'get',
        params
    })
};
export const getSectionList = (params)=>{
    return service({
        url: `${BASE_URL}/knowledge/doc/segment/list`,
        method: 'get',
        params
    })
};
export const setSectionStatus = (data)=>{
    return service({
        url: `${BASE_URL}/knowledge/doc/segment/status/update`,
        method: 'post',
        data
    })
};

export const setAnalysis = (data)=>{
    return service({
        url: `${BASE_URL}/knowledge/doc/url/analysis`,
        method: 'post',
        data
    })
};

export const docImport = (data)=>{
    return service({
        url: `${BASE_URL}/knowledge/doc/import`,
        method: 'post',
        data
    })
};
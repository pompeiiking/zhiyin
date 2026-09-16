import service from "@/utils/request"
const BASE_URL = '/user/api/v1'

// 获取列表
export const fetchModelList = (params) => {
    return service({
        url: `${BASE_URL}/model/list`,
        method: "get",
        params,
    })
}

// 获取单个模型
export const getModelDetail = (params) => {
    return service({
        url: `${BASE_URL}/model`,
        method: "get",
        params,
    })
}

// 创建
export const addModel = (data) => {
    return service({
        url: `${BASE_URL}/model`,
        method: "post",
        data
    })
}
// 编辑
export const editModel = (data) => {
    return service({
        url: `${BASE_URL}/model`,
        method: "put",
        data
    })
}
// 删除
export const deleteModel = (data) => {
    return service({
        url: `${BASE_URL}/model`,
        method: "delete",
        data,
    })
}
// 修改状态
export const changeModelStatus = (data) => {
    return service({
        url: `${BASE_URL}/model/status`,
        method: "put",
        data,
    })
}

//获取embedding列表
export const getEmbeddingList = (params) => {
    return service({
        url: `${BASE_URL}/model/select/embedding`,
        method: "get",
        params,
    })
}

//获取rerank模型列表
export const getRerankList = () => {
    return service({
        url: `${BASE_URL}/model/select/rerank`,
        method: "get"
    })
}

//获取下来选择模型列表
export const selectModelList = () => {
    return service({
        url: `${BASE_URL}/model/select/llm`,
        method: "get"
    })
}
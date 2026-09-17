import service from "@/utils/request"
const BASE_URL = '/user/api/v1'

// 获取组织列表
export const fetchOrgList = (params) => {
    return service({
        url: `${BASE_URL}/org/list`,
        method: "get",
        params,
    })
}
// 获取组织详情
export const fetchOrgDetail = (params) => {
    return service({
        url: `${BASE_URL}/org/info`,
        method: "get",
        params,
    })
}
// 创建组织
export const createOrg = (data) => {
    return service({
        url: `${BASE_URL}/org`,
        method: "post",
        data,
    })
}
// 编辑组织
export const editOrg = (data) => {
    return service({
        url: `${BASE_URL}/org`,
        method: "put",
        data,
    })
}
// 删除组织
export const deleteOrg = (data) => {
    return service({
        url: `${BASE_URL}/org`,
        method: "delete",
        data,
    })
}
// 修改组织状态
export const changeOrgStatus = (data) => {
    return service({
        url: `${BASE_URL}/org/status`,
        method: "put",
        data,
    })
}

// 获取导航组织列表
export const fetchOrgs = () => {
    return service({
        url: `${BASE_URL}/org/select`,
        method: "get",
    })
}
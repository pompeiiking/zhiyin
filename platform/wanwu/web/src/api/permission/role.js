import service from "@/utils/request"
const BASE_URL = '/user/api/v1'

// 获取角色列表
export const fetchRoleList = (params) => {
    return service({
        url: `${BASE_URL}/role/list`,
        method: "get",
        params,
    })
}
// 获取角色详情
export const fetchRoleDetail = (params) => {
    return service({
        url: `${BASE_URL}/role/info`,
        method: "get",
        params,
    })
}
// 创建角色
export const createRole = (data) => {
    return service({
        url: `${BASE_URL}/role`,
        method: "post",
        data,
    })
}
// 编辑角色
export const editRole = (data) => {
    return service({
        url: `${BASE_URL}/role`,
        method: "put",
        data,
    })
}
// 删除角色
export const deleteRole = (data) => {
    return service({
        url: `${BASE_URL}/role`,
        method: "delete",
        data,
    })
}
// 修改角色状态
export const changeRoleStatus = (data) => {
    return service({
        url: `${BASE_URL}/role/status`,
        method: "put",
        data,
    })
}
// 获取权限树
export const fetchPermTree = () => {
    return service({
        url: `${BASE_URL}/role/template`,
        method: "get",
    })
}

import service from "@/utils/request"
const BASE_URL = '/user/api/v1'

// 获取用户列表
export const fetchUserList = (params) => {
    return service({
        url: `${BASE_URL}/user/list`,
        method: "get",
        params,
    })
}
// 获取用户详情
export const fetchUserDetail = (params) => {
    return service({
        url: `${BASE_URL}/user/info`,
        method: "get",
        params,
    })
}
// 获取角色列表用户
export const fetchRoleList = () => {
    return service({
        url: `${BASE_URL}/role/select`,
        method: "get",
    })
}
// 创建用户
export const createUser = (data) => {
    return service({
        url: `${BASE_URL}/user`,
        method: "post",
        data,
    })
}
// 编辑用户
export const editUser = (data) => {
    return service({
        url: `${BASE_URL}/user`,
        method: "put",
        data,
    })
}
// 删除用户
export const deleteUser = (data) => {
    return service({
        url: `${BASE_URL}/user`,
        method: "delete",
        data,
    })
}
// 修改用户状态
export const changeUserStatus = (data) => {
    return service({
        url: `${BASE_URL}/user/status`,
        method: "put",
        data,
    })
}
// 获取邀请用户时的用户列表
export const fetchInviteUser = (params) => {
    return service({
        url: `${BASE_URL}/org/other/select`,
        method: "get",
        params,
    })
}
// 邀请用户
export const inviteUser = (data) => {
    return service({
        url: `${BASE_URL}/org/user`,
        method: "post",
        data,
    })
}

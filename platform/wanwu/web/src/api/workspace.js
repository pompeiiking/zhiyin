import service from "@/utils/request"

export const getAppSpaceList = (params)=>{
    return service({
        url: '/user/api/v1/appspace/app/list',
        method: 'get',
        params
    })
}

export const deleteApp = (data)=>{
    return service({
        url: '/workflow/api/app/delete',
        method: 'delete',
        data
    })
}
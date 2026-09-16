import service from "@/utils/request"
const BASE_URL = '/user/api/v1'

export const getHistoryList = ()=>{
    return service({
        url: `${BASE_URL}/exploration/app/history`,
        method: 'get',
    })
}
export const setFavorite = (data)=>{
    return service({
        url: `${BASE_URL}/exploration/app/favorite`,
        method: 'post',
        data
    })
}
export const getExplorList = (params)=>{
    return service({
        url: `${BASE_URL}/exploration/app/list`,
        method: 'get',
        params
    })
}
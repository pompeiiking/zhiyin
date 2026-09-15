import service from "@/utils/request";
const hasLang = true
const BASE_URL = '/user/api/v1'

// 登录
export const login = (data) => {
    return service({
        url: `${BASE_URL}/base/login`,
        method: "post",
        data,
        hasLang
    });
};

// 获取图形验证码
export const getImgVerCode = () => {
    return service({
        url: `${BASE_URL}/base/captcha`,
        method: "get",
        hasLang
    });
};

export const getLangList = () => {
    return service({
        url: `${BASE_URL}/base/language/select`,
        method: "get",
    });
};


export const changeLang = (data) => {
    return service({
        url: `${BASE_URL}/user/language`,
        method: "put",
        data
    });
};

export const getUserDetail = (data) => {
    return service({
        url: `${BASE_URL}/user/info`,
        method: "get",
        params:data,
    });
};

export const getPermission = (data) => {
    return service({
        url: `${BASE_URL}/user/permission`,
        method: "get",
        params:data
    });
};

export const restUserPassword= (data) => {
    return service({
        url: `${BASE_URL}/user/admin/password`,
        method: "put",
        data,
    });
};
export const restOwnPassword= (data) => {
    return service({
        url: `${BASE_URL}/user/password`,
        method: "put",
        data,
    });
};

export const docDownload = () => {
    return service({
        url: `${BASE_URL}/doc_center`,
        method: "get",
    });
};

// 公用上传 avatar
export const uploadAvatar = (data, config) => {
    return service({
        url: `${BASE_URL}/avatar`,
        method: "post",
        data,
        config
    })
}

// 平台信息
export const getCommonInfo= () => {
    return service({
        url: `${BASE_URL}/base/custom`,
        method: "get",
        hasLang
    });
}
import Vue from 'vue'
import VueRouter from 'vue-router'
import { PERMS } from "./constants"
import { basePath } from "@/utils/config"

const routerPush = VueRouter.prototype.push;
VueRouter.prototype.push = function(location){
    return routerPush.call(this,location).catch(err=>{})
}

Vue.use(VueRouter)

const orgPermission = localStorage.getItem('access_cert')
    ? JSON.parse(localStorage.getItem('access_cert')).user.permission.orgPermission
    : []

const constantRoutes = [
    {
        path: '/',
    },
    {
        path: '/portal',
        name: 'portal',
        component:resolve =>require(['@/views/layout'],resolve),
        children:[
            {
                path: '/404',
                name: '404',
            },
            {
                path: '/userInfo',
                component:resolve =>require(['@/views/userCenter/components/info'],resolve),
            },
            {
                path: '/permission',
                component:resolve =>require(['@/views/permission'],resolve),
                meta:{perm: [PERMS.PERMISSION]},
            },
            {
                path: '/modelAccess',
                component:resolve =>require(['@/views/modelAccess'],resolve),
                meta:{perm: [PERMS.MODEL]},
            },
            {
                path: '/mcp',
                component:resolve => require(['@/views/mcpManagement'],resolve),
                meta:{perm: [PERMS.MCP]},
            },
            {
                path: '/mcp/detail/:type',
                component:resolve =>require(['@/views/mcpManagementPublic/detail'],resolve),
                meta:{perm: [PERMS.MCP]},
            },
            {
                path: '/explore',
                component:resolve =>require(['@/views/ExploreSquare'],resolve),
                meta:{perm: [PERMS.EXPLORE]},
            },
            {
                path: '/explore/agent',
                component:resolve =>require(['@/views/agent'],resolve),
                meta:{perm: [PERMS.EXPLORE]},
            },
            {
                path: '/explore/rag',
                component:resolve =>require(['@/views/rag'],resolve),
                meta:{perm: [PERMS.EXPLORE]},
            },
            {
                path: '/agent/test',
                component:resolve =>require(['@/views/agent/components/form'],resolve),
                meta:{perm: [PERMS.AGENT]},
            },
            {
                path: '/rag/test',
                component:resolve =>require(['@/views/rag/components/form'],resolve),
                meta:{perm: [PERMS.RAG]},
            },
            {
                path: '/workflow',
                component:resolve =>require(['@/views/workflow'],resolve),
                meta:{perm: [PERMS.WORKFLOW]},
            },
            {
                path: '/appSpace/:type',
                component:resolve =>require(['@/views/appSpace'],resolve),
                meta:{perm: [PERMS.RAG, PERMS.AGENT, PERMS.WORKFLOW]},
            },
            {
                path: '/knowledge',
                component:resolve =>require(['@/views/knowledge'],resolve),
                meta:{perm: [PERMS.KNOWLEDGE]},
            },
            {
                path: '/knowledge/doclist/:id',
                component:resolve =>require(['@/views/knowledge/component/doclist.vue'],resolve),
                meta:{perm: [PERMS.KNOWLEDGE]},
            },
             {
                path: '/knowledge/fileUpload',
                component:resolve =>require(['@/views/knowledge/component/fileUpload.vue'],resolve),
                meta:{perm: [PERMS.KNOWLEDGE]},
            },
            {
                path: '/knowledge/section',
                component:resolve =>require(['@/views/knowledge/component/section.vue'],resolve),
                meta:{perm: [PERMS.KNOWLEDGE]},
            },
            {
                path: '/userCenter/*',
                name:'userCenter',
                component:resolve =>require(['@/views/userCenter'],resolve),
            },
        ]
    },
    {
        path: '/portal/*',
        name:'portalWithoutParams',
        component:resolve =>require(['@/views/layout'],resolve),
    },
    {
        path: '/portal/:path(.*)',
        name:'portalWithParams',
        component:resolve =>require(['@/views/layout'],resolve),
    },
    {
        path: '/login',
        component:resolve =>require(['@/views/login'],resolve),
    },
    {
        path: '/:catchAll(.*)',
        redirect: "/"
    }
]


// 判断是否有权限
const hasPermission = (perm, route) => {
    if (!Array.isArray(perm)) return false
    if (route.meta && route.meta.perm) {
        return route.meta.perm.some(role => perm.includes(role))
    } else {
        return true
    }
}
// 把有权限的路由重新组合
const filterAsyncRoutes = (routes, perm) => {
    const res = []

    routes.forEach(route => {
        const tmp = { ...route }
        if (hasPermission(perm, tmp)) {
            if (tmp.children) {
                tmp.children = filterAsyncRoutes(tmp.children, perm)
                if (tmp.children.length && !tmp.redirect) tmp.redirect = tmp.children[0].path
            }
            res.push(tmp)
        }
    })
    return res
}

const baseConfig = {
    mode: 'history',
    base: basePath + '/aibase',//process.env.BASE_URL,
    scrollBehavior (to, from, savedPosition) {
        return { x: 0, y: 0 }
    },
}

let router = new VueRouter({
    ...baseConfig,
    routes: filterAsyncRoutes(constantRoutes, orgPermission)
})

export const replaceRouter = (permission) => {
    // 创建新的 Router 实例
    const newRouter = new VueRouter({
        ...baseConfig,
        routes: filterAsyncRoutes(constantRoutes, permission), // 使用新的路由配置
    })

    // 替换现有的路由器
    router.matcher = newRouter.matcher
}

export default router

import Vue from 'vue'
import Vuex from 'vuex'
import VuexPersistence from 'vuex-persist'
import { user } from '@/store/module/user'
import { app } from './module/app'
import { workflow } from './module/workflow'


Vue.use(Vuex)
// 用户信息持久化
const vuexLocal = new VuexPersistence({
    key:'access_cert',
    storage: window.localStorage,
    modules: ['user']
})

export const store = new Vuex.Store({
    modules: {
        user,
        app,
        workflow
    },
    plugins: [vuexLocal.plugin]
})

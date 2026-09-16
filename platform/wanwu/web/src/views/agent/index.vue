<template>
    <CommonLayout
    :aside-title="asideTitle" 
    :isButton="true"
    @handleBtnClick="handleBtnClick"
    :isBtnDisabled="sessionStatus === 0"
  >
    <template #aside-content>
      <div class="explore-aside-app">
        <div v-for="n in historyList " class="appList" 
        :class="['appList',{'disabled':sessionStatus === 0},{'active':n.active}]"
        @click="historyClick(n)"  
        @mouseenter="mouseEnter(n)"
        @mouseleave="mouseLeave(n)">
           <span class="appName">
                <span class="appTag"></span>
                {{n.title}}
            </span>
            <span class="el-icon-delete appDelete" v-if="n.hover || n.active" @click.stop="deleteConversation(n)"></span>
        </div>
      </div>
    </template>
    <template #main-content>
      <div class="app-content">
        <Chat :chatType="'chat'" :editForm="editForm"  ref="agentChat" @reloadList="reloadList" @setHistoryStatus="setHistoryStatus"/>
      </div>
    </template>
  </CommonLayout>
</template>
<script>
import CommonLayout from '@/components/exploreContainer.vue'
import Chat from './components/chat.vue'
 import {mapGetters} from 'vuex'
 import { getAgentInfo } from "@/api/agent";
import sseMethod from '@/mixins/sseMethod'
import { getConversationlist} from "@/api/agent";
export default {
    components: {CommonLayout,Chat },
    mixins: [sseMethod],
    data(){
        return {
            asideTitle:'新建对话',
            assistantId:'',
            historyList:[],
            editForm:{
                assistantId:'',
                avatar:{},
                name:'',
                desc:'',
                prologue:''
            },
        }
    },
    computed: {
        ...mapGetters('app', ['sessionStatus'])
    },
    created(){
        if(this.$route.query.id){
            this.assistantId = this.$route.query.id
            this.editForm.assistantId = this.$route.query.id;
            this.getDetail()
            this.getList()
        }
    },
    methods:{
      reloadList(val){
        this.getList(val)
      },
      getDetail(){
            getAgentInfo({assistantId:this.editForm.assistantId}).then(res =>{
                if(res.code === 0){
                    this.editForm.avatar = res.data.avatar;
                    this.editForm.name = res.data.name;
                    this.editForm.desc = res.data.desc;
                    this.editForm.prologue = res.data.prologue;
                }
            })
        },
        getList(noInit){
            getConversationlist({assistantId:this.assistantId,pageNo:1,pageSize:1000}).then(res =>{
                if(res.code === 0){
                    if(res.data.list && res.data.list.length > 0){
                        this.historyList = res.data.list.map(n =>{
                            return {...n, hover: false, active: false}
                        })
                        if (noInit) {
                            this.historyList[0].active = true  //noInit 是true时，左侧默认选中第一个,但是不要调接口刷新详情
                        } else {
                            this.historyClick[this.historyList[0]]
                        }
                    }else{
                        this.historyList = []
                    }
                }else{
                    this.historyList = []
                }
            })
        },
        setHistoryStatus(){
            this.historyList.forEach(m => {
                m.active = false
            })
        },
        historyClick(n){//切换对话
            n.hover = true;
            this.$refs['agentChat'].conversionClick(n)
        },
        deleteConversation(n){
            this.$refs['agentChat'].preDelConversation(n)
        },
        handleBtnClick(){//新建对话
            this.$refs['agentChat'].createConversion()
        },
         async doDeleteHistory(){//删除历史记录
            let res = await deleteConversationHistory({conversationId:this.conversationId})
            if(res.code === 0){
                this.$message.success(this.$t('yuanjing.deleteTips'))
            }
        },
        mouseEnter(n){
            n.hover = true;
        },
        mouseLeave(n){
            n.hover = false;
        }
    }
}
</script>
<style lang="scss" scoped>
@import '@/style/chat.scss';
.active{
    background-color: $color_opacity !important;
    .appTag{
        background-color: #384BF7!important;
    }
}
.explore-aside-app{
    .appList:hover{
        background-color: $color_opacity !important;
    }
    .appList{
        margin:10px 20px;
        padding:10px;
        border-radius: 6px;
        margin-bottom: 6px;
        display: flex;
        gap: 8px;
        align-items: center;
        justify-content:space-between;
        cursor: pointer;
        position:relative;
        .appDelete{
            color:#384BF7;
            margin-right:-5px;
            cursor: pointer;
        }
        .appName{
            display: block;
            max-width: 130px;
            overflow: hidden;
            white-space: nowrap;
            pointer-events: none;
            text-overflow: ellipsis;
            .appTag{
                display:inline-block;
                width:8px;
                height:8px;
                border-radius:50%;
                background:#ccc;
            }
      }
    }
}
 .app-content{
    width:100%;
    height:100%;
 }
</style>
<template>
    <!-- 远景大模型 -->
    <div class="full-content flex">
        <el-main class="scroll">
            <div class="smart-center">
                <!--基础配置回显-->
                <div v-show="echo" class="session rl echo">
                    <Prologue  :editForm="editForm" @setProloguePrompt="setProloguePrompt" :isBigModel="true" />
                </div>
                <!--对话-->
                <div v-show="!echo" class="center-session">
                    <SessionComponentSe
                            ref="session-com"
                            class="component"
                            :sessionStatus="sessionStatus"
                            @clearHistory="clearHistory"
                            @refresh="refresh"
                            @queryCopy="queryCopy"
                            :defaultUrl="editForm.avatar.path"
                    />
                </div>
                <!--输入框-->
                <div class="center-editable">
                    <div v-show="stopBtShow" class="stop-box">
                        <span v-show="sessionStatus === 0" class="stop" @click="preStop">
                            <img class="stop-icon mdl" :src="require('@/assets/imgs/stop.png')"/>
                            <span class="mdl">{{$t('agent.stop')}}</span>
                        </span>
                        <span v-show="sessionStatus !== 0" class="stop" @click="refresh">
                            <img class="stop-icon mdl" :src="require('@/assets/imgs/refresh.png')"/>
                            <span class="mdl">{{$t('agent.refresh')}}</span>
                        </span>
                    </div>
                    <EditableDivV3
                            ref="editable"
                            source="perfectReminder"
                            :fileTypeArr="fileTypeArr"
                            :currentModel="currentModel"
                            :isModelDisable="isModelDisable"
                            :showModelSelect="false"
                            @preSend="preSend"
                            @modelChange="modelChange"
                            @setSessionStatus="setSessionStatus"
                    />
                </div>
            </div>
        </el-main>
    </div>
</template>

<script>
    import SessionComponentSe from './SessionComponentSe'
    import EditableDivV3 from './EditableDivV3'
    import {delConversation,createConversation,getConversationHistory} from "@/api/agent";
    import Prologue from './Prologue'
    import sseMethod from '@/mixins/sseMethod'
    import {md} from '@/mixins/marksown-it'
    import {mapActions, mapGetters} from 'vuex'

    export default {
        props:{
            editForm:{
                type:Object,
                default:null
            },
            chatType:{
                type:String,
                default:''
            }
        },
        components: {
            SessionComponentSe,
            EditableDivV3,
            Prologue
        },
        mixins: [sseMethod],
        computed: {
            ...mapGetters('app', ['sessionStatus']),
            ...mapGetters('menu', ['basicInfo']),
            ...mapGetters('user', ['commonInfo']),
        },
        data() {
            return {
                amswerNum:0,
                isModelDisable:false,
                currentModel:null,
                echo: true,
                fileTypeArr: ['doc/*'],
                hasDrawer: false,
                drawer: true,
            }
        },
        methods: {
            createConversion(){
                if (this.echo) {
                    this.$message({
                        type: 'info',
                        message: '已切换最新会话',
                        customClass: 'dark-message',
                        iconClass: 'none',
                        duration: 1500
                    })
                    return
                }
                this.conversationId = ''
                this.echo = true
                this.clearPageHistory()
                this.$emit('setHistoryStatus')
            },
            //切换对话
            conversionClick(n) {
                // this.isModelDisable = true;
                if (this.sessionStatus === 0) {
                    //this.$message.warning('上个问题未答完')
                    return
                }else{
                    this.stopBtShow = false
                }

                this.$emit('setHistoryStatus')
                this.amswerNum = 0
                n.active = true
                this.clearPageHistory()
                this.echo = false
                this.conversationId = n.conversationId
                this.getConversationDetail(this.conversationId,true)
            },
            async getConversationDetail(id,loading){
                loading && this.$refs['session-com'].doLoading()
                let res = await getConversationHistory({conversationId: id, pageSize: 1000, pageNo: 1})
                if (res.code === 0) {
                    let history = res.data.list ? res.data.list.map(n => {
                        return {
                            ...n,
                            query: n.prompt,
                            response:[0,1,2,3,4,5,6,20,21,10].includes(n.qa_type)?md.render(n.response):n.response.replaceAll('\n-','\n•'),
                            oriResponse:n.response,
                            searchList: n.searchList ? n.searchList : [],
                            filepath: n.responseFileUrls,
                            "gen_file_url_list":n.responseFileUrls || [],
                            "isOpen":true
                        }
                    }) : []
                    this.$refs['session-com'].replaceHistory(history)
                    this.$nextTick(()=>{
                        this.addCopyClick()
                    })
                }
            },
            //删除对话
            async preDelConversation(n) {
                if (this.sessionStatus === 0) {
                    //this.$message.warning('上个问题未答完')
                    return
                }
                let res = await delConversation({conversationId: n.conversationId})
                if (res.code === 0) {
                    this.$emit('reloadList')
                    if(this.conversationId === n.conversationId){
                        this.conversationId = ''
                        this.$refs['session-com'].clearData()
                    }
                    this.echo = true
                }
            },
            /*------会话------*/
            async preSend(val,fileId,fileInfo) {
                this.inputVal = val || this.$refs['editable'].getPrompt()
                this.fileId = fileId || null;
                this.isTestChat = this.chatType === 'test' ? true :false;
                const file_List = this.$refs['editable'].getFileList();
                this.fileList = file_List.length > 0 ? file_List : fileInfo || []
                if (!this.inputVal) {
                    this.$message.warning('请输入内容');
                    return
                }
                if (!this.verifiyFormParams()) {
                    return;
                }
                //如果是新会话，先创建
                if (!this.conversationId && this.chatType === 'chat') {
                    let res = await createConversation({prompt: this.inputVal,assistantId:this.editForm.assistantId})
                    if (res.code === 0) {
                        this.conversationId = res.data.conversationId
                        this.$emit('reloadList',true)
                        this.setParams()
                    }
                } else {
                    this.setParams()
                }
            },
            verifiyFormParams(){
                if (this.chatType === 'chat') return true;
                const conditions = [
                    { check: !this.editForm.modelParams, message: '请选择模型' },
                    { check: !this.editForm.prologue, message: '请输入开场白' }
                ];
                for (const condition of conditions) {
                    if (condition.check) {
                    this.$message.warning(condition.message);
                    return false;
                    }
                }
                if(this.editForm.knowledgeBaseIds.length > 0){
                    if(!this.editForm.rerankParams){
                        this.$message.warning('请选择rerank模型');
                        return false;
                    }
                }
                return true;
            },
            modelChange(){//切换模型新建对话
                this.preCreateConversation()
            },
            setParams() {
                ++this.amswerNum;
                if(this.amswerNum > 0){
                    this.isModelDisable = true
                }
                let fileId = this.$refs['editable'].getFileIdList() || this.fileId;
                this.useSearch = this.$refs['editable'].sendUseSearch();
                this.setSseParams({conversationId: this.conversationId, fileInfo:fileId,assistantId:this.editForm.assistantId})
                this.doSend()
                this.echo = false
            },
            /*--右侧提示词--*/
            showDrawer() {
                this.drawer = true
            },
            hideDrawer() {
                this.drawer = false
            },
            async getReminderList(cb) {
                let res = await getTemplateList({pageNo:0,pageSize:0,title:''})
                if (res.code === 0) {
                    this.reminderList = res.data.list||[]
                    cb && cb()
                    console.log(new Date().getTime())
                }
            },
            reminderClick(n) {
                this.$refs['editable'].setPrompt(n.prompt)
            }
        }
    }
</script>

<style lang="scss" scoped>
@import '@/style/chat.scss';
</style>

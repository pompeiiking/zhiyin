<template>
  <div class="agent-from-content">
    <div class="form-header">
      <div class="header-left">
        <span class="el-icon-arrow-left btn" @click="goBack"></span>
        <span class="header-left-title">智能体编辑</span>
      </div>
      <div class="header-right">
          <div class="header-api">
            <el-tag  effect="plain" class="root-url">API根地址</el-tag>
            {{apiURL}}
          </div>
          <el-button size="small" @click="openApiDialog" class="apikeyBtn">
            <img :src="require('@/assets/imgs/apikey.png')" />
            API秘钥
          </el-button>
          <el-button size="small" type="primary" @click="handlePublish" style="padding:13px 12px;">发布<span class="el-icon-arrow-down" style="margin-left:5px;"></span></el-button>
          <div class="popover-operation" v-if="showOperation">
            <div>
              <el-radio :label="'private'" v-model="scope">私密发布：仅自己可见</el-radio>
            </div>
            <div>
              <el-radio :label="'public'" v-model="scope">公开发布：组织内可见</el-radio>
            </div>
            <div class="saveBtn">
              <el-button size="mini" type="primary" @click="savePublish">保 存</el-button>
            </div>
          </div>
      </div>
    </div>
    <div class="agent_form">
      <div class="drawer-form" v-if="!showActionConfig">
        <div class="block prompt-box">
          <div class="basicInfo">
            <div class="img">
              <img :src="editForm.avatar.path ? `/user/api`+ editForm.avatar.path : '@/assets/imgs/bg-logo.png'" />
            </div>
            <div>
              <span class="basicInfo-title">{{editForm.name || '无信息'}}</span>
              <span class="el-icon-edit-outline editIcon" @click="editAgent"></span>
              <p>{{editForm.desc || '无信息'}}</p>
            </div>
          </div>
        </div>
        <div class="agnetSet">
          <h3 class="labelTitle">智能体配置</h3>
          <div class="block prompt-box">
            <p class="block-title model-title">
              <span class="label">
                <img :src="require('@/assets/imgs/require.png')" class="required-label"/>
                模型选择
              </span>
              <span class="el-icon-s-operation operation" @click="showModelSet"></span>
            </p>
            <div class="rl">
              <el-select
                v-model="editForm.modelParams"
                placeholder="请选择模型"
                @visible-change="visibleChange"
                loading-text="模型加载中..."
                class="cover-input-icon model-select"
                :disabled="isPublish"
                :loading="modelLoading"
              >
                <el-option
                  v-for="(item,index) in modleOptions"
                  :key="item.modelId"
                  :label="item.displayName"
                  :value="item.modelId"
                >
                </el-option>
              </el-select>
            </div>
          </div>
          <div class="block prompt-box">
            <p class="block-title">
              <img :src="require('@/assets/imgs/require.png')" class="required-label"/>
              开场白
            </p>
            <div class="rl">
              <el-input
                class="desc-input"
                v-model="editForm.prologue"
                maxlength="100"
                placeholder="请输入开场白"
                type="textarea"
              ></el-input>
              <span class="el-input__count">{{editForm.prologue.length}}/100</span>
            </div>
          </div>
          <div class="block prompt-box">
            <p class="block-title ">系统提示词</p>
            <div class="rl">
              <el-input
                class="desc-input "
                v-model="editForm.instructions"
                maxlength="600"
                placeholder="描述你想创建的应用，详细描述应用的详细功能及作用，以及对该应用生成结果的要求"
                type="textarea"
              ></el-input>
              <span class="el-input__count">{{editForm.instructions.length}}/600</span>
            </div>
          </div>
          <div class="block recommend-box">
            <p class="block-title recommend-title">
              <span>推荐问题</span>
              <span @click="addRecommend" class="common-add">
                <span class="el-icon-plus"></span>
                <span class="handleBtn">添加</span>
              </span>
            </p>
            <div
              class="recommend-item"
              v-for="(n,i) in editForm.recommendQuestion"
              @mouseenter="mouseEnter(n)" 
              @mouseleave="mouseLeave(n)"
            >
              <el-input
                class="recommend--input"
                v-model="n.value"
                maxlength="50"
                :key="`${i}rml`"
              ></el-input>
              <span class="el-icon-delete recommend-del" @click="clearRecommend(n,i)" v-if="n.hover && n.hover === true"></span>
            </div>
          </div>
        </div>
        <div class="common-box">
          <div class="block recommend-box">
            <p class="block-title">关联知识库</p>
            <div class="rl">
              <el-select v-model="editForm.knowledgeBaseIds" placeholder="请选择关联知识库" style="width:100%;" multiple>
                <el-option
                  v-for="item in knowledgeData"
                  :key="item.knowledgeId"
                  :label="item.name"
                  :value="item.knowledgeId">
                </el-option>
              </el-select>
            </div>
          </div>
          <div class="block prompt-box">
            <p class="block-title">Rerank模型</p>
            <div class="rl">
              <el-select
                v-model="editForm.rerankParams"
                placeholder="请选择模型"
                @visible-change="rerankVisible"
                loading-text="模型加载中..."
                class="cover-input-icon"
                style="width:100%;"
                :disabled="isPublish"
                :loading="modelLoading"
              >
                <el-option
                  v-for="(item,index) in rerankOptions"
                  :key="item.modelId"
                  :label="item.displayName"
                  :value="item.modelId"
                >
                </el-option>
              </el-select>
            </div>
          </div>
        </div>
        <div class="block prompt-box link-box">
          <p class="block-title">联网检索</p>
          <div class="rl">
            <div class="block-link" style="width:50%;">
              <span class="link-text">
                <img :src="require('@/assets/imgs/bocha.png')" style="width:20px;margin-right:8px;" />
                <span>博查</span>
              </span>
              <span>
                <span class="el-icon-s-operation link-operation" @click="showLinkDiglog"></span>
                <el-switch v-model="editForm.onlineSearchConfig.enable"></el-switch>
              </span>
            </div>
          </div>
        </div>
        <div class="block recommend-box tool-box">
          <p class="block-title tool-title">
            <span>工具</span>
            <span @click="addTool" class="common-add">
              <span class="el-icon-plus"></span>
              <span class="handleBtn">添加</span>
            </span>
          </p>
          <div class="rl tool-conent">
            <div class="tool-left tool" v-show="editForm.actionInfos.length">
              <div class="action-list">
              <div
                class="action-item"
                v-for="(n,i) in editForm.actionInfos"
                :key="`${i}ac`"
              >
                <div
                  class="name"
                  @click="preUpdateAction(n.actionId)"
                >{{n.apiName}}</div>
                <div class="bt">
                  <el-switch v-model="n.enable" class="bt-switch" @change="actionSwitch(n.actionId)"></el-switch>
                  <span @click="preDelAction(n.actionId)" class="el-icon-delete del"></span>
                </div>
              </div>
              </div>
            </div>
            <div class="tool-right tool" v-show="workFlowInfos.length">
              <div class="action-list">
                <div
                  class="action-item"
                  v-for="(n, i) in workFlowInfos"
                  :key="`${i}ac`"
                >
                  <div
                    class="name"
                    style="color: #333"
                  >
                    {{ n.configName }}
                  </div>

                  <div class="bt">
                    <el-switch v-model="n.enable" class="bt-switch" @change="workflowSwitch(n.workFlowId)"></el-switch>
                    <span @click="workflowRemove(n.workFlowId)" class="el-icon-delete del"></span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div  class="actionConfig" v-if="showActionConfig">
        <ActionConfig @closeAction="closeAction" :assistantId="this.editForm.assistantId" />
      </div>
      <div class="drawer-test">
        <Chat :editForm="editForm" :chatType="'test'"/>
      </div>
    </div>
    <!-- 添加自定义插件 -->
    <el-dialog
      top="10vh"
      :title="$t('agent.addComponent')"
      :close-on-click-modal="false"
      :visible.sync="wfDialogVisible"
      width="50%"
      class="workflow-modal"
    >
      <div class="workflow-dialog">
        <p style="margin-bottom: 30px">
          <el-tag type="warning"
            ><i class="el-icon-warning"></i
            >{{$t('agent.addComponentTips')}}</el-tag
          >
        </p>
        <div class="workflow-list">
          <div
            class="workflow-item"
            v-for="(n, i) in workflowList"
            :key="`${i}`"
          >
            <img class="workflow-item-icon" :src="require('@/assets/imgs/workflowIcon.png')" />
            <div class="workflow-item-info">
              <p class="info-name">{{ n.configName }}</p>
              <p class="info-desc">{{ n.configDesc }}</p>
            </div>
            <div class="workflow-item-bt">
              <el-button v-if="n.checked" disabled size="mini"
                >{{$t('agent.added')}}</el-button
              >
              <el-button
                v-else
                type="primary"
                size="mini"
                @click="getWorkFlowDetail(n, i)"
                >{{$t('agent.add')}}</el-button
              >
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
    <!-- 编辑智能体 -->
    <CreateIntelligent ref="createIntelligentDialog" :type="'edit'" :editForm="editForm" @updateInfo="getAppDetail" />
    <!-- 模型设置 -->
    <ModelSet @setModelSet="setModelSet" ref="modelSetDialog" :modelform="editForm.modelConfig" />
    <!-- apikey -->
    <ApiKeyDialog ref="apiKeyDialog" :appId="editForm.assistantId" :appType="'agent'" />
    <!-- 选择工作类型 -->
    <ToolDiaglog ref="toolDiaglog" @selectTool="selectTool" />
    <!-- 联网检索 -->
    <LinkDialog ref="linkDialog" @setLinkSet="setLinkSet" :linkform="editForm.onlineSearchConfig" />
  </div>
</template>

<script>
import {getApiKeyRoot,appPublish} from "@/api/appspace";
import { store } from "@/store/index";
import { mapGetters } from "vuex";
import { getKnowledgeList } from "@/api/knowledge";
import CreateIntelligent from "@/components/createApp/createIntelligent";
import ModelSet from "./modelSetDialog";
import ApiKeyDialog from "./ApiKeyDialog";
import { selectModelList,getRerankList} from "@/api/modelAccess";
import { getAgentInfo,addWorkFlowInfo,delWorkFlowInfo,delActionInfo,putAgentInfo,enableWorkFlow,enableAction } from "@/api/agent";
import ActionConfig from "./action";
import ToolDiaglog from "./toolDialog";
import LinkDialog from "./linkDialog";
import { getWorkFlowList,readWorkFlow} from "@/api/workflow";
import { Base64 } from "js-base64";
import Chat from "./chat";
export default {
  components: {
    Chat,
    CreateIntelligent,
    ModelSet,
    ActionConfig,
    ApiKeyDialog,
    ToolDiaglog,
    LinkDialog
  },
  watch: {
    editForm: {
      handler(newVal) {
         if(this.debounceTimer){
            clearTimeout(this.debounceTimer)
          }
        this.debounceTimer = setTimeout(() =>{
            const props = ['modelParams', 'modelConfig', 'prologue', 'knowledgeBaseIds','instructions','recommendQuestion','onlineSearchConfig'];
            const changed = props.some(prop => {
            return JSON.stringify(newVal[prop]) !== JSON.stringify(
                (this.initialEditForm || {})[prop]
              );
            });
            if (changed) {
              if(newVal['modelParams']!== '' && newVal['prologue']!== ''){
                this.updateInfo();
              }
            }
        },500)

      },
      deep: true
    }
  },
  computed: {
    ...mapGetters("app", ["cacheData"]),
    ...mapGetters('user', ['commonInfo']),
  },
  data() {
    return {
      showOperation:false,
      appId:'',
      scope:'public',
      showActionConfig:false,
      rerankOptions:[],
      editForm:{
        assistantId:'',
        avatar:{},
        name:'',
        desc:'',
        rerankParams:'',
        modelParams:'',
        prologue:'',//开场白
        instructions:'',//系统提示词
        knowledgeBaseIds:[],
        recommendQuestion:[{ value: "", hover:false }],
        actionInfos:[],//action
        modelConfig:{
          temperature:0.7,
          topP:1,
          frequencyPenalty:0,
          presencePenalty:0,
          maxTokens:512, 
          maxTokensEnable:true,
          frequencyPenaltyEnable:true,
          temperatureEnable:true,
          topPEnable:true,
          presencePenaltyEnable:true
        },
        onlineSearchConfig:{
          enable:false,
          searchKey:'',
          searchUrl:'',
          searchRerankId:''
        }
      },
      apiURL:'',
      hasPluginPermission:false,
      modelLoading:false,
      wfDialogVisible: false,
      workFlowInfos: [],
      workflowList: [],
      modelParams: {},
      platform: this.$platform,
      isPublish: false,
      modleOptions: [],
      selectKnowledge: [],
      knowledgeData: [],
      loadingPercent: 10,
      nameStatus: "",
      saved: false, //按钮
      loading: false, //按钮
      t: null,
      logoFileList: [],
      imageUrl: "",
      defaultLogo: require("@/assets/imgs/bg-logo.png"),
      debounceTimer:null //防抖计时器
    };
  },
  created() {
    this.getKnowledgeList();
    this.getModelData();    //获取模型列表
     this.getRerankData(); //获取rerank模型
    if (this.$route.query.id) {
      this.editForm.assistantId = this.$route.query.id;
      setTimeout(() => {
        this.getAppDetail();
        this.apiKeyRootUrl() //获取api跟地址
      }, 500);
    }
    //判断是否发布
    if (this.$route.query.publish) {
      this.isPublish = true;
    }
    //判断是否有插件管理的权限
    const accessCert = localStorage.getItem('access_cert');
    const permission = accessCert ? JSON.parse(accessCert).user.permission.orgPermission : '';
    this.hasPluginPermission = permission.indexOf('plugin') !== -1;

    //自定义插件列表
    this.getWorkflowList([])
  },
  beforeDestroy() {
    store.dispatch("app/initState");
  },
  methods: {
    actionSwitch(id){
      enableAction({actionId:id}).then(res =>{
        if(res.code === 0){
          this.getAppDetail();
        }
      })
    },
    workflowSwitch(id){
      enableWorkFlow({workFlowId:id}).then(res => {
        if(res.code === 0){
          this.getAppDetail();
        }
      })
    },
    showLinkDiglog(){
      this.$refs.linkDialog.showDialog()
    },
    selectTool(val){
      if(val === 'action'){
        this.preCreateAction()
      }else{
        this.preAddWorkflow()
      }
    },
    addTool(){
      this.wfDialogVisible = true
      // this.$refs.toolDiaglog.showDialog();
    },
    rerankVisible(val){
      if(val){
        this.getRerankData();
      }
    },
    getRerankData(){
      getRerankList().then(res =>{
        if(res.code === 0){
          this.rerankOptions = res.data.list || []
        }
      })
    },
    goBack(){
      this.$router.go(-1)
    },
    handlePublish(){
      this.showOperation = !this.showOperation;
    },
    savePublish(){
      if(this.editForm.modelParams === ''){
        this.$message.warning('请选择模型！')
        return false
      }
      if(this.editForm.prologue === ''){
        this.$message.warning('请输入开场白！')
        return false
      }
      const data = {appId:this.editForm.assistantId,appType:'agent',publishType:this.scope}
      appPublish(data).then(res =>{
        if(res.code === 0){
          this.$router.push({path:'/explore'})
        }
      })
    },
    apiKeyRootUrl(){
      const data = {appId:this.editForm.assistantId,appType:'agent'}
      getApiKeyRoot(data).then(res =>{
        if(res.code === 0){
          this.apiURL = res.data || ''
        }
      })
    },
    openApiDialog(){
      this.$refs.apiKeyDialog.showDialog()
    },
    setModelSet(data){
      this.editForm.modelConfig = data;
    },
    setLinkSet(data){
      this.editForm.onlineSearchConfig.searchKey = data.searchKey;
      this.editForm.onlineSearchConfig.searchUrl = data.searchUrl;
      this.editForm.onlineSearchConfig.searchRerankId = data.searchRerankId;
    },
    showModelSet(){
      this.$refs.modelSetDialog.showDialog()
    },
    editAgent(){
      this.$refs.createIntelligentDialog.openDialog()
    },
    async getWorkFlowDetail(n, index) {
      let params = {
        workflowID: n.id,
      };
      let res = await readWorkFlow(params);
      if (res.code === 0) {
        this.doCreateWorkFlow(n.id, res.data.base64OpenAPISchema, index);
      }
    },
    preAddWorkflow() {
      this.wfDialogVisible = true;
    },
     workflowRemove(val) {
      this.doDeleteWorkflow(val);
    },
    visibleChange(val){//下拉框显示的时候请求模型列表
      if(val){
        this.getModelData()
      }
    },
    async getModelData() {
      this.modelLoading = true;
      const res = await selectModelList();
      if (res.code === 0) {
        this.modleOptions = res.data.list || [];
        this.modelLoading = false;
      }
      this.modelLoading = false;
    },
    async getKnowledgeList() {
      //获取文档知识分类
      const res = await getKnowledgeList();
      if (res.code === 0) {
        this.knowledgeData = res.data.knowledgeList || [];
      } else {
        this.$message.error(res.message);
      }
    },
    async updateInfo() {
         //知识库数据
      const knowledgeMap = new Map(this.knowledgeData.map(item => [item.knowledgeId, item]));
      const knowledgeData = this.editForm.knowledgeBaseIds.map(id => {
        const found = knowledgeMap.get(id);
        return found ? { id: found.knowledgeId, name: found.name } : null;
      }).filter(Boolean);
      //模型数据
      const modeInfo = this.modleOptions.find(item => item.modelId === this.editForm.modelParams)
      const rerankInfo = this.rerankOptions.find(item => item.modelId === this.editForm.rerankParams)
      const recommendQuestion = this.editForm.recommendQuestion.map(item => item.value)
      const params = {
        assistantId:this.editForm.assistantId,
        prologue:this.editForm.prologue,
        recommendQuestion:recommendQuestion.length > 0 && recommendQuestion[0] !== '' ? recommendQuestion : [],
        instructions:this.editForm.instructions,
        knowledgeBaseConfig:{
          knowledgebases:!knowledgeData.length ? [] : knowledgeData,
        },
        modelConfig:{
          config:this.editForm.modelConfig,
          displayName: modeInfo.displayName,
          model: modeInfo.model,
          modelId: modeInfo.modelId,
          modelType: modeInfo.modelType,
          provider: modeInfo.provider,
        },
        onlineSearchConfig:this.editForm.onlineSearchConfig,
        rerankConfig:rerankInfo?{
          displayName: rerankInfo.displayName,
          model: rerankInfo.model,
          modelId: rerankInfo.modelId,
          modelType: rerankInfo.modelType,
          provider: rerankInfo.provider,
        }:{}

      }
      let res = await putAgentInfo(params);
    },
    startLoading(val) {
      this.loadingPercent = val;
      if (val === 0) {
        this.loading = true;
      }
      if (val === 100) {
        setTimeout(() => {
          this.loading = false;
        }, 500);
      }
    },
    async getAppDetail() {
      this.startLoading(0);
      let res = await getAgentInfo({ assistantId: this.editForm.assistantId });
      if (res.code === 0) {
        this.startLoading(100);
        let data = res.data;
        const knowledgeData = res.data.knowledgeBaseConfig.knowledgebases;
        if(knowledgeData && knowledgeData.length > 0){
          this.editForm.knowledgeBaseIds = knowledgeData.map(item => item.id);
        }
        this.editForm = {
          ...this.editForm,
          avatar: data.avatar || {},
          prologue: data.prologue || "",//开场白
          name: data.name || "",
          desc: data.desc || "",
          rerankParams:data.rerankConfig.modelId || "",
          modelConfig:data.modelConfig.config,
          modelParams: data.modelConfig.modelId || "",
          recommendQuestion:data.recommendQuestion && data.recommendQuestion.length >0
            ? data.recommendQuestion.map((n,index) => {
                return { 
                  value: n,
                  hover:false
                };
              })
            : [],
          actionInfos: data.actionInfos || [],
          onlineSearchConfig:data.onlineSearchConfig
        };

        //回显自定义插件
        this.getWorkflowList(data.workFlowInfos || []);
      }
    },
    async getWorkflowList(workFlowInfos) {
      let res = await getWorkFlowList();
      if (res.code === 0) {
        //获取已发布插件
        this.workflowList = res.data.list.filter((n) => {
          return n.status === "published";
        });
        //回显已选插件
        let _workFlowInfos = [];
        workFlowInfos.forEach((n) => {
          this.workflowList.forEach((m, j) => {
            if (n.workFlowId === m.id) {
              const updatedItem = {
                    ...m,         
                    enable:n.enable,
                    workFlowId: n.id,
                    checked: true
                  };
              this.$set(this.workflowList, j, updatedItem);
              _workFlowInfos.push(updatedItem );
            }
          });
        });
        this.workFlowInfos = _workFlowInfos;
      }
    },
    async doCreateWorkFlow(workFlowId, schema, index) {
      let params = {
        assistantId: this.editForm.assistantId,
        schema: Base64.decode(schema),
        workFlowId,
        apiAuth: {
          type: "none",
        },
      };
      let res = await addWorkFlowInfo(params);
      if (res.code === 0) {
        this.$message.success(this.$t('agent.addPluginTips'));
        this.getAppDetail();
      }
    },
     async doDeleteWorkflow(workFlowId) {
      if (this.editForm.assistantId) {
        let res = await delWorkFlowInfo({
          workFlowId,
          assistantId: this.editForm.assistantId,
        });
        if (res.code === 0) {
          this.$message.success(this.$t('agent.delPluginTips'));
          this.getAppDetail();
        }
      } else {
        this.$message.error(this.$t('agent.otherTips'));
      }
    },
    mouseEnter(n){
      if(n.hover !== undefined){
        n.hover = true
      }
    },
    mouseLeave(n){
      if(n.hover !== undefined){
        n.hover = false
      }
    },
    //推荐问题
    addRecommend() {
      if (this.editForm.recommendQuestion.length > 3) {
        return;
      }
      this.editForm.recommendQuestion.push({ value: "",hover:false});
    },
    clearRecommend(n, index) {
      if(this.editForm.recommendQuestion.length === 1) return;
      this.editForm.recommendQuestion.splice(index, 1);
    },
    closeAction(){
      this.showActionConfig = false
    },
    preCreateAction() {
      this.showActionConfig = true
    },
    preUpdateAction(actionId) {
      this.showActionConfig = true
    },
    async preDelAction(actionId) {
      this.$confirm(this.$t('createApp.delActionTips'),this.$t('knowledgeManage.tip'), {
        confirmButtonText: this.$t('createApp.save'),
        cancelButtonText: this.$t('createApp.cancel'),
        type: "warning",
      })
        .then(async () => {
          let res = await delActionInfo({ actionId });
          if (res.code === 0) {
            this.$message.success(this.$t('createApp.delSuccess'));
            this.getAppDetail();
          }
        })
        .catch(() => {});
    },
  },
};
</script>

<style lang="scss" scoped>
/deep/{
  .apikeyBtn{
    border:1px solid #384BF7;
    padding: 12px 10px;
    color: #384BF7;
    display:flex;
    align-items: center;
    img{
      height:14px;
    }
  }
}
//通用添加按钮
.common-add{
  color:#595959;
  cursor: pointer;
  .handleBtn,.el-icon-plus{
    font-size: 13px!important;
    padding:0 2px;
  }
  .el-icon-plus{
    font-weight:bold;
  }
}
.model-title{
  display:flex;
  justify-content:space-between;
  align-items:center;
  .label{
    display: flex;
    align-items:center;
    font-size: 15px;
  }
}
.question {
  cursor: pointer;
  color: #999;
  margin-left: 8px;
}
::selection {
  color: #1a2029;
  background: #c8deff;
}
.question {
  cursor: pointer;
  color: #ccc;
  margin-left: 6px;
}
.form-header{
  width:100%;
  height:60px;
  display:flex;
  justify-content:space-between;
  align-items:center;
  padding:0 20px;
  position:relative;
  border-bottom:1px solid #dbdbdb;
  .popover-operation{
    position:absolute;
    bottom:-100px;
    right:20px;
    background:#fff;
    box-shadow: 0px 1px 7px rgba(0, 0, 0, 0.3);
    padding:10px 20px;
    border-radius:6px;
    z-index:999;
    .saveBtn{
      display:flex;
      justify-content:center;
      padding:10px 0;
    }
  }
  .header-left{
    .btn{
      margin-right:10px;
      font-size:18px;
      cursor: pointer;
    }
    .header-left-title{
      font-size:18px;
      color: #434C6C;
      font-weight: bold;
    }
  }
  .header-right{
    display: flex;
    align-items:center;
    .header-api{
      padding: 6px 10px;
      box-shadow: 1px 2px 2px #ddd;
      background-color: #fff;
      margin:0 10px;
      border-radius:6px;
      .root-url{
        background-color:#ECEEFE;
        color:#384BF7;
        border:none;
      }
    }
  }

}
.agent-from-content{
  height:100%;
  width:100%;
  overflow: hidden;
}
.agent_form{
  padding:0 10px;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  height:calc(100% - 60px);
  .actionConfig{
    overflow-y: auto;
    width:40% ;
    padding:0 40px;
  }
  .drawer-form {
    width:50%;
    position: relative;
    height:100%;
    padding:0 10px;
    border-radius: 6px;
    overflow-y: auto;
    .editIcon{
      font-size: 16px;
      margin-left: 5px;
      cursor: pointer;
    }
  /deep/.el-input__inner,
  /deep/.el-textarea__inner {
    background-color: transparent !important;
    border: 1px solid #d3d7dd !important;
    font-family: "Microsoft YaHei", Arial, sans-serif;
    padding: 15px;
  }
  .flex {
    width: 100%;
    display: flex;
    justify-content: space-between;
  }
  .link-box{
    background: #F7F8FA;
    box-shadow: 0 1px 4px 0 rgba(0, 0, 0, 0.15);
    border-radius:8px;
    padding:10px 20px;
  }
  .common-box{
    background: #F7F8FA;
    box-shadow: 0 1px 4px 0 rgba(0, 0, 0, 0.15);
    border-radius:8px;
    padding:5px 20px;
    margin-bottom: 15px;
    .block{
      margin-bottom:10px;
    }
  }
  .tool-box{
    background: #F7F8FA;
    box-shadow: 0 1px 4px 0 rgba(0, 0, 0, 0.15);
    border-radius:8px;
    padding:10px 20px;
  }

  .agnetSet{
    background:#F7F8FA;
    box-shadow: 0 1px 4px 0 rgba(0, 0, 0, 0.15);
    border-radius:8px;
    margin-bottom:15px;
    .block{
      padding:5px 20px;
      margin-bottom:0px !important;
    }
    .labelTitle{
      font-size: 18px;
      font-weight:800;
      padding:10px 20px;
    }
  }
  /*通用*/
  .block {
    margin-bottom: 15px;
    .basicInfo{
      display: flex;
      align-items:center;
      background:#F7F8FA;
      box-shadow: 0 1px 4px 0 rgba(0, 0, 0, 0.15);
      border-radius:8px;
      padding:10px 0;
      margin-top:10px;
      .img{
        width:70px;
        height:70px;
        padding:10px;
        img{
          border:1px solid #eee;
          border-radius:50%;
          width:100%;
          height:100%;
          object-fit: cover;
        }
      }
      .basicInfo-title{
        display:inline-block;
        font-weight:800;
        font-size:18px;
      }
    }
    .tool-title{
      display:flex;
      justify-content:space-between;
      span{font-size: 15px;}
    }
    .block-title {
      line-height: 30px;
      font-size: 15px;
      font-weight: bold;
      display: flex;
      align-items:center;
      .title_tips {
        color: #999;
        margin-left: 20px;
        font-weight: normal;
      }
    }
    .block-link{
      width:300px;
      border:1px solid #ddd;
      padding: 6px 10px;
      border-radius:6px;
      display:flex;
      justify-content:space-between;
      align-items:center;
      .link-text{
        color:#384BF7;
        display:flex;
        align-items:center;
      }
      .link-operation{
        cursor: pointer;
        margin-right:5px;
        font-size:16px;
      }
    }
    .tool-conent{
      display:flex;
      justify-content:space-between;
      gap:10px;
      .tool{
        width:100%;
        max-height:300px;
        .action-list{
          width:100%;
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
        }
      }
    }
    .model-select{
      width:100%;
    }
    .operation{
      text-align:center;
      cursor:pointer;
      font-size: 16px;
      padding-right:10px;
    }
    .operation:hover{
      color:#384BF7;
    }
    .tips {
      display: flex;
      align-items: center;
      margin-bottom: 5px;
      .block-title-tips {
        color: #ccc;
        margin-right: 10px;
      }
    }
    .paramsSet {
      padding: 10px;
    }
    .required-label {
      width: 18px;
      height:18px;
      margin-right: 4px;
    }
    .block-tip {
      color: #919eac;
    }
  }
  .el-input__count {
    color: #909399;
    background: #fafafa;
    position: absolute;
    font-size: 12px;
    bottom: 5px;
    right: 10px;
  }
  /*新建应用*/
  .name-box {
    height: 90px;
    line-height: 90px;
    font-size: 22px;
    display: flex;
    .name-input {
      width: 100%;
    }
    .input-echo {
      font-size: 22px;
      .name-edit {
        margin-left: 20px;
        cursor: pointer;
        font-size: 16px;
      }
    }
  }
  .logo-box {
    margin-top: 20px;
    .right-input-box {
      flex: 1;
      width: 0;
      margin-left: 20px;
    }
    .instructions-input {
      margin-top: 10px;
    }
  }
  .logo-upload {
    width: 120px;
    height: 120px;
    margin-top: 3px;
    /deep/ {
      .el-upload {
        width: 100%;
        height: 100%;
      }
      .echo-img {
        img {
          object-fit: cover;
          height: 100%;
        }
        .echo-img-tip {
          position: absolute;
          width: 100%;
          bottom: 0;
          background: #33333396;
          color: #fff !important;
          font-size: 12px;
          line-height: 26px;
          z-index: 10;
        }
      }
    }
  }
  /deep/.desc-input {
    .el-textarea__inner {
      height: 90px !important;
    }
  }
  .systemPrompt-tip {
    background-color: #f1f1f1;
    border-radius: 6px;
    line-height: 24px;
    color: #919eac;
    margin-top: 10px;
    padding: 8px 20px;
  }
  /*推荐问题*/
  .recommend-box {
    .recommend-title{
      display:flex;
      justify-content: space-between;
      span{
        font-size:15px;
      }
    }
    .recommend-item {
      margin-bottom: 12px;
      display:flex;
      justify-content: space-between;
      position:relative;
      .recommend--input {
        width:100%;
      }
      .recommend-del{
        position:absolute;
        right:10px;
        top:10px;
        color:#595959;
        cursor: pointer;
      }
      .close--icon {
        display: inline-block;
        width: 60px;
        line-height: 40px;
        text-align: center;
        cursor: pointer;
        color: #333;
        &:hover {
          font-weight: bold;
        }
      }
    }
  }

  /*知识增强*/
  .knowledge-config-com {
    margin-top: 10px;
  }

  /*action*/
  .api-box {
    padding-bottom: 60px;
  }

  /*插件*/
  .plugin-box {
    .el-checkbox-group {
      margin-top: 10px;
    }
    .plugin-checkbox /deep/.el-checkbox__inner.is-checked.el-checkbox__inner {
      background-color: #409eff;
      border-color: #409eff;
    }
  }

  /*footer*/
  .footer {
    position: absolute;
    height: 80px;
    padding: 20px 0;
    bottom: 0;
    left: 0;
    right: 0;
    text-align: center;
    border-top: 1px solid #d3d7dd;
  }
}
.drawer-test{
  width:50%;
  background:#F7F8FA;
  border-radius:8px;
  margin:10px 0;
  box-shadow: 0 1px 4px 0 rgba(0, 0, 0, 0.15);
}
}


.loading-progress {
  width: 100%;
  top: -4px;
  z-index: 1;
  position: fixed;
  left: -2px;
  right: -2px;
}
.action-list {
  margin: 10px 0 15px 0;
  width:100%;
  .action-item {
    display: flex;
    justify-content: space-between;
    align-items:center;
    border: 1px solid #ddd;
    border-radius:6px;
    margin-bottom: 5px;
    width:100%;
    .name {
      width:60%;
      box-sizing:border-box;
      padding: 10px 20px;
      cursor: pointer;
      color: #2c7eea;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis; 
    }
    .bt {
      text-align: center;
      width:40%;
      display:flex;
      justify-content:flex-end;
      padding-right:10px;
      box-sizing:border-box;
      cursor: pointer;
      .del{
        color:#384BF7;
        font-size:16px;
      }
      .bt-switch{
        margin-right:10px;
      }
    }
  }
}
.workflow-dialog {
  height: 700px;
}
.workflow-list {
  height: calc(100% - 60px);
  overflow: auto;
  padding: 0 40px;
  .workflow-item {
    display: flex;
    margin: 10px 0;
    padding: 10px 0;
    border-bottom: 1px solid #eee;
    .workflow-item-icon {
      width: 30px;
      height: 30px;
      object-fit: fill;
    }
    .workflow-item-info {
      flex: 6;
      margin-left: 20px;
      .info-name {
        font-size: 16px;
        color: #111;
      }
      .info-desc {
        margin-top: 10px;
      }
    }
    .workflow-item-bt {
      flex: 1;
      margin-top: 7px;
    }
  }
}
.workflow-modal /deep/.el-dialog__body {
  max-height: none;
  padding: 10px 20px 30px 20px;
}
.workflow-list-checked {
  .workflow-item {
    display: flex;
    margin: 10px 0;
    padding: 10px 0;
    border-bottom: 1px solid #eee;
  }
}
</style>
<style lang="scss">
.vue-treeselect .vue-treeselect__menu-container {
  z-index: 9999 !important;
}
.custom-tooltip.is-light {
  border-color: #ccc; /* 设置边框颜色 */
  background-color: #fff; /* 设置背景颜色 */
  color: #666; /* 设置文字颜色 */
}
.custom-tooltip.el-tooltip__popper[x-placement^="top"] .popper__arrow::after {
  border-top-color: #fff !important;
}
.custom-tooltip.el-tooltip__popper.is-light[x-placement^="top"] .popper__arrow {
  border-top-color: #ccc !important;
}
</style>


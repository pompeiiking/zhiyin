<template>
  <div class="agent-from-content">
    <div class="form-header">
      <div class="header-left">
        <span class="el-icon-arrow-left btn" @click="goBack"></span>
        <span class="header-left-title">文本问答编辑</span>
      </div>
      <div class="header-right">
        <div class="header-api">
          <el-tag  effect="plain" class="root-url">API根地址</el-tag>
          {{apiURL}}
        </div>
        <el-button @click="openApiDialog" plain class="apikeyBtn" size="small" >
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
      <div class="drawer-form">
        <div class="block prompt-box">
          <div class="basicInfo">
            <div class="img">
              <img :src="editForm.avatar.path ? `/user/api`+ editForm.avatar.path : '@/assets/imgs/bg-logo.png'"  />
            </div>
            <div>
              <span class="basicInfo-title">{{editForm.name || '无信息'}}</span>
              <span class="el-icon-edit-outline editIcon" @click="editAgent"></span>
              <p>{{editForm.desc || '无信息'}}</p>
            </div>
          </div>
        </div>
        <div class="model-box">
          <div class="block prompt-box">
            <p class="block-title common-set">
              <span class="common-set-label">
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
              Rerank模型
            </p>
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
          <div class="block recommend-box">
            <p class="block-title common-set">
              <span class="common-set-label">
                <img :src="require('@/assets/imgs/require.png')" class="required-label"/>
                关联知识库
              </span>
              <span class="el-icon-s-operation operation" @click="showKnowledgeSet"></span>
            </p>
            <div class="rl">
              <el-select 
              v-model="editForm.knowledgeBaseIds" 
              placeholder="请选择关联知识库" 
              class="model-select" 
              clearable 
              multiple>
                <el-option
                  v-for="item in knowledgeData"
                  :key="item.knowledgeId"
                  :label="item.name"
                  :value="item.knowledgeId">
                </el-option>
              </el-select>
            </div>
          </div>
        </div>
      </div>
      <div class="drawer-test">
        <Chat :chatType="'test'" :editForm="editForm"/>
      </div>
    </div>
    <!-- 编辑智能体 -->
    <CreateTxtQues ref="createTxtQues" :type="'edit'" :editForm="editForm" @updateInfo="getDetail"/>
    <!-- 模型设置 -->
    <ModelSet @setModelSet="setModelSet" ref="modelSetDialog" :modelConfig="editForm.modelConfig" />
    <!-- 知识库设置 -->
    <knowledgeSet @setKnowledgeSet="setKnowledgeSet" ref="knowledgeSetDialog" :knowledgeConfig="editForm.knowledgeConfig" />
    <!-- apikey -->
    <ApiKeyDialog ref="apiKeyDialog" :appId="editForm.appId" :appType="'rag'" />
  </div>
</template>

<script>
import {getApiKeyRoot,appPublish} from "@/api/appspace";
import { getKnowledgeList } from "@/api/knowledge";
import CreateTxtQues from "@/components/createApp/createRag.vue"
import ModelSet from "./modelSetDialog.vue";
import knowledgeSet from "./knowledgeSetDialog.vue"
import ApiKeyDialog from "./ApiKeyDialog";
import { getRerankList,selectModelList } from "@/api/modelAccess";
import { getRagInfo,updateRagConfig } from "@/api/rag";
import Chat from "./chat";
export default {
  components: {
    Chat,
    CreateTxtQues,
    ModelSet,
    knowledgeSet,
    ApiKeyDialog
  },
  data() {
    return {
      rerankOptions:[],
      showOperation:false,
      scope:'public',
      editForm:{
        appId:'',
        avatar:{},
        name:'',
        desc:'',
        modelParams:'',
        modelConfig:{
          temperature:0.14,
          topP:0.85,
          frequencyPenalty:1.1,
          temperatureEnable:true,
          topPEnable:true,
          frequencyPenaltyEnable:true
        },
        rerankParams:'',
        knowledgeBaseIds:[],
        knowledgeConfig:{
          maxHistory:0,
          threshold:0.4,
          topK:5,
          maxHistoryEnable:true,
          thresholdEnable:true,
          topKEnable:true
        }
      },
      initialEditForm:null,
      apiURL:'',
      modelLoading:false,
      wfDialogVisible: false,
      workFlowInfos: [],
      workflowList: [],
      modelParams:'',
      rerankParams:'',
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
      debounceTimer:null //防抖计时器
    };
  },
  watch:{
    editForm: {
    handler(newVal) {
      if(this.debounceTimer){
        clearTimeout(this.debounceTimer)
      }
      this.debounceTimer = setTimeout(() =>{
          const props = ['modelParams', 'modelConfig', 'rerankParams', 'knowledgeBaseIds', 'knowledgeConfig'];
          const changed = props.some(prop => {
          return JSON.stringify(newVal[prop]) !== JSON.stringify(
              (this.initialEditForm || {})[prop]
            );
          });
          if (changed) {
            if(newVal['modelParams']!== '' && newVal['rerankParams']!== '' && newVal['knowledgeBaseIds'].length > 0){
              this.updateInfo();
            }
          }
      },500)
    },
    deep: true
    }
  },
  mounted() {
    this.initialEditForm = JSON.parse(JSON.stringify(this.editForm));
  },
  created() {
    this.getModelData(); //获取模型列表
    this.getRerankData(); //获取rerank模型
    this.getKnowledgeList();//获取知识库列表
    if (this.$route.query.id) {
      this.editForm.appId = this.$route.query.id;
      setTimeout(() => {
        this.getDetail();//获取详情
        this.apiKeyRootUrl(); //获取api跟地址
      }, 500);
    }
  },
  methods: {
    goBack(){
      this.$router.go(-1);
    },
    getDetail(){//获取详情
      getRagInfo({ragId:this.editForm.appId}).then(res =>{
        if(res.code === 0){
            this.editForm.avatar = res.data.avatar;
            this.editForm.name = res.data.name;
            this.editForm.desc = res.data.desc;
            this.editForm.modelParams = res.data.modelConfig.modelId;
            if(res.data.modelConfig.config !== null){
              this.editForm.modelConfig = res.data.modelConfig.config;
            }
            this.editForm.rerankParams = res.data.rerankConfig.modelId;
            const knowledgeData = res.data.knowledgeBaseConfig.knowledgebases;
            if(knowledgeData && knowledgeData.length > 0){
              this.editForm.knowledgeBaseIds = knowledgeData.map(item => item.id);
            }
            this.editForm.knowledgeConfig = res.data.knowledgeBaseConfig.config;//需要后端修改
        }
      })
    },
    getRerankData(){
      getRerankList().then(res =>{
        if(res.code === 0){
          this.rerankOptions = res.data.list || []
        }
      })
    },
    handlePublish(){
      this.showOperation = !this.showOperation;
    },
    savePublish(){
      if(this.editForm.modelParams === ''){
        this.$message.warning('请选择模型！')
        return false
      }
      if(this.editForm.rerankParams === ''){
        this.$message.warning('请选rerank择模型！')
        return false
      }
      if(this.editForm.knowledgeBaseIds.length === 0){
        this.$message.warning('请选择关联知识库！')
        return false
      }
      const data = {appId:this.editForm.appId,appType:'rag',publishType:this.scope}
      appPublish(data).then(res =>{
        if(res.code === 0){
          this.$router.push({path:'/explore'})
        }
      })
    },
    apiKeyRootUrl(){
      const data = {appId:this.editForm.appId,appType:'rag'}
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
    showModelSet(){
      this.$refs.modelSetDialog.showDialog()
    },
    showKnowledgeSet(){
      this.$refs.knowledgeSetDialog.showDialog()
    },
    setKnowledgeSet(data){
      this.editForm.knowledgeConfig = data;
    },
    editAgent(){
      this.$refs.createTxtQues.openDialog()
    },
    visibleChange(val){
      if(val){
        this.getModelData();
      }
    },
    rerankVisible(val){
      if(val){
        this.getRerankData();
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
      let fromParams = {
        ragId:this.editForm.appId,
        knowledgeBaseConfig:{
          knowledgebases:knowledgeData,
          config:this.editForm.knowledgeConfig
        },
        modelConfig:{
          config:this.editForm.modelConfig,
          displayName: modeInfo.displayName,
          model: modeInfo.model,
          modelId: modeInfo.modelId,
          modelType: modeInfo.modelType,
          provider: modeInfo.provider,
        },
        rerankConfig:{
          displayName: rerankInfo.displayName,
          model: rerankInfo.model,
          modelId: rerankInfo.modelId,
          modelType: rerankInfo.modelType,
          provider: rerankInfo.provider,
        }
      }
      const res = await updateRagConfig(fromParams)
    }
  }
};
</script>

<style lang="scss" scoped>
/deep/{
  .apikeyBtn{
    padding: 12px 10px;
    border:1px solid #384BF7;
    color: #384BF7;
    display:flex;
    align-items: center;
    img{
      height:14px;
    }
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
  .drawer-form {
    width:50% ;
    position: relative;
    height:100%;
    padding:0 10px;
    border-radius: 6px;
    overflow-y: auto;
    display:flex;
    flex-direction: column;
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
  .model-box{
    background:#F7F8FA;
    box-shadow: 0 1px 4px 0 rgba(0, 0, 0, 0.15);
    border-radius:8px;
    padding:20px 15px;
    margin-bottom:10px;
    .block{
      margin-bottom:10px;
    }
  }
  .common-set{
    display:flex;
    justify-content: space-between;
    .common-set-label{
      display:flex;
      align-items:center;
      font-size: 15px;
      font-weight:bold;
    }
  }
  /*通用*/
  .block {
    margin-bottom: 24px;
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
    .tool-conent{
      display:flex;
      justify-content:space-between;
      gap:10px;
      .tool{
        width:50%;
        height:300px;
        max-height:300px;
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
    .required-label{
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
    .recommend-item {
      margin-bottom: 12px;
      .recommend--input {
        width: calc(100% - 60px);
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
  border-radius:6px;
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
  border: 1px solid #ddd;
  .action-item {
    display: flex;
    justify-content: space-between;
    border-top: 1px solid #ddd;
    margin-top: -1px;
    .name {
      border-right: 1px solid #ddd;
      flex: 4;
      padding: 10px 20px;
      cursor: pointer;
      color: #2c7eea;
    }
    .bt {
      text-align: center;
      flex: 1;
      cursor: pointer;
      padding: 10px 20px;
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


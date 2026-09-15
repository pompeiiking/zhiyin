<template>
    <div class="full-content">
        <div class="title">
            <i class="el-icon-back" @click="preBack" style="margin-right: 20px; font-size: 20px; cursor: pointer"></i>
            {{$t('knowledgeManage.hitTest')}}
            </div>
        <el-container class="mainConetnt">
            <el-aside width="260px" class="border">
                <el-container>
                    <el-header>{{$t('knowledgeManage.selectKnowledgeTips')}}</el-header>
                    <el-main>
                       <el-tree
                        ref="knowledgeTree"
                        :data="nodeList"
                        :props="props"
                        node-key="id"
                        show-checkbox
                        :default-expanded-keys="['all']"
                       >
                       </el-tree> 
                    </el-main>
                </el-container>
            </el-aside>
            <el-main class="padding border" style="margin-left:10px;">
                <el-container style="width:100%;height:100%">
                    <el-header>{{$t('knowledgeManage.hitPrediction')}}</el-header>
                    <el-main class="padding">
                       <div style="height:30%;width:100%;">
                            <el-input  type="textarea" :rows="4" :placeholder="$t('knowledgeManage.inputTestContent')" v-model="testInput"></el-input>
                            <div class="btn">
                                <el-button type="primary" @click="startTest">{{$t('knowledgeManage.startTest')}}</el-button>
                            </div>
                       </div>
                       <div style="height:70%;width:100%;">
                        <el-header>{{$t('knowledgeManage.hitResult')}}</el-header>
                        <div class="result" v-loading="resultLoading">
                            <template v-if="searchList.length >0">
                            <div v-for="(item,index) in searchList" :key="'result'+index" class="resultItem">
                                <div class="resultTitle">
                                    <span class="tag">{{$t('knowledgeManage.section')}}{{index+1}}</span>
                                    <span class="score">{{$t('knowledgeManage.hitScore')}}: {{score[index]}}</span>
                                </div>
                                <div>{{item}}</div>
                            </div>
                            </template>
                            <div v-else class="noResult">
                               {{ noResult }}
                            </div>
                        </div>
                       </div>
                    </el-main>
                </el-container>
            </el-main>
        </el-container>
    </div>
</template>
<script>
import { test,getDocList } from "@/api/knowledge";
export default{
    data(){
        return{
            resultLoading:false,
            nodeList:[],
            props:{
                label:'categoryName',
                children:'children'
            },
            testInput:'',
            searchList:[],
            score:[],
            noResult: "",
        }
    },
    created(){
        this.getClassfyDoc()
    },
    methods:{
        preBack(){
          this.$router.go(-1);
        },
        startTest(){
            const nodelist = this.$refs.knowledgeTree.getCheckedNodes(false,true)
            if(nodelist.length === 0 ){
                this.$message.warning(this.$t('knowledgeManage.pselectKnowledgeTips'))
                return
            }
            if(this.testInput === ''){
                 this.$message.warning(this.$t('knowledgeManage.inputTestContent'))
                return
            }
            const data = {
                knowledgeBase: nodelist.filter(item =>item.id !== 'all').map( item => item.categoryName),
                question:this.testInput
            }
            this.test(data)
        },
        async getClassfyDoc() {//获取文档知识分类
            const res = await getDocList();
            const obj = {id:"all",categoryName:this.$t('knowledgeManage.allDoc'),children:[]}
            if (res.code === 0) {
                if(res.data.length > 0){
                    this.nodeList.push(obj)
                    this.nodeList[0]['children'] = res.data
                }else{
                    this.nodeList = []
                }
            }
        },
        async test(data){
            this.resultLoading = true
            const res = await test(data);
            if(res.code === 0){
                this.$message.success(this.$t('knowledgeManage.operateSuccess'))
                this.searchList = res.data !== null ? res.data.searchList : [];
                if(res.data){
                    this.score = res.data.score.map(item =>item.toFixed(5))
                }else{
                    this.noResult = this.$t('knowledgeManage.testResultTips')+`“${data.question}”`+this.$t('knowledgeManage.testResultTips1');
                    this.score = []
                }
                this.resultLoading = false
            }else{
                this.searchList = [];
                this.resultLoading = false
            }
        }
    }
}
</script>
<style lang="scss" scoped>
/deep/ {
    .el-tree--highlight-current .el-tree-node.is-current>.el-tree-node__content{
    background:#ffefef;
  }
  .el-tree .el-tree-node__content:hover {
    background: #ffefef;
  }
  .el-loading-spinner .path {
        stroke: #e60001 !important;
    }
}
.border { border: 1px solid #e4e7ed;}
.padding{padding:10px;}
.full-content{
  padding: 20px 20px 30px 20px;
  margin: auto;
  overflow: auto;
  background: #fafafa;
  .title {
    font-size: 18px;
    font-weight: bold;
    color: #333;
    padding: 10px 0;
  }
  .mainConetnt{
      width:100%;
      height: calc(100% - 44px);
      .el-aside{padding:10px;}
      .el-tree{background:none;}
      .el-header{height:30px!important;line-height:30px!important;padding:0 10px;}
      .btn{display:flex;justify-content: flex-end;padding:10px 0;}
      .result{
          background:#f6f7f9;
          width:100%;
          height:calc(100% - 30px);
          overflow-y:auto;
          .resultItem{
              padding:10px;
              border-bottom:1px solid #e4e7ed;
          }
        .noResult{
            color:#ccc;
            text-align:center;
            padding-top:40px;
        }
        .resultTitle{
            display:flex;
            justify-content:space-between;
            padding:5px 0 10px 0;
            .tag{
                background:#e60001;
                color:#fff;
                padding:2px 5px;
            }
            .score{
                color: #e60001;
            }
            }
      }
  }
  
}
</style>
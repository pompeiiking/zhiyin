<template>
  <div class="page-wrapper full-content">
    <div class="page-title">
      <i
        class="el-icon-arrow-left"
        @click="goBack"
        style="margin-right: 10px; font-size: 20px; cursor: pointer"
      >
      </i>
      {{knowledgeName}}
    </div>
    <div class="block table-wrap list-common wrap-fullheight">
      <el-container class="konw_container">
        <el-main class="noPadding">
          <el-container>
            <el-header class="classifyTitle">
              <div class="searchInfo">
                <el-select
                  @change="changeOption($event)"
                  v-model="docQuery.status"
                  :placeholder="$t('knowledgeManage.please')"
                  style="width:150px;"
                  class="marginRight no-border-select cover-input-icon"
                >
                  <el-option
                    v-for="item in knowLegOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
                <search-input class="cover-input-icon" :placeholder="$t('knowledgeManage.docPlaceholder')" ref="searchInput" @handleSearch="handleSearch" />
              </div>

              <div class="content_title">
                <el-button size="mini" type="primary" icon="el-icon-refresh" @click="reload">{{$t('common.gpuDialog.reload')}}</el-button>
                <el-button
                  size="mini"
                  type="primary"
                  :underline="false"
                  @click="handleUpload"
                >{{$t('knowledgeManage.fileUpload')}}</el-button>
              </div>
            </el-header>
            <el-main
              class="noPadding"
              v-loading="tableLoading"
            >
              <el-alert
                :title="title_tips"
                type="warning"
                show-icon
                style="margin-bottom:10px;"
                v-if="showTips"
              ></el-alert>
              <el-table
                :data="tableData"
                style="width: 100%"
                :header-cell-style="{ background: '#F9F9F9', color: '#999999' }"
              >
                <el-table-column
                  prop="docName"
                  :label="$t('knowledgeManage.fileName')"
                  min-width="350"
                >
                  <template slot-scope="scope">
                    <el-popover
                      placement="bottom-start"
                      :content="scope.row.docName"
                      trigger="hover"
                      width="300"
                    >
                      <span slot="reference">{{scope.row.docName.length>20?scope.row.docName.slice(0,20)+'...':scope.row.docName}}</span>
                    </el-popover>
                  </template>
                </el-table-column>
                <!-- <el-table-column
                  prop="fileSize"
                  :label="$t('knowledgeManage.fileSize')"
                ></el-table-column> -->
                <el-table-column
                  prop="docType"
                  :label="$t('knowledgeManage.fileStyle')"
                  width="80"
                >
                </el-table-column>
                <el-table-column
                  prop="uploadTime"
                  :label="$t('knowledgeManage.importTime')"
                  width="180"
                >
                </el-table-column>
                <el-table-column
                  prop="status"
                  :label="$t('knowledgeManage.currentStatus')"
                >
                  <template slot-scope="scope">
                    <span :class="[[4,5].includes(scope.row.status)?'error':'']">{{filterStatus(scope.row.status)}}</span>
                    <el-tooltip
                      class="item"
                      effect="light"
                      :content="scope.row.errorMsg?scope.row.errorMsg:''"
                      placement="top"
                      v-if="scope.row.status === 5"
                      popper-class="custom-tooltip"
                    >
                      <span
                        class="el-icon-warning"
                        style="margin-left:5px;color:#E6A23C;"
                      ></span>
                    </el-tooltip>
                  </template>
                </el-table-column>
                <el-table-column
                  :label="$t('knowledgeManage.operate')"
                  width="260"
                >
                  <template slot-scope="scope">
                    <el-button
                      size="mini"
                      round
                      @click="handleDel(scope.row)"
                      :disabled="[2,3].includes(Number(scope.row.status))"
                      :type="[2,3].includes(Number(scope.row.status))?'info':''"
                    >{{$t('common.button.delete')}}</el-button>
                    <el-button
                      size="mini"
                      round
                      :type="[0,3,5].includes(Number(scope.row.status))?'info':''"
                      :disabled="[0,3,5].includes(Number(scope.row.status))"
                      @click="handleView(scope.row)"
                    >{{$t('knowledgeManage.view')}}</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <!-- 分页 -->
              <Pagination
                class="pagination table-pagination"
                ref="pagination"
                :listApi="listApi"
                :page_size="10"
                @refreshData="refreshData"
              />
            </el-main>
          </el-container>
        </el-main>
      </el-container>
    </div>
  </div>
</template>

<script>
import Pagination from "@/components/pagination.vue";
import SearchInput from "@/components/searchInput.vue";
import {getDocList,delDocItem,uploadFileTips} from "@/api/knowledge";
export default {
  components: { Pagination,SearchInput},
  data() {
    return {
      knowledgeName:this.$route.query.name || '',
      loading:false,
      tableLoading:false,
      docQuery: {
        docName:'',
        knowledgeId:this.$route.params.id,
        status: -1
      },
      fileList: [],
      listApi: getDocList,
      title_tips:'',
      showTips:false,
      tableData: [],
      knowLegOptions:this.getKnowOptions(),
      knowledgeData: [],
      currentKnowValue:null
    };
  },
  mounted(){
    this.getTableData(this.docQuery)
  },
  methods: {
    goBack(){
      this.$router.push({path:'/knowledge'})
    },
    reload(){
      this.getTableData(this.docQuery)
    },
    handleSearch(val){
      this.docQuery.docName = val;
      this.getTableData(this.docQuery)
    },
    getKnowOptions(){
      const commonOptions = [
        { label:this.$t('knowledgeManage.all'), value: -1 },
        { label: this.$t('knowledgeManage.finish'), value: 1 },
        { label: this.$t('knowledgeManage.fail'), value: 5 },
        { label: this.$t('knowledgeManage.analysising'), value: 3 },
        { label: this.$t('knowledgeManage.checkFail'), value: 4 },
        { label: this.$t('knowledgeManage.pendingProcessing'), value: 0 },
        { label: this.$t('knowledgeManage.checking'), value: 2 }
      ];
      return commonOptions;
    },
    handleRemove(item){
      this.fileList = this.fileList.filter((files) => files.name !== item.name);
    },
    handelText(data){
      if(data.length > 0){
        return data.join(',')
      }
    },
    handleHit(){//跳转到命中预测页面
      if(this.$route.path.includes('rag')){
        this.$router.push({path:'/rag/knowledge/hitTest'})
      }else{
        this.$router.push({path:'/knowledge/hitTest'})
      }
    },
    normalizeOptions(node){
      if(node.children == null || node.children == 'null'){
        delete node.children;
      }
      return {
        id: node.id,
        label: node.categoryName,
        children: node.children,
      };
    },
    submitDocname(formName){
      this.$refs[formName].validate((valid) =>{
        if(valid){
          this.modifyDoc({id:this.currentDocdata.id,docName:this.ruleForm.docName})
        }
      })
    },
    async modifyDoc(data){
      this.loading = true;
      const res = await modifyDoc(data)
      if(res.code === 0){
        this.$message.success(this.$t('knowledgeManage.operateSuccess'))
        this.docListVisible = false
        this.getTableData(this.docQuery)
      }
      this.loading = false;
    },
    handleEdit(data){
      this.ruleForm.docName = data.docName
      this.docListVisible = true
      this.currentDocdata = data
    },
    handleDel(data){
       this.$confirm(this.$t('knowledgeManage.deleteTips'),this.$t('knowledgeManage.tip'),
        {
          confirmButtonText:  this.$t('common.button.confirm'),
          cancelButtonText: this.$t('common.button.cancel'),
          type: "warning"
        }
      )
        .then(async () => {
          let jsondata = {docIdList:[data.docId]}
          this.loading = true;
          let res = await delDocItem(jsondata);
          if (res.code === 0) {
            this.$message.success('删除成功');
            this.getTableData(this.docQuery)//获取知识分类数据
          }
          this.loading = false;
        })
        .catch((error) => {
          this.getTableData(this.docQuery)
        });
    },
    async getTableData(data){
       this.tableLoading = true;
       this.tableData = await this.$refs["pagination"].getTableData(data);
       this.tableLoading = false;
       this.getTips();
    },
    getTips(){
        uploadFileTips({knowledgeId:this.docQuery.knowledgeId}).then(res =>{
          if(res.code === 0){
              if(res.data.uploadstatus === 1){
                 this.showTips = true
                 this.title_tips = this.$t('knowledgeManage.refreshTips')
              }else if(res.data.uploadstatus === 2){
                  this.showTips = false
                  this.title_tips = ''
              }else{
                this.showTips = true
                this.title_tips = res.data.msg
              }
          }
        })
    },
    changeOption(data) {
      //通过文档状态查找
      this.docQuery.status = data
      this.getTableData({...this.docQuery, pageNo: 1})
    },
    filterStatus(status) {
      switch (status) {
        case 0:
          return this.$t('knowledgeManage.pendingProcessing');
          break;
        case 1:
          return this.$t('knowledgeManage.finish');
          break;
        case 2:
          return this.$t('knowledgeManage.checking');
          break;
        case 3:
          return this.$t('knowledgeManage.analysising');
          break;
        case 4:
          return this.$t('knowledgeManage.checkFail');
          break;
        case 5:
          return this.$t('knowledgeManage.fail');
          break;
        case -2:
          return this.$t('knowledgeManage.beUploaded');
          break;
        default:
          return this.$t('knowledgeManage.noStatus');
      }
    },

    handleView(row){
      this.$router.push({
        path: "/knowledge/section",
        query: {
          id: row.docId,
          type: row.docType,
          name:row.docName
        },
      });
    },
    async download(url,name){
      const res = await downDoc(url)
      const blobUrl = window.URL.createObjectURL(res) // 将blob对象转为一个URL
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = name
      link.click() // 启动下载
      window.URL.revokeObjectURL(link.href) // 下载完毕删除a标签
    },
    handleUpload() {
      this.$router.push({path:'/knowledge/fileUpload',query:{id:this.docQuery.knowledgeId,name:this.knowledgeName}})
    },
    refreshData(data) {
      this.tableData = data
    }
  }
};
</script>
<style lang="scss" scoped>
/deep/ {
  .el-button.is-disabled,
  .el-button--info.is-disabled {
    color: #c0c4cc !important;
    background-color: #fff !important;
    border-color: #ebeef5 !important;
  }
  .el-tree--highlight-current
    .el-tree-node.is-current
    > .el-tree-node__content {
    background: #ffefef;
  }
  .el-tabs__item.is-active {
    color: #e60001 !important;
  }
  .el-tabs__active-bar {
    background-color: #e60001 !important;
  }
  .el-tabs__content {
    width: 100%;
    height: calc(100% - 40px);
  }
  .el-tab-pane {
    width: 100%;
    height: 100%;
  }
  .el-tree .el-tree-node__content {
    height: 40px;
  }
  .custom-tree-node {
    padding: 0 10px;
  }
  .el-tree .el-tree-node__content:hover {
    background: #ffefef;
  }
  .el-tree-node__expand-icon {
    display: none;
  }
  .el-button.is-round {
    border-color: #dcdfe6;
    color: #606266;
  }
  .el-upload-list {
    max-height: 200px;
    overflow-y: auto;
  }
}
.fileNumber {
  margin-left: 10px;
  display: inline-block;
  padding: 0 20px;
  line-height: 2;
  background: rgb(243, 243, 243);
  border-radius: 8px;
}
.defalutColor {
  color: #e7e7e7 !important;
}
.border {
  border: 1px solid #e4e7ed;
}
.noPadding {
  padding: 0 10px;
}
.activeColor {
  color: #e60001;
}
.error {
  color: #e60001;
}
.marginRight {
  margin-right: 10px;
}
.full-content {
  //padding: 20px 20px 30px 20px;
  margin: auto;
  overflow: auto;
  //background: #fafafa;
  .title {
    font-size: 18px;
    font-weight: bold;
    color: #333;
    padding: 10px 0;
  }
  .tips {
    font-size: 14px;
    color: #aaabb0;
    margin-bottom: 10px;
  }
  .block {
    width: 100%;
    height: calc(100% - 58px);
    .el-tabs {
      width: 100%;
      height: 100%;
      .konw_container {
        width: 100%;
        height: 100%;
        .tree {
          height: 100%;
          background: none;
          .custom-tree-node {
            width: 100%;
            display: flex;
            justify-content: space-between;
            .icon {
              font-size: 16px;
              transform: rotate(90deg);
              color: #aaabb0;
            }
            .nodeLabel {
              color: #e60001;
              display: flex;
              align-items: center;
              .tag {
                display: block;
                width: 5px;
                height: 5px;
                border-radius: 50%;
                background: #e60001;
                margin-right: 5px;
              }
            }
          }
        }
      }
    }
    .classifyTitle {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0 10px;
      h2 {
        font-size: 16px;
      }
      .content_title {
        display: flex;
        align-items: center;
        justify-content: flex-end;
      }
    }
  }
  .uploadTips {
    color: #aaabb0;
    font-size: 12px;
    height: 30px;
  }
  .document_lise {
    list-style: none;
    li {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      padding: 7px;
      border-radius: 3px;
      line-height: 1;
      .el-icon-success {
        display: block;
      }
      .el-icon-error {
        display: none;
      }
      &:hover {
        cursor: pointer;
        background: #eee;

        .el-icon-success {
          display: none;
        }
        .el-icon-error {
          display: block;
        }
      }
      &.document_loading {
        &:hover {
          cursor: pointer;
          background: #eee;

          .el-icon-success {
            display: none;
          }
          .el-icon-error {
            display: none;
          }
        }
      }
      .el-icon-success {
        color: #67c23a;
      }

      .result_icon {
        float: right;
      }
      .size {
        font-weight: bold;
      }
    }
    .document_error {
      color: red;
    }
  }
}
</style>
<style lang="scss">
.custom-tooltip.is-light {
  border-color: #eee; /* 设置边框颜色 */
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
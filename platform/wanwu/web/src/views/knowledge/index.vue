<template>
  <div class="page-wrapper">
    <div class="page-title">
      <img class="page-title-img" src="@/assets/imgs/knowledge.png" alt="" />
      <span class="page-title-name">{{$t('knowledgeManage.knowledge')}}</span>
    </div>
    <div style="padding: 20px">
      <search-input class="cover-input-icon" :placeholder="$t('knowledgeManage.searchPlaceholder')" ref="searchInput" @handleSearch="getTableData" />
      <el-button class="add-button" size="mini" type="primary" @click="showCreate()" icon="el-icon-plus">
        {{$t('common.button.create')}}
      </el-button>
      <knowledgeList :appData="knowledgeData" @editItem="showCreate" @reloadData="getTableData" ref="knowledgeList" v-loading="tableLoading" />
      <createKnowledge ref="createKnowledge" @reloadData="getTableData" />
    </div>
  </div>
</template>
<script>
import { getKnowledgeList } from "@/api/knowledge";
import SearchInput from "@/components/searchInput.vue"
import knowledgeList from './component/knowledgeList.vue';
import createKnowledge from './component/create.vue';
export default {
    components: { SearchInput,knowledgeList,createKnowledge },
    data(){
       return{
        knowledgeData:[],
        tableLoading:false
       } 
    },
    mounted(){
      this.getTableData();
    },
    methods:{
        getTableData(){
            const searchInput = this.$refs.searchInput.value
            this.tableLoading = true
            getKnowledgeList({name:searchInput}).then(res => {
                this.knowledgeData = res.data.knowledgeList || [];
                this.tableLoading = false
            }).catch((error) =>{
                this.tableLoading = false
                this.$message.error(error)
            })
        },
        clearIptValue(){
          this.$refs.searchInput.clearValue()
        },
        showCreate(row){
            this.$refs.createKnowledge.showDialog(row)
        }
    }
}
</script>
<style lang="scss" scoped>
.add-button {
 float: right;
}

/deep/{
  .el-loading-mask{
    background: none !important;
  }
}

</style>

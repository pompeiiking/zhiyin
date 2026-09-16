<template>
  <div class="block">
    <div class="app-card" v-if="listData && listData.length">
      <div class="smart rl" v-for="(n,i) in listData" :key="`${i}sm`" @click.stop="toDocList(n)">
        <img  class="logo" :src="require('@/assets/imgs/knowledgeIcon.png')" />
        <div class="info rl">
          <p class="name" :title="n.name">
            {{n.name}}
          </p>
          <el-tooltip
            v-if="n.description"
            popper-class="instr-tooltip tooltip-cover-arrow"
            effect="dark"
            :content="n.description"
            placement="bottom-start"
          >
            <p class="desc">{{n.description}}</p>
          </el-tooltip>
        </div>
        <div class="tags">
          <!-- <span style="margin-left: 5px">{{n.stringNum || 0}}个字符</span> -->
          <span :class="['smartDate']">{{n.docCount || 0}}个文档 </span>
        </div>
        <div class="editor">
          <el-dropdown @command="handleClick($event, n)" placement="top">
            <span class="el-dropdown-link">
              <i class="el-icon-more icon edit-icon" @click.stop></i>
            </span>
            <el-dropdown-menu slot="dropdown">
              <el-dropdown-item command="edit">{{$t('common.button.edit')}}</el-dropdown-item>
              <el-dropdown-item command="delete">{{$t('common.button.delete')}}</el-dropdown-item>
            </el-dropdown-menu>
          </el-dropdown>
        </div>
      </div>
    </div>
    <el-empty class="noData" v-else :description="$t('common.noData')"></el-empty>
  </div>
</template>

<script>
import { delKnowledgeItem } from "@/api/knowledge";
import { removeDoc } from "@/api/knowledge";
import { AppType } from "@/utils/commonSet"
export default {
  props:{
    appData:{
      type:Array,
      required:true,
      default:[]
    }
  },
  watch:{
    appData:{
      handler:function(val){
        this.listData = val
      },
      immediate:true,
      deep:true
    }
  },
  data(){
    return{
      apptype:AppType,
      basePath: this.$basePath,
      listData:[]
    }
  },
  methods:{
    handleClick(command,n){
      switch (command){
        case 'edit':
          this.editItem(n);
          break;
        case 'delete':
          this.deleteItem(n.knowledgeId)
          break;
      }
    },
    editItem(row) {
      this.$emit('editItem', row)
    },
    deleteItem(knowledgeId){
      this.$confirm(this.$t('knowledgeManage.delKnowledgeTips'), this.$t('knowledgeManage.tip'), {
        confirmButtonText: this.$t('common.confirm.confirm'),
        cancelButtonText: this.$t('common.confirm.cancel'),
        type: "warning",
        beforeClose:(action, instance, done) =>{
          if(action === 'confirm'){
            instance.confirmButtonLoading = true;
            delKnowledgeItem({knowledgeId})
              .then(res =>{
                if(res.code === 0){
                  this.$message.success(this.$t('knowledgeManage.operateSuccess'));
                  this.$emit('reloadData')
                }
              })
              .catch(() => {})
              .finally(() =>{
                done();
                setTimeout(() => {
                  instance.confirmButtonLoading = false;
                }, 300);
              })
          }else{
            done()
          }
        }
      }).then(() => {})
    },
    toDocList(n){
      this.$router.push({path:`/knowledge/doclist/${n.knowledgeId}`,query:{name:n.name}});
    },
  }
}
</script>

<style lang="scss" scoped>
@import "@/style/appCard.scss";
// .noData{
//   opacity:0;
// }
.app-card {
  .smart {
    height: 152px;
    .info {
      padding-right: 0;
    }
    .desc{
      padding-top: 5px;
    }
    .logo{
      border-radius:50%;
      background: #F1F4FF;
      box-shadow: none;
      width:70px;
      height:70px;
    }
  }
}
</style>

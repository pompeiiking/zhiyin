<template>
  <div class="app-card-container">
    <div class="app-card">
      <div class="smart rl smart-create" v-if="isShowTool">
        <div class="app-card-create" @click="showCreate">
          <div class="create-img-wrap">
            <img v-if="type" class="create-type" :src="require(`@/assets/imgs/create_${type}.png`)" alt="" />
            <img class="create-img" src="@/assets/imgs/create_icon.png" alt="" />
            <div class="create-filter"></div>
          </div>
          <span>{{`创建${apptype[type]}`}}</span>
        </div>
      </div>
      <div
        v-if="listData && listData.length"
        class="smart rl"
        v-for="(n,i) in listData"
        :key="`${i}sm`"
        :style="`cursor: ${isCannotClick(n) ? 'pointer' : 'default'} !important;`"
        @click.stop="isCannotClick(n) && toEdit(n)"
      >
        <img v-if="n.avatar && n.avatar.path" class="logo" :src="basePath + '/user/api/' + n.avatar.path" />
        <span :class="['tag-app', `${n.appType}-tag`]">{{apptype[n.appType] || ''}}</span>
        <img
          v-if="apptype[n.appType]"
          class="tag-img"
          src="@/assets/imgs/rectangle.png"
          alt=""
        />
        <div class="info rl">
          <p
            class="name-wrap"
            :title="n.name"
          >
            <span class="name">{{n.name}}</span>
            <i
              v-if="isShowPublished && n.publishType"
              class="el-icon-success published-icon"
            />
          </p>
          <el-tooltip
            v-if="n.desc"
            popper-class="instr-tooltip tooltip-cover-arrow"
            effect="dark"
            :content="n.desc"
            placement="bottom-start"
          >
            <p class="desc">{{n.desc}}</p>
          </el-tooltip>
        </div>
        <div class="tags">
          <span :class="['smartDate']">{{n.createdAt}}</span>
          <div
            v-if="!isShowTool"
            class="favorite-wrap"
          >
            <img
              v-if="!n.isFavorite"
              class="favorite"
              src="@/assets/imgs/like.png"
              alt=""
              @click="handelMark($event, n, i)"
            />
            <img
              v-else
              class="favorite"
              src="@/assets/imgs/like_active.png"
              alt=""
              @click="handelMark($event, n, i)"
            />
          </div>
        </div>
        <div v-if="isShowPublished && n.publishType && type !== 'workflow'" class="publishType">
            <span v-if="n.publishType === 'private'" class="publishType-tag"><span class="el-icon-lock"></span> 私密</span>
            <span v-else class="publishType-tag"><span class="el-icon-unlock"></span> 公开</span>
        </div>
        <div
          class="editor"
          v-if="isShowTool"
        >
          <el-dropdown
            @command="handleClick($event, n)"
            placement="top"
          >
            <span class="el-dropdown-link">
              <i
                class="el-icon-more icon edit-icon"
                @click.stop
              />
            </span>
            <el-dropdown-menu slot="dropdown">
              <el-dropdown-item
                command="edit"
                v-if="isCannotClick(n)"
              >
                {{$t('common.button.edit')}}
              </el-dropdown-item>
              <el-dropdown-item
                command="delete"
                v-if="n.appId !== 'example'"
              >
                {{$t('common.button.delete')}}
              </el-dropdown-item>
              <el-dropdown-item
                command="copy"
                v-if="n.appType === 'workflow'"
              >
                {{$t('common.button.copy')}}
              </el-dropdown-item>
              <el-dropdown-item
                command="publish"
                v-if="n.appType === 'workflow' && !n.publishType && n.appId !== 'example'"
              >
                {{$t('common.button.publish')}}
              </el-dropdown-item>
            </el-dropdown-menu>
          </el-dropdown>
        </div>
      </div>
    </div>
    <el-empty class="noData" v-if="!(listData && listData.length)" :description="$t('common.noData')"></el-empty>
  </div>
</template>

<script>
import {mapActions} from 'vuex'
import { AppType } from "@/utils/commonSet";
import { deleteAPP } from "@/api/appspace";
import { copyWorkFlow, publishWorkFlow, copyExample } from "@/api/workflow";
import { setFavorite } from "@/api/explore";
export default {
  props:{
    type: String,
    showCreate: Function,
    appData:{
      type:Array,
      required:true,
      default:[]
    },
    isShowTool: false,
    isShowPublished: false,
    appFrom:{
      type:String,
      default:''
    }
  },
  watch: {
    appData: {
      handler: function (val) {
        this.listData = val;
      },
      immediate: true,
      deep: true,
    },
  },
  data() {
    return {
      apptype: AppType,
      basePath: this.$basePath,
      listData: [],
      row: {},
    };
  },
  methods: {
    // ...mapActions('app', ['getHistoryList']),
    isCannotClick(n) {
      return (n.appType === 'workflow' && !n.publishType && n.appId !== 'example') || n.appType !== 'workflow'
    },
    // 公用删除方法
    async handleDelete() {
      const params = {
        appId: this.row.appId,
        appType:this.row.appType
      };
      const res = await deleteAPP(params);
      if (res.code === 0) {
        this.$message.success(this.$t("list.delSuccess"));
        this.$emit("reloadData");
      }
    },
    workflowEdit(row) {
      const querys = {
        id: row.appId,
      };
      this.$router.push({ path: "/workflow", query: querys });
    },
    workflowDelete(row) {
      this.row = row;
      this.$alert(this.$t("list.deleteTips"), this.$t("list.tips"), {
        confirmButtonText: this.$t("list.confirm"),
        callback: (action) => {
          if (action === "confirm") {
            this.handleDelete();
          }
        },
      });
    },
    async workflowCopy(row) {
      const params = {
        workflowID: row.appId,
      }

      const isExample = row.appId === 'example'
      const exampleParams = {
        configName: row.name + '_副本',
        configENName: "",
        configDesc: row.desc,
        isStream: false
      }

      const res = isExample
        ? await copyExample({...params, ...exampleParams})
        : await copyWorkFlow(params);

      if (res.code === 0) {
        this.$router.push({
          path: "/workflow",
          query: { id: isExample ? res.data.workflowID : res.data.workflow_id },
        });
      }
    },
    workflowPublish(row) {
      this.$alert(this.$t("workFlow.publishText"), this.$t("list.tips"), {
        confirmButtonText: this.$t("list.confirm"),
        callback: async (action) => {
          if (action === "confirm") {
            const params = {
              workflowID: row.appId,
            };
            const res = await publishWorkFlow(params);
            if (res.code === 0) {
              this.$message.success(this.$t("list.publicSuccess"))
              this.$emit('reloadData')
            }
          }
        },
      });
    },
    workflowOperation(method, row) {
      console.log(method, row, "-----------------workflowOperation");
      switch (method) {
        case "edit":
          this.workflowEdit(row);
          break;
        case "delete":
          this.workflowDelete(row);
          break;
        case "copy":
          this.workflowCopy(row);
          break;
        case "publish":
          this.workflowPublish(row);
          break;
      }
    },
    intelligentEdit(row) {
      this.$router.push({
          path: "/agent/test",
          query: { id: row.appId }
      });
    },
    intelligentDelete(row) {
      this.row = row;
      this.handleDelete();
    },
    intelligentOperation(method, row) {
      switch (method) {
        case "edit":
          // 智能体编辑
          this.intelligentEdit(row);
          break;
        case "delete":
          // 智能体删除
          this.intelligentDelete(row);
          break;
      }
    },
    txtQuesEdit(row) {
      this.$router.push({
          path: "/rag/test",
          query: { id: row.appId }
      });
    },
    txtQuesDelete(row) {
      this.row = row;
      this.handleDelete();
    },
    txtQuesOperation(method, row) {
      switch (method) {
        case "edit":
          // 文本问答编辑
          this.txtQuesEdit(row);
          break;
        case "delete":
          // 文本问答删除
          this.txtQuesDelete(row);
          break;
      }
    },
    commonToChat(row){
      const type = row.appType;
      switch (type) {
        case "agent":
          this.$router.push({path:'/explore/agent', query:{id:row.appId}});
          break;
        case "rag":
          this.$router.push({path:'/explore/rag', query:{id:row.appId}});
          break;
        case "workflow":
          console.log('workflow')
          break;
      }
    },
    commonMethods(method, row) {
      const type = row.appType;
      switch (type) {
        case "agent":
          this.intelligentOperation(method, row);
          break;
        case "rag":
          this.txtQuesOperation(method, row);
          break;
        case "workflow":
          this.workflowOperation(method, row);
          break;
      }
    },
    handleClick(command, row) {
      this.commonMethods(command, row);
    },
    toEdit(row) {
      if(this.appFrom === 'explore'){
        this.commonToChat(row)
      }else{
        this.commonMethods("edit", row);
      }
    },
    handelMark(e,n, i) {
      e.stopPropagation();
      this.$confirm(
        n.isFavorite
          ? this.$t("explore.unFavorite")
          : this.$t("explore.favorite"),
        this.$t("common.confirm.title"),
        {
          confirmButtonText: this.$t("common.confirm.confirm"),
          cancelButtonText: this.$t("common.confirm.cancel"),
          type: "warning",
        }
      )
        .then(() => {
          setFavorite({
            appId: n.appId,
            appType:n.appType,
            isFavorite: !n.isFavorite,
          }).then((res) => {
            if (res.code === 0) {
              this.$message.success(
                n.isFavorite
                  ? this.$t("explore.delSuccess")
                  : this.$t("explore.setSuccess")
              );
              const list = [...this.listData];
              list[i].isFavorite = !n.isFavorite;
              this.listData = [...list];
              // this.getHistoryList();
            }
          });
        })
        .catch(() => {});
      
    },
  },
};
</script>

<style lang="scss" scoped>
@import "@/style/appCard.scss";
.noData {
  padding: 30px 0;
}
</style>

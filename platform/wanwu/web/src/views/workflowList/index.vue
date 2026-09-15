<template>
  <div class="workflow-list">
    <el-row class="search">
      <el-col :span="4">
        <el-input
          size="small"
          v-model="searchForm.keyword"
          :placeholder="$t('list.pluginName')"
          clearable
        ></el-input>
        <!--<i class="el-icon-search search-icon" @click="searchTagPagination"></i>-->
        <el-button
          type="primary"
          icon="el-icon-search"
          class="search-icon"
          circle
          @click="searchTagPagination"
        ></el-button>
      </el-col>
      <el-col :span="20" style="text-align: right">
        <el-button size="mini" type="primary" @click="preCreate"
          >{{$t('list.createplugin')}}</el-button
        >
      </el-col>
    </el-row>

    <table-with-pagination
      class="little-table"
      ref="tag-table"
      :pageSize="10"
      border
      :table="table"
      :rowClassName="tableRowClassName"
      @handlePagination="handleTagPagination"
    >
      <el-table-column
        slot="button"
        :label="$t('list.status')"
        :filter-method="filterHandler"
        :filter-multiple="false"
        :filters="[
          { text: $t('list.unpublished'), value: 'draft' },
          { text: $t('list.published'), value: 'published' },
        ]"
      >
        <template slot-scope="scope">
          <el-tag
            v-if="scope.row.status === 'published'"
            class="haveReleased"
            type="success"
            >{{$t('list.published')}}</el-tag
          >
          <el-tag class="noReleased" v-else type="info">{{$t('list.unpublished')}}</el-tag>
          <el-tag v-if="scope.row.is_stream == 1"  size="mini">{{$t('list.stream')}}</el-tag>
        </template>
      </el-table-column>
      <el-table-column slot="button" :label="$t('list.updatedTime')">
        <template slot-scope="scope">
          <span>{{ scope.row.updatedTime }}</span>
        </template>
      </el-table-column>
      <el-table-column slot="button" width="250" fixed="right" :label="$t('list.operate')">
        <template slot-scope="scope">
          <div v-if="scope.row.example_flag != 1">
            <span
              class="copy"
              v-if="scope.row.status !== 'published'"
              @click="preUpdate(scope.row)"
              >{{$t('list.edit')}}</span
            >
            &nbsp;
            <el-dropdown @command="handleCommand" :trigger="'click'">
              <el-button type="text" @click="handleClick(scope.row)"
                >{{$t('list.more')}} <i class="el-icon-arrow-down"></i
              ></el-button>
              <el-dropdown-menu slot="dropdown">
                <el-dropdown-item command="copy">{{$t('list.copy')}}</el-dropdown-item>

                <el-dropdown-item
                  v-if="scope.row.status != 'published'"
                  command="push"
                  >{{$t('list.public')}}</el-dropdown-item
                >
                <el-dropdown-item command="delete">{{$t('list.delete')}}</el-dropdown-item>
                <el-dropdown-item
                  command="cust"
                  v-if="scope.row.status == 'published'"
                  >{{$t('list.view')}}</el-dropdown-item
                >
              </el-dropdown-menu>
            </el-dropdown>
          </div>
          <div v-else>
            <span class="copy" @click="copyExample(scope.row)"
              >{{$t('list.copyDemo')}}</span
            >
          </div>
        </template>
      </el-table-column>
    </table-with-pagination>

    <CreateForm ref="create_ref" />

    <CreateForm ref="clone_ref" type="clone" />

    <PublishForm ref="publish_ref" @refreshTable="getWorkFlowList" />

    <SchemaRead ref="schema_ref" />
  </div>
</template>

<script>
import TableWithPagination from "@/components/TableWithPagination";
import {
  getWorkFlowList,
  deleteWorkFlow,
  copyWorkFlow,
  readWorkFlow,
} from "@/api/workflow";
import CreateForm from "./components/createForm";
import PublishForm from "./components/publishForm";
import SchemaRead from "./components/schemaRead";

export default {
  components: {
    TableWithPagination,
    CreateForm,
    PublishForm,
    SchemaRead,
  },
  data() {
    return {
      searchForm: {
        keyword: "",
      },
      row: {},
      table: {
        data: [],
        column: [
          { prop: "configName", label: this.$t('list.pluginName') },
          { prop: "configENName", label: this.$t('list.pluginEnName') },
          { prop: "configDesc", label: this.$t('list.pluginDesc') },
          // { prop: "status", label: "状态",formatter:function (row) {
          //         return row.status === 'published'?'已发布':'未发布'
          //     } },
        ],
        total: 0,
      },
    };
  },
  mounted() {
    this.searchTagPagination();
  },
  methods: {
    tableRowClassName({ row, rowIndex }){
      console.log(row,rowIndex)
       if (row.example_flag === 1) {
        // 假设你想要设置第二行的背景色
        return "row-bg-color";
      }
    },
    handleClick(row){
      this.row = row;
    },
     // 下拉点击事件
    handleCommand(item) {
      switch (item) {
        case "copy":
          this.preCopy(this.row);
          break;
        case "push":
          this.prePublish(this.row);
          break;
        case "delete":
          this.preDelete(this.row);
          break;
        case "cust":
          this.preRead(this.row);
          break;
      }
    },
    copyExample(row){
      this.$refs["clone_ref"].openDialog(row);
    },
    handleTagPagination(data) {
      this.getWorkFlowList(data);
    },
    searchTagPagination() {
      this.$refs["tag-table"].handelInitPage();
      this.$refs["tag-table"].handlePagination();
    },
    filterHandler(value, row) {
      return row.status === value;
    },
    async getWorkFlowList(data) {
      let params = {
        ...data,
        keyword: this.searchForm.keyword,
      };
      let res = await getWorkFlowList(params);
      this.table.data = res.data.list;
      this.table.total = res.data.total;
    },
    // 复制
    async preCopy(row) {
      let params = {
        workflowID: row.id,
      };
      let res = await copyWorkFlow(params);
      if (res.code === 0) {
        this.$router.push({
          path: "/workflow",
          query: { id: res.data.workflow_id },
        });
      }
    },
    async preRead(row) {
      let params = {
        workflowID: row.id,
      };
      let res = await readWorkFlow(params);
      if (res.code == 0) {
        this.$refs["schema_ref"].openDialog(res.data.base64OpenAPISchema);
      }
    },
    preCreate(row) {
      this.$refs["create_ref"].openDialog();
    },
    preUpdate(row) {
     let querys = {
        id: row.id
      }
      if(row.is_stream == 1){
        querys.isStream = true
      }
      this.$router.push({ path: "/workflow", query: querys });
    },
    prePublish(row) {
      this.$refs["publish_ref"].openDialog(row);
    },
    preDelete(row) {
      this.row = row;
      this.$alert(this.$t('list.deleteTips'), this.$t('list.tips'), {
        confirmButtonText: this.$t('list.confirm'),
        callback: (action) => {
          if (action == "confirm") {
            this.doDelete();
          }
        },
      });
    },
    async doDelete() {
      let params = {
        workflowID: this.row.id,
      };
      let res = await deleteWorkFlow(params);
      if (res.code === 0) {
        this.$message.success(this.$t('list.delSuccess'));
        this.searchTagPagination();
      }
    },
  },
};
</script>

<style lang="scss" scoped>
@import "../../style/workflow.scss";
.el-button--text{
  color: $color;
}
.workflow-list {
  padding: 40px;
  .search {
    margin-bottom: 20px;
    justify-content: space-between;
    .el-col {
      position: relative;
    }
    /deep/.el-input__inner {
      padding-right: 30px;
    }
    .search-icon {
      position: absolute;
      right: -29px;
      top: 0;
      padding: 8px;
      border-radius: 0 4px 4px 0;
      cursor: pointer;
      z-index: 10;
    }
  }
  .little-table {
    height: 100%;
  }
  .copy {
    color: $color;
    font-size: 13px;
    cursor: pointer;
  }
  .el-tag--mini {
    padding: 2px 5px;
    height: auto;
  }
  .el-tag {
    &:hover {
      cursor: pointer;
      background: $btn_bg;
      color: #fff;
    }
  }
}
/deep/.cell {
  .el-tag {
    margin-right: 5px;
  }
}
/deep/.row-bg-color {
  background: #f4f4f5 !important;
  div {
    color: #bcbec2 !important;
  }
}
</style>

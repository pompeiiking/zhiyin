<template>
  <div class="mcp-content-box customize">
    <div class="mcp-content">
      <div class="card-search card-search-cust">
        <div>
          <p class="card-search-des">
            集合各MCP server，即选即用。可支持在插件编排工具中使用。如使用自定义MCP，请在自定义TAB中进行添加和查看&nbsp;
          </p>
          <!--<div class="radio-box" >
            <el-radio-group v-model="source" @input="radioChange" size="mini">
              <el-radio label="">全部</el-radio>
              <el-radio label="1">来自我添加</el-radio>
              <el-radio label="2">来自广场发送</el-radio>
            </el-radio-group>
          </div>-->
        </div>
        <div>
          <search-input placeholder="请输入MCP名称进行搜索" ref="searchInput" @handleSearch="handleSearch" />
          <el-button size="mini" type="primary" @click="handleAddMCP">导入</el-button>
        </div>
      </div>

      <div class="card-box" v-if="list.length > 0">
        <div
          class="card"
          v-for="(item, index) in list"
          :key="index"
          @click.stop="handleClick(item)"
        >
          <div class="card-title">
            <img class="card-logo" v-if="item.avatar && item.avatar.path" :src="basePath + '/user/api/' + item.avatar.path" />
            <div class="mcp_detailBox">
              <span class="mcp_name">{{ item.name }}</span>
              <span class="mcp_from">
                <label>
                  {{ item.from }}
                </label>
              </span>
            </div>
            <i
              class="el-icon-delete-solid"
              @click.stop="handleDelete(item)"
            ></i>
          </div>
          <div class="card-des">{{ item.desc }}</div>
        </div>
      </div>

      <div class="no-list" v-if="list.length === 0 && is">
        <div>
          <i class="el-icon-circle-plus-outline" @click="handleAddMCP"></i>
          <span>添加你的第一个MCP Server</span>
        </div>
      </div>
    </div>
    <addDialog :dialogVisible="addOpen" @handleClose="handleClose"></addDialog>
  </div>
</template>
<script>
import addDialog from "./addDialog.vue";
import SearchInput from "@/components/searchInput.vue"
import { getList, setDelete } from "@/api/mcp";
export default {
  components: { SearchInput, addDialog },
  data() {
    return {
      basePath: this.$basePath,
      is: true, // 是否第一次进来
      addOpen: false, // 自定义添加mcp开关
      list: [],
    };
  },
  mounted() {
    this.is = true;
    this.fetchList((list) => {
      if (list.length) {
        this.is = false
      }
    })
  },
  methods: {
    radioChange(val) {
      this.handleSearch()
    },
    handleSearch() {
      if (this.is !== false) {
        if (this.list && this.list.length) {
          this.is = false
        } else {
          this.is = true
        }
      }
      this.fetchList()
    },
    fetchList(cb) {
      const searchInput = this.$refs.searchInput
      const params = {
        name: searchInput.value,
      }
      getList(params)
        .then((res) => {
          this.list = res.data.list || []
          cb && cb(this.list)
        })
        .catch(() => {})
    },
    init() {
      this.fetchList((list) => {
        if (!this.is) return
        if (list.length > 0) {
          this.is = false
        } else {
          this.is = true
        }
      })
    },
    handleClose(val) {
      this.addOpen = val;
      this.init();
    },
    handleClick(val) {
      // smcpSquareId 有值 mcp广场, 否则自定义
      this.$router.push({path: `/mcp/detail/custom?mcpId=${val.mcpId}&mcpSquareId=${val.mcpSquareId}`})
    },
    handleAddMCP() {
      this.addOpen = true;
    },
    handleDelete(item) {
      this.$confirm(
        "确定要删除 <span style='font-weight: bold;'>" + item.name + "</span> 该服务吗？",
        "提示",
        {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          dangerouslyUseHTMLString: true,
          type: "warning",
          center: true,
        }
      ).then(async () => {
        setDelete({
          mcpId: item.mcpId,
        }).then((res) => {
          if (res.code === 0) {
            this.$message.success("删除成功")
            this.init();
          } else {
            this.$message.error( res.msg || '删除失败')
          }
        })
      })
    },
  },
};
</script>
<style lang="scss">
.card-search-cust {
  text-align: left !important;

  .radio-box {
    margin: 20px 0 0 0 !important;
  }
}
.card-logo{
  width: 50px;
  height: 50px;
  object-fit: cover;
}
</style>
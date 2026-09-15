<template>
  <div class="mcp-content-box mcp-third">
    <div class="mcp-main">
      <div class="mcp-content">
        <!--<div class="mcp-menu">
          <p style="margin: 10px;border-bottom: 1px solid #d9d9d9;font-weight: bold">分类筛选</p>
          <el-radio-group v-model="category" @input="radioChange">
            <el-radio-button v-for="(n,i) in menuList" :key="`${i}ml`" :label="n"></el-radio-button>
          </el-radio-group>
        </div>-->
        <div class="mcp-card-box">
          <div class="card-search card-search-cust">
            <div>
              <span
                v-for="item in typeList"
                :key="item.key"
                :class="['tab-span', {'is-active': typeRadio === item.key}]"
                @click="changeTab(item.key)"
              >
                {{item.name}}
              </span>
            </div>
            <search-input style="margin-right: 2px" placeholder="请输入MCP名称进行搜索" ref="searchInput" @handleSearch="doGetPublicMcpList" />
          </div>

          <div class="card-loading-box" v-if="list.length">
            <div class="card-box" v-loading="loading">
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
                </div>
                <div class="card-des">{{ item.desc }}</div>
              </div>
              <!--<p class="loading-tips" v-if="loading"><i class="el-icon-loading"></i></p>
              <p class="loading-tips">没有更多了</p>-->
            </div>
          </div>
          <div v-else class="empty"><el-empty description="暂无数据"></el-empty></div>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import { getPublicMcpList } from "@/api/mcp"
import SearchInput from "@/components/searchInput.vue"
export default {
  components: { SearchInput },
  data() {
    return {
      basePath: this.$basePath,
      mcpSquareId: "",
      category: '全部',
      menuList: [],
      list: [],
      loading:false,
      typeRadio: 'all',
      typeList: [
        {name: '全部', key: 'all'},
        {name: '数据', key: 'data'},
        {name: '创作', key: 'create'},
        {name: '搜索', key: 'search'},
      ]
    };
  },
  mounted() {
    this.doGetPublicMcpList()
  },
  methods: {
    changeTab(key) {
      this.typeRadio = key
      this.$refs.searchInput.value = ''
      this.doGetPublicMcpList()
    },
    loadList(){
      this.loading = true
      this.doGetPublicMcpList()
    },
    doGetPublicMcpList(){
      const searchInput = this.$refs.searchInput
      let params = {
        name: searchInput.value,
        category: this.typeRadio,
      }

      getPublicMcpList(params)
        .then((res) => {
          this.list = res.data.list || []
          this.loading = false
        })
        .catch(() => this.loading = false)
    },
    radioChange(val){
      this.$refs.searchInput.value = ''
      this.doGetPublicMcpList()
    },
    handleClick(val) {
      this.mcpSquareId = val.mcpSquareId;
      this.$router.push({path:`/mcp/detail/square?mcpSquareId=${val.mcpSquareId}`})
    },
  },
};
</script>

<style lang="scss">
.mcp-management .mcp-third{
  min-height: 600px;
  .el-radio-button__inner{
    border: none!important;
  }
  .tab-span {
    display: inline-block;
    vertical-align: middle;
    padding: 6px 12px;
    border-radius: 6px;
    color: $color_title;
    cursor: pointer;
  }
  .tab-span.is-active {
    color: $color;
    background: #fff;
    font-weight: bold;
  }
  .mcp-main{
    display: flex;
    padding: 0 20px;
    height: 100%;
    .mcp-content{
      display: flex;
      width:100%;
      padding: 0;
      height: 100%;
      .mcp-menu{
        margin-top: 10px;
        margin-right: 20px;
        width: 90px;
        height: 450px;
        border: 1px solid $border_color; //#d0a7a7
        text-align: center;
        border-radius: 6px;
        color: #333;
        p{
          line-height: 28px;
          margin:10px 0;
        }
        .active{
          background: rgba(253, 231, 231, 1);
        }
      }
      .mcp-card-box{
        width: 100%;
        height: 100%;
        .input-with-select {
          width: 300px;
        }
        .card-loading-box{
          .card-box {
            align-content: start;
            padding-bottom: 20px;
            .hosted{
              position: absolute;
              right: -8px;
              top:5px;
              padding: 2px 6px;
              font-size: 12px;
              border-radius: 2px;
            }
            .sse{
              background: #d81e06;
              color: #fff;
            }
            .local{
              background: #555;
              color: #fff;
            }
            .loading-tips{
              height: 20px;
              color: #999;
              text-align: center;
              display: block;
              width: 100%;
              i{
                font-size: 18px;
              }
            }
          }
        }
      }
    }
  }
  .card-logo{
    width: 50px;
    height: 50px;
    object-fit: cover;
  }
}
/*.el-radio-button:first-child .el-radio-button__inner,
.el-radio-button:last-child .el-radio-button__inner{
  border-radius: 0!important;
}*/
</style>
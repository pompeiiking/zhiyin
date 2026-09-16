<template>
  <div class="page-wrapper">
    <div class="page-title">
      <img class="page-title-img" :src="typeObj[type] ? typeObj[type].img : require('@/assets/imgs/task.png')" alt="" />
      <span class="page-title-name">{{typeObj[type] ? typeObj[type].title : $t('appSpace.title')}}</span>
    </div>
    <div class="hide-loading-bg" style="padding: 20px" v-loading="loading">
      <search-input :placeholder="$t('appSpace.search')" ref="searchInput" @handleSearch="getTableData" />
      <el-button class="add-button" size="mini" type="primary" @click="showCreate" icon="el-icon-plus">
        {{$t('common.button.create')}}
      </el-button>
      <AppList
        :type="type"
        :showCreate="showCreate"
        :appData="listData"
        :isShowPublished="true"
        :isShowTool="true"
        @reloadData="getTableData"
      />
      <CreateTotalDialog ref="createTotalDialog" />
    </div>
  </div>
</template>

<script>
import SearchInput from "@/components/searchInput.vue"
import AppList from "@/components/appList.vue"
import CreateTotalDialog from "@/components/createTotalDialog.vue"
import { getAppSpaceList } from "@/api/workspace"
import { mapGetters} from 'vuex'

export default {
  components: { SearchInput, CreateTotalDialog, AppList },
  data() {
    return {
      type: '',
      loading: false,
      listData:[],
      typeObj: {
        workflow: {title: '工作流', img: require('@/assets/imgs/workflow_icon.png')},
        rag: {title: '文本问答', img: require('@/assets/imgs/rag.png')},
        agent: {title: '智能体', img: require('@/assets/imgs/agent.png')}
      },
      currentTypeObj: {}
    }
  },
  watch: {
    $route: {
      handler(val) {
        const {type} = val ? val.params || {} : {}
        this.listData = []
        this.type = type
        this.$refs.searchInput.value = ''
        this.getTableData()
        console.log(type, '----------------appSpace')
      },
      // 深度观察监听
      deep: true
    },
    fromList:{
      handler(val){
        if(val !== ''){
          this.type = val;
          this.getTableData();
        }
      }
    }
  },
  computed: {
    ...mapGetters('app', ['fromList']),
  },
  mounted() {
    const {type} = this.$route.params || {}
    this.type = type
    this.getTableData()
  },
  methods: {
    getTableData() {
      this.loading = true
      const searchInput = this.$refs.searchInput
      const searchInfo = {
        appType: this.type === 'all' ? '' : this.type,
        ...searchInput.value && {name: searchInput.value}
      }
      getAppSpaceList(searchInfo).then(res => {
        this.loading = false
        this.listData = res.data ? res.data.list || [] : []
      }).catch(() => {
        this.loading = false
        this.listData = []
      })
    },
    showCreate() {
      switch (this.type) {
        case 'agent':
          this.$refs.createTotalDialog.showCreateIntelligent()
          break
        case 'rag':
          this.$refs.createTotalDialog.showCreateTxtQues()
          break
        case 'workflow':
          this.$refs.createTotalDialog.showCreateWorkflow()
          break
        default:
          this.$refs.createTotalDialog.openDialog()
          break
      }
    }
  }
}
</script>
<style lang="scss" scoped>
.add-button {
 float: right;
}
</style>
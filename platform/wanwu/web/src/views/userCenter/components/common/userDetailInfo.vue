<template>
  <div class="detail-ul">
    <div class="flex"><label>{{$t('userInfo.username')}}</label><span>{{form.username}}</span></div>
    <div class="flex">
      <label>{{$t('userInfo.password')}}</label>
      <span class="pwd-span">{{form.password || '--'}}</span>
      <el-button type="primary" size="mini" style="margin-left: 30px;" @click="showPwd">修改密码</el-button>
    </div>
    <div class="flex"><label>{{$t('userInfo.company')}}</label><span>{{form.company || '--'}}</span></div>
    <div class="flex"><label>{{$t('userInfo.phone')}}</label><span>{{form.phone || '--'}}</span></div>
    <div class="flex"><label>{{$t('userInfo.email')}}</label><span>{{form.email || '--'}}</span></div>
    <div class="flex"><label>{{$t('userInfo.remark')}}</label><span>{{form.remark || '--'}}</span></div>
    <el-dialog
      :title="$t('resetPwd.title')"
      :visible.sync="pwdVisible"
      width="600px"
      append-to-body
      :close-on-click-modal="false"
      :before-close="handleClose"
    >
      <Pwd @handleClose="handleClose" />
    </el-dialog>
  </div>
</template>

<script>
import Pwd from "../pwd/index.vue"
export default {
  components: {Pwd},
  data(){
    return{
      form:{
        userId:'',
        username:'',
        password: '',
        company:'',
        phone:'',
        email:'',
        remark: ''
      },
      pwdVisible: false
    }
  },
  methods:{
    setData(data){
      const {userId, username, company, phone, email, remark} = data || {}
      this.form = {userId, username, company, phone, email, remark, password: '***'}
    },
    showPwd() {
      this.pwdVisible = true
    },
    handleClose() {
      this.pwdVisible = false
    }
  }
}
</script>

<style lang="scss" scoped>
.detail-ul{
  width: 500px;
  margin: 26px auto;
  .flex{
    display: block;
    line-height: 26px;
    padding: 14px 0;
    label{
      display: block;
      width: 100%;
      color: $color_title;
      font-size: 15px;
      font-weight: bold;
      min-width: 150px;
    }
    span{
      display: inline-block;
      color: #425466;
      width: 420px;
      background: #fff;
      border-radius: 4px;
      margin-top: 5px;
      padding: 3px 20px;
      box-shadow: 0 0 15px 0 rgba(89,104,178,0.06), 0 15px 20px 0 rgba(89,104,178,0.06);
    }
    .pwd-span {
      width: 306px;
    }
  }
}
</style>

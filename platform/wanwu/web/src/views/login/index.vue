<template>
  <div class="login">
    <overview :login="login" />
    <div class="login-modal">
      <div class="header__left">
        <!--<img
          style="height: 26px; margin: 0 15px 0 22px"
          :src="home.logoPath ? (basePath + '/user/api' + home.logoPath) : require('@/assets/imgs/wanwu.svg')"
        />
         <span style="font-size: 16px;">{{home.title || ''}}</span>-->
        <!--<div style="margin-left: 10px">
          <ChangeLang :isLogin="true" />
        </div>-->
      </div>
      <div class="login-box">
        <p class="login-header">
          <span style="font-weight: bold">{{$t('login.title')}}</span>
          <span style="margin-left: 20px; font-size: 16px; padding-bottom: 2px">
            {{login.welcomeText || $t('login.welcomeText')}}
          </span>
        </p>
        <div class="login-form">
          <el-form ref="form" class="form" :model="form" label-position="top">
            <el-form-item :label="$t('login.form.username')" class="login-form-item">
              <img class="login-icon" src="./img/user.png" alt="" />
              <el-input
                v-model.trim="form.username"
                :placeholder="$t('common.input.placeholder') + $t('login.form.username')"
              />
            </el-form-item>
            <el-form-item :label="$t('login.form.password')" class="login-form-item">
              <img class="login-icon" src="./img/pwd.png" alt="" />
              <el-input
                :type="isShowPwd ? '' : 'password'"
                class="login-pwd-input"
                v-model.trim="form.password"
                :placeholder="$t('common.input.placeholder') + $t('login.form.password')"
              />
              <img v-if="!isShowPwd" class="pwd-icon" src="./img/showPwd.png" alt="" @click="() => this.isShowPwd = true" />
              <img v-else class="pwd-icon" src="./img/hidePwd.png" alt="" @click="() => this.isShowPwd = false" />
            </el-form-item>
            <el-form-item :label="$t('login.form.code')" class="login-form-item">
              <img class="login-icon" src="./img/code.png" alt="" />
              <el-input
                style="width: calc(100% - 90px)"
                v-model.trim="form.code"
                @keyup.enter.native="addByEnterKey"
                :placeholder="$t('common.input.placeholder') + $t('login.form.code')"
              />
              <span style="display: inline-block; height: 32px; width: 80px; margin-left: 10px; vertical-align: middle">
                <img style="width: 100%; height: 100%" v-if="codeData.b64" :src="codeData.b64" @click="getImgCode" />
              </span>
            </el-form-item>
          </el-form>
          <div class="login-bt">
            <p :class="['primary-bt', {'disabled': isDisabled()}]" :style="`background: ${loginButtonColor} !important`" @click="doLogin">
              {{$t('login.button')}}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import overview from '@/views/layout/overview'
import { mapActions, mapState } from 'vuex'
import { getImgVerCode, getCommonInfo } from "@/api/user"
import { Encrypt, Urlencode } from "../../utils/crypto";
import ChangeLang from "@/components/changeLang.vue"
import { redirectUrl, replaceTitle, replaceIcon } from "@/utils/util"
let urlEncrypt = (data) => {
  return Urlencode(Encrypt(data));
};
export default {
  components: { overview, ChangeLang },
  data(){
    return{
      loginDialogVisable:false,
      form:{
        username:'',
        password:'',
        code: '',
      },
      isShowPwd: false,
      home: {},
      login: {},
      loginButtonColor: '',
      codeData: {
        key: '',
        b64: ''
      },
      basePath: this.$basePath
    }
  },
  computed: {
    ...mapState({
      lang: state => state.user.lang,
    }),
  },
  watch: {
    'lang': {
      handler(val) {
        if (val) {
          /*this.getImgCode()
          this.getLogoInfo()*/
        }
      },
      immediate: true
    }
  },
  created() {
    // 如果已登录，重定向到有权限的页面
    if (localStorage.getItem("access_cert")) redirectUrl()

    this.getImgCode()
    this.getLogoInfo()
  },
  methods:{
    ...mapActions('user', ['LoginIn']),
    isDisabled() {
      const {username, password, code} = this.form
      return !(username && password && code)
    },
    addByEnterKey(e){
      if (e.keyCode === 13) {
        this.doLogin()
      }
    },
    getLogoInfo() {
      getCommonInfo().then(res => {
        const {login, home, tab = {}} = res.data || {}
        this.login = login || {}
        this.home = home || {}
        this.loginButtonColor = this.login.loginButtonColor || '#384BF7'
        replaceTitle(tab.title)
        replaceIcon(tab.logoPath)
      })
    },
    // 获取图片验证码
    async getImgCode() {
      const res = await getImgVerCode()
      this.codeData = res.data || {}
    },
    async doLogin(){
      if (this.isDisabled()) return

      const data = {
        username:this.form.username,
        password: urlEncrypt(this.form.password),
        key: this.codeData.key,
        code: this.form.code
      }

      try {
        await this.LoginIn(data)
      } catch (e) {
        await this.getImgCode()
      }
    },
  }
}
</script>

<style lang="scss" scoped>
.login{
  height: 100%;
}
.login-modal{
  position: fixed;
  top:0;
  bottom:0;
  left:0;
  right: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  .header__left {
    position: relative;
    width: 100%;
    min-width: 500px;
    color: #fff;
    font-weight: bold;
    display: flex;
    align-items: center;
    margin-top: 16px;
    margin-left: 10px;
  }
  .login-box{
    position: absolute;
    width: 400px;
    min-width: 400px;
    height: 460px;
    top:0;
    bottom:0;
    right: 13%;
    margin: auto;
    background: rgba(244,247,255,0.5);
    border-radius: 4px;
    //box-shadow: 0px 5px 30px 0px rgba(5,8,27,0.1);
    //border: 1px solid;
    //border-image: linear-gradient(180deg, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0.8)) 1 1;
    backdrop-filter: blur(10px);
    .login-header{
      color: $color_title;
      text-align: left;
      padding: 30px 30px 0 30px;
      //border-bottom: 1px solid rgba(235,235,235,0.8);
      span {
        display: inline-block;
        vertical-align: bottom;
        font-size: 24px;
      }
    }
    .login-form{
      padding: 30px;
      /deep/ {
        .el-input {
          height: 30px;
          line-height: 36px;
        }
        .el-input__prefix{
          left:14px;
        }
        .el-form-item__label{
          font-size: 12px!important;
          padding: 0!important;
          margin-left: 0!important;
          line-height: 26px!important;
          color: #425466;
        }
        .el-input__inner{
          font-size: 12px !important;
          background: #fff;
          border: none !important;
          padding-left: 50px;
        }
        i {
          color: #666!important;
        }
        .el-icon-lock, .el-icon-user, .el-icon-key {
          font-size: 18px;
        }
        input[type=input]::placeholder{
          color: #B3B1BC;
        }
        input::-webkit-input-placeholder{
          color: #B3B1BC;
        }
        input::-moz-placeholder{   /* Mozilla Firefox 19+ */
          color: #B3B1BC;
        }
        input:-moz-placeholder{    /* Mozilla Firefox 4 to 18 */
          color: #B3B1BC;
        }
        input:-ms-input-placeholder{  /* Internet Explorer 10-11 */
          color: #B3B1BC;
        }
      }
      .login-form-item {
        position: relative;
      }
      .login-icon {
        position: absolute;
        width: 17px;
        z-index: 10;
        top: 13.5px;
        left: 17px;
      }
      .pwd-icon {
        position: absolute;
        width: 17px;
        z-index: 10;
        top: 13.5px;
        right: 17px;
        cursor: pointer;
      }
      .login-bt{
        width: 100%;
        height: 40px;
        line-height: 30px;
        font-size: 14px;
        margin-top: 40px;
        .primary-bt {
          padding: 13px 0;
          height: 40px;
          //background: $color;
          border: none;
          font-size: 14px;
          border-radius: 3px !important;
        }
        .disabled.primary-bt {
          opacity: 0.5;
          cursor: not-allowed;
          border-color: #e9e9eb;
        }
        .operation{
          /*color: #fff;*/
          color: #8d8d8d;
          display: flex;
          margin: 30px 70px;
          span{
            display: block;
            flex:1;
            text-align: center;
            font-size: 12px;
            cursor: pointer;
          }
        }
      }
    }
    .login-pwd-input /deep/ {
      .el-input__inner {
        padding-right: 46px;
      }
    }
  }
}
</style>

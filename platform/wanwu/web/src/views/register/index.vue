<template>
    <div class="login">
        <overview />
        <div class="login-modal">
            <div class="login-box">
                <p class="login-header">{{$t('register.title')}}</p>
                <div class="login-form">
                    <el-form ref="form" class="form" :model="form" label-position="top">
                        <el-form-item :label="$t('login.form.username')">
                            <el-input prefix-icon="el-icon-user" v-model.trim="form.username" :placeholder="$t('common.input.placeholder') + $t('login.form.username')" clearable></el-input>
                        </el-form-item>
                        <el-form-item :label="$t('login.form.password')">
                            <el-input prefix-icon="el-icon-unlock" type="password" v-model.trim="form.password" @keyup.enter.native="addByEnterKey" :placeholder="$t('common.input.placeholder') + $t('login.form.password')" clearable></el-input>
                        </el-form-item>
                    </el-form>
                    <div class="login-bt">
                        <p class="primary-bt" @click="doLogin">{{$t('register.button')}}</p>
                        <p class="operation"><span @click="preBack">{{$t('register.back')}}</span></p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
    import overview from '@/views/layout/overview'
    import { mapActions } from 'vuex'
    import { Encrypt, Urlencode } from "../../utils/crypto";
    let urlEncrypt = (data) => {
        return Urlencode(Encrypt(data));
    };
    export default {
        data(){
            return{
                loginDialogVisable:false,
                form:{
                    username:'',
                    password:'',
                }
            }
        },
        components:{overview},
        methods:{
            ...mapActions('user', ['LoginIn']),
            addByEnterKey(e){
                if (e.keyCode == 13) {
                    this.doLogin()
                }
            },
            async doLogin(){
                let data = {
                    username:this.form.username,
                    password: urlEncrypt(this.form.password),
                };
                let res = await this.LoginIn(data)
            },
            preBack(){
                console.log(this.$route)
                if(this.$route.query.redirect){
                    history.go(-2)
                }else{
                    history.go(-1)
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
        .login-box{
            position: absolute;
            width: 3.4rem;
            min-width: 340px;
            height: 470px;
            top:0;
            bottom:0;
            left:0;
            right: 0;
            margin: auto;
            background: linear-gradient(360deg, rgba(255,255,255,0.8) 0%, rgba(255,255,255,0.5) 100%);
            box-shadow: 0px 5px 30px 0px rgba(5,8,27,0.1);
            border-radius: 5px;
            border: 1px solid;
            border-image: linear-gradient(180deg, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0.8)) 1 1;
            backdrop-filter: blur(10px);
            .login-header{
                height: 80px;
                line-height: 24px;
                font-size: 24px;
                font-weight: 500;
                color: #333333;
                text-align: center;
                border-bottom: 1px solid rgba(235,235,235,0.8);
                padding: .3rem;
            }
            .login-form{
                padding: .45rem .3rem;
                /deep/ {

                    .el-input__prefix{
                        left:14px;
                    }
                    .el-form-item__label{
                        font-size: 12px!important;
                        padding: 0!important;
                        margin-left: 0!important;
                        line-height: 26px!important;
                    }
                    .el-input__inner{
                        font-size: 12px!important;
                        background: rgba(0,0,0,0.08)!important;
                        border: 1px solid transparent!important;
                        padding-left: 50px;
                    }
                    i{
                        color: #666!important;
                    }
                    .el-icon-unlock,.el-icon-user {

                        font-size: 20px;
                    }
                    input[type=input]::placeholder{
                        color: #666;
                    }
                    input::-webkit-input-placeholder{
                        color:#666;
                    }
                    input::-moz-placeholder{   /* Mozilla Firefox 19+ */
                        color:#666;
                    }
                    input:-moz-placeholder{    /* Mozilla Firefox 4 to 18 */
                        color:#666;
                    }
                    input:-ms-input-placeholder{  /* Internet Explorer 10-11 */
                        color:#666;
                    }
                }

                .login-bt{
                    width: 100%;
                    height: 40px;
                    line-height: 30px;
                    font-size: 14px;
                    margin-top: 40px;
                    .primary-bt{
                        padding: 13px 0;
                        height: 40px;
                    }
                    .operation{
                        line-height: 80px;
                        /*color: #fff;*/
                        color: #8d8d8d;
                        display: flex;
                        padding: 0 70px;
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
        }
    }
</style>

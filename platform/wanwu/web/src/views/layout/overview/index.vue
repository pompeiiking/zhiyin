<template>
  <div class="overview">
    <img v-if="backgroundSrc" id="bg" :src="backgroundSrc">
  </div>
</template>

<script>
export default {
  props: {
    login: {}
  },
  data() {
    return {
      backgroundSrc: ''
    }
  },
  watch: {
    'login': {
      handler(val) {
        if (val) {
          this.setLoginBg(val.backgroundPath)
        }
      },
      deep: true
    }
  },
  mounted() {
    this.setLoginBg(this.login.backgroundPath)
  },
  methods:{
    setDefaultImage() {
      this.backgroundSrc = require('../img/login-bg.png')
    },
    setLoginBg(backgroundPath) {
      if (!backgroundPath) {
        this.setDefaultImage()
        return
      }
      this.backgroundSrc = this.$basePath + '/user/api' + backgroundPath
    },
  }
}
</script>

<style lang="scss" scoped>
.overview{
  position: relative;
  height: 100%;
  overflow: hidden;
  //background-color: #000;
  z-index: 10;
  img{
    width: 100%;
    height: 100%;
    object-fit: cover;
    background-size: 100% 100%;
  }
  .overview-desc{
    width: 800px;
    position: absolute;
    bottom:56px;
    left:56px;
    color: #fff;
    text-align: center;
    opacity: .8;
    letter-spacing: 1px;
    .desc{
      font-size: 30px;
      text-align: left;
      p:nth-child(1){
        font-size: 22px;
      }
      p:nth-child(2){
        font-size: 30px;
        margin: 10px 0;
      }
      p:nth-child(3){
        font-size: 18px;
      }
    }
    .tabs{
      display: flex;
      font-size: 27px;
      margin-top: 30px;
      color: #fff;
      .tab{
        width: 1.63rem;
        min-width: 163px;
        margin-right: 20px;
        border: 1px solid #fff;
        cursor: pointer;
        p:nth-child(1){
          font-size: 18px;
          padding: 4px 0 3px 0;
        }
        p:nth-child(2){
          font-size: 12px;
          font-weight: 400;
          padding:0 0 6px 0;
        }
      }
    }
  }
}
</style>

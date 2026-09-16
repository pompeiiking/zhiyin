<template>
  <div class="createDialog">
    <el-dialog
      :title="$t('modelAccess.dialog.title')"
      :visible.sync="dialogVisible"
      width="700px"
      append-to-body
      :close-on-click-modal="false"
      :before-close="handleClose"
    >
      <div>
        <div
          :class="['provider-card-item', {'is-active': item.key === currentObj.key}]"
          v-for="item in providerType"
          :key="item.key"
          @click="showCreate(item)"
        >
          <img class="provider-card-img" :src="item.key === yuanjing ? require('@/assets/imgs/yuanjing.png') : require('@/assets/imgs/openAI.png')" alt="" />
          <div>
            <div class="provider-card-name">{{item.name}}</div>
            <div>
              <span class="provider-card-tag" v-for="it in item.children" :key="it.key">{{it.name}}</span>
            </div>
          </div>
        </div>
      </div>
      <span slot="footer" class="dialog-footer">
        <el-button @click="handleClose">{{$t('common.button.cancel')}}</el-button>
        <el-button type="primary" @click="handleConfirm">{{$t('common.button.confirm')}}</el-button>
      </span>
    </el-dialog>
  </div>
</template>
<script>
import { PROVIDER_TYPE, YUAN_JING } from "../constants"

export default {
  data() {
    return {
      dialogVisible: false,
      providerType: PROVIDER_TYPE,
      currentObj: PROVIDER_TYPE[0],
      yuanjing: YUAN_JING
    }
  },
  methods: {
    openDialog() {
      this.dialogVisible = true
      this.currentObj = PROVIDER_TYPE[0]
    },
    handleClose() {
      this.dialogVisible = false
    },
    showCreate(item) {
      this.currentObj = item
    },
    handleConfirm() {
      this.handleClose()
      this.$emit('showCreate', this.currentObj)
    },
  }
}
</script>
<style lang="scss" scoped>
.provider-card-item {
  margin-bottom: 20px;
  margin-right: 20px;
  border-radius: 8px;
  border: 1px solid #D9D9D9;
  padding: 15px 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  .provider-card-img {
    width: 50px;
    height: 50px;
    object-fit: cover;
    padding: 10px 6px;
    background: #FFFFFF;
    box-shadow: 0 1px 4px 0 rgba(0,0,0,0.15);
    border-radius: 8px;
    border: 0 solid #D9D9D9;
    margin-right: 16px;
  }
  .provider-card-name {
    font-size: 17px;
    font-weight: bold;
    color: $color_title;
    margin-bottom: 10px;
  }
  .provider-card-tag {
    display: inline-block;
    margin-right: 10px;
    font-size: 13px;
    border-radius: 4px;
    padding: 2px 8px;
    background: #ECEEFE;
    color: #6977F9;
  }
}
.provider-card-item:hover, .provider-card-item.is-active {
  box-shadow: 0 1px 4px 0 rgba(0,0,0,0.15);
  border: 1px solid $color;
  .provider-card-name {
    color: $color;
  }
}
</style>
<template>
  <div class="workflow-list">
    <el-dialog :title="$t('list.publishPlugins')" :visible.sync="dialogVisible" width="750" :close-on-click-modal="false">
      <el-form ref="form" :model="publishForm" label-width="120px">
        <el-form-item :label="$t('list.pluginField')+':'">
          <el-checkbox-group v-model="publishForm.pluginFieldArr">
            <el-checkbox :label="$t('list.mapSearch')"></el-checkbox>
            <el-checkbox :label="$t('list.entertainment')"></el-checkbox>
            <el-checkbox :label="$t('list.imageProcessing')"></el-checkbox>
            <el-checkbox :label="$t('list.speechProcessing')"></el-checkbox>
            <el-checkbox :label="$t('list.newsReading')"></el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item :label="$t('list.sampleplugin')+':'">
          <el-input
            type="textarea"
            v-model="publishForm.pluginQuestionExample"
          ></el-input>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="dialogVisible = false">{{$t('list.cancel')}}</el-button>
        <el-button type="primary" @click="doPublish">{{$t('list.confirm')}}</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import { publishWorkFlow } from "@/api/workflow";

export default {
  data() {
    return {
      dialogVisible: false,
      publishForm: {
        pluginFieldArr: [],
        pluginQuestionExample: "",
      },
      row: {},
    };
  },
  created() {},
  methods: {
    openDialog(row) {
      this.row = row;
      this.dialogVisible = true;
    },
    async doPublish() {
      let params = {
        workflowID: this.row.id,
        pluginField: this.publishForm.pluginFieldArr.join(","),
        pluginQuestionExample: this.publishForm.pluginQuestionExample,
      };
      let res = await publishWorkFlow(params);
      if (res.code === 0) {
        this.$message.success(this.$t('list.publicSuccess'));
        this.$emit("refreshTable");
        this.dialogVisible = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
@import "../../../style/workflow.scss";
.workflow-list {
  padding: 40px;
  .table {
  }
}
</style>

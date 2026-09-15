<template>
  <div class="workflow-list">
    <el-dialog
      :title="titleMap[type]"
      :visible.sync="dialogVisible"
      width="750"
      append-to-body
      :close-on-click-modal="false"
    >
      <el-form ref="form" :model="form" label-width="120px" :rules="rules">
        <el-form-item :label="$t('list.pluginName')+':'" prop="configName">
          <el-input
            :placeholder="$t('list.nameplaceholder')"
            v-model="form.configName"
            maxlength="30"
            show-word-limit
          ></el-input>
        </el-form-item>
        <!--<el-form-item label="插件英文名:" prop="configENName">
          <el-input
            type="input"
            placeholder="插件英文名将用于被大模型识别及调用，仅支持英文、数字、下划线，以英文字母开头"
            v-model="form.configENName"
          ></el-input>
        </el-form-item>-->
        <el-form-item :label="$t('list.pluginDesc')+':'" prop="configDesc">
          <el-input
            type="textarea"
            :placeholder="$t('list.descplaceholder')"
            v-model="form.configDesc"
            show-word-limit
            maxlength="600"
          ></el-input>
        </el-form-item>
        <!--v-if="type === 'create'"-->
        <el-form-item v-if="false" :label="$t('list.mapTypeLabel')+':'">
          <el-radio-group v-model="form.isStream">
            <el-radio :label="false">{{$t('list.normalMap')}}</el-radio>
            <!-- <el-radio :label="true">{{$t('list.streamMap')}}</el-radio> -->
          </el-radio-group>
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
import { createWorkFlow,copyExample} from "@/api/workflow";

export default {
  props: {
    type: {
      type: String,
      default: "create",
    },
    editForm: {
      type: Object,
    },
  },
  data() {
    return {
      dialogVisible: false,
      form: {
        configName: "",
        configENName: "",
        configDesc: "",
        isStream: false
      },
      titleMap: {
        edit: this.$t('list.editplugin'),
        create:this.$t('list.createplugin'),
        clone: this.$t('list.copy_Demo'),
      },
      workflowID: "",
      rules: {
        configName: [
          { required: true, message: this.$t('list.nameRules'), trigger: "blur" },
          {
            validator: (rule, value, callback) => {
              if (/^[A-Za-z0-9.\u4e00-\u9fa5_-]+$/.test(value)) {
                callback();
              } else {
                callback(
                  new Error(
                    this.$t('list.nameplaceholder')
                  )
                );
              }
            },
            trigger: "change",
          },
          {
            max:30,message:this.$t('list.pluginNameRules'),trigger: "blur"
          }
        ],
        configENName: [
          { required: false, message: this.$t('list.enNameRules'), trigger: "blur" },
          {
            validator: (rule, value, callback) => {
                if(!value){
                    callback();
                }else{
                    if (/^[a-zA-Z][a-zA-Z0-9_]*$/.test(value)) {
                        callback();
                    } else {
                        callback(
                            new Error(this.$t('list.enNameErrorRules'))
                        );
                    }
                }

            },
            trigger: "change",
          },
        ],
        configDesc: [
          { required: true, message: this.$t('list.pluginDescRules'), trigger: "blur" },
          { max: 600, message:this.$t('list.pluginLimitRules'),trigger: "blur"}
        ],
      },
    };
  },
  methods: {
    openDialog(row) {
      if (this.type === "edit" && this.editForm) {
        this.form = this.editForm;
      } else {
        this.clearForm();
      }
      if(row){
        this.workflowID = row.id;
      }
      this.dialogVisible = true;
      this.$nextTick(()=>{
          this.$refs['form'].clearValidate()
      })
    },
    clearForm() {
      this.form = {
        configName: "",
        configENName: "",
        configDesc: "",
        isStream:false
      };
    },
    async doPublish() {
      let valid = false;
      await this.$refs.form.validate((vv) => {
        if (vv) {
          valid = true;
        }
      });
      if (!valid) return;
      if (this.type == "edit") {
        this.$emit("save");
        this.dialogVisible = false;
        return;
      }
      if (this.type == "clone") {
        this.form.workflowID = this.workflowID;
        let res = await copyExample(this.form);
        if (res.code === 0) {
          this.$message.success(this.$t('list.copySuccess'));
          this.dialogVisible = false;
          let { workflowID } = res.data;
          this.$router.push({ path: "/workflow", query: { id: workflowID } });
        }
        return;
      }
      let res = await createWorkFlow(this.form);
      if (res.code === 0) {
        this.$message.success(this.$t('list.createSuccess'));
        this.dialogVisible = false;
        let { workflowID } = res.data;
        let querys = { id:workflowID };
        if(this.form.isStream){
          querys.isStream = true
        }
        this.$router.push({ path: "/workflow", query: querys });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
@import "../../../style/workflow.scss";
.workflow-list {
  position: absolute;
}
</style>

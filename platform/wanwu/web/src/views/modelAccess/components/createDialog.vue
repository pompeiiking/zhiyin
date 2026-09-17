<template>
  <div class="createDialog">
    <!--:title="isEdit ? $t('modelAccess.dialog.edit') : $t('modelAccess.dialog.create')"-->
    <el-dialog
      :title="provider.name || ''"
      :visible.sync="dialogVisible"
      width="760px"
      append-to-body
      :close-on-click-modal="false"
      :before-close="handleClose"
    >
      <el-form :model="{...createForm}" :rules="rules" ref="createForm" label-width="110px" class="createForm form">
        <el-form-item :label="$t('modelAccess.table.modelType')" prop="modelType">
          <el-radio-group :disabled="isEdit" v-model="createForm.modelType">
            <el-radio v-for="item in modelType" :label="item.key" :key="item.key">
              {{item.name}}
            </el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('modelAccess.table.modelName')" prop="model">
          <el-input :disabled="isEdit" v-model="createForm.model" :placeholder="$t('common.input.placeholder')"></el-input>
        </el-form-item>
        <el-form-item :label="$t('modelAccess.table.modelDisplayName')" prop="displayName">
          <el-input v-model="createForm.displayName" :placeholder="$t('common.hint.modelName')"></el-input>
        </el-form-item>
        <el-form-item :label="$t('modelAccess.table.picPath')" prop="avatar">
          <el-upload
            class="avatar-uploader"
            action=""
            name="files"
            :show-file-list="false"
            :http-request="handleUploadImage"
            :on-error="handleUploadError"
            accept=".png,.jpg,.jpeg"
          >
            <img
              class="upload-img"
              :src="createForm.avatar && createForm.avatar.path ? basePath + '/user/api/' + createForm.avatar.path : defaultLogo"
            />
            <!--<span style="margin-left: 12px; color: #606266 !important;" v-if="createForm.avatar && createForm.avatar.path">
              {{createForm.avatar.path}}
            </span>-->
            <span class="upload-hint">
              可上传 .png、jpg、jpeg 文件
            </span>
          </el-upload>
        </el-form-item>
        <el-form-item v-if="createForm.modelType === llm" label="Function Call" prop="functionCalling">
          <el-select
            v-model="createForm.functionCalling"
            :placeholder="$t('common.select.placeholder')"
            style="width: 100%"
          >
            <el-option
              v-for="item in functionCalling"
              :key="item.key"
              :label="item.name"
              :value="item.key"
            >
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('modelAccess.table.apiKey')" prop="apiKey">
          <el-input v-model="createForm.apiKey" :placeholder="$t('common.input.placeholder')"></el-input>
        </el-form-item>
        <el-form-item :label="$t('modelAccess.table.inferUrl')" prop="endpointUrl">
          <el-input v-model="createForm.endpointUrl" :placeholder="$t('common.hint.inferUrl')"></el-input>
        </el-form-item>
        <el-form-item :label="$t('modelAccess.table.publishTime')" prop="publishDate">
          <el-date-picker
            v-model="createForm.publishDate"
            type="date"
            value-format="yyyy-MM-dd"
            :placeholder="$t('common.select.placeholder')"
          >
          </el-date-picker>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="handleClose">{{$t('common.button.cancel')}}</el-button>
        <el-button type="primary" @click="handleSubmit">{{$t('common.button.confirm')}}</el-button>
      </span>
    </el-dialog>
  </div>
</template>
<script>
import { addModel, editModel } from "@/api/modelAccess"
import { uploadAvatar } from "@/api/user"
import { MODEL_TYPE, PROVIDER_OBJ, FUNC_CALLING, LLM, DEFAULT_CALLING } from "../constants"

export default {
  data() {
    const validateUrls = (rule, value, callback) => {
      const reg = /^(http|ftp|https):\/\/[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&:/~\+#]*[\w\-\@?^=%&/~\+#])?$/

      if (!reg.test(value)) {
        callback(new Error(this.$t('modelAccess.hint.urlError')))
      } else {
        return callback()
      }
    }
    return {
      basePath: this.$basePath,
      defaultLogo: require("@/assets/imgs/bg-logo.png"),
      dialogVisible: false,
      modelType: MODEL_TYPE,
      functionCalling: FUNC_CALLING,
      llm: LLM,
      createForm: {
        model: '',
        displayName: '',
        endpointUrl: '',
        apiKey: '',
        modelType: LLM,
        avatar: {
          key: '',
          path: ''
        },
        publishDate: '',
        functionCalling: DEFAULT_CALLING
      },
      rules: {
        model: [
          { required: true, message: this.$t('common.input.placeholder'), trigger: 'blur'},
          // { min: 2, max: 50, message: this.$t('common.hint.modelNameLimit'), trigger: 'blur'},
          // { pattern: /^(?!_)[a-zA-Z0-9-_.\u4e00-\u9fa5]+$/, message: this.$t('common.hint.modelName'), trigger: "blur"}
        ],
        displayName: [
          { pattern: /^(?!_)[a-zA-Z0-9-_.\u4e00-\u9fa5]+$/, message: this.$t('common.hint.modelName'), trigger: "blur"},
          { min: 2, max: 50, message: this.$t('common.hint.modelNameLimit'), trigger: 'blur'},
        ],
        modelType: [{ required: true, message: this.$t('common.select.placeholder'), trigger: "change"}],
        endpointUrl: [
          { required: true, message: this.$t('common.input.placeholder'), trigger: "blur"},
          { validator: validateUrls, trigger: "blur"}
        ],
      },
      row: {},
      provider: {},
      isEdit: false,
    }
  },
  methods: {
    uploadAvatar(file, key) {
      const formData = new FormData()
      const config = {headers: { "Content-Type": "multipart/form-data" }}
      formData.append(key, file)
      return uploadAvatar(formData, config)
    },
    handleUploadImage(data) {
      if (data.file) {
        this.uploadAvatar(data.file, 'avatar').then(res => {
          const {key, path} = res.data || {}
          this.createForm.avatar = {key, path}
        })
      }
    },
    handleUploadError() {
      this.$message.error(this.$t('common.message.uploadError'))
    },
    formatValue(data) {
      for (let key in this.createForm) {
        this.createForm[key] = data ? (data[key] || '') : ''
      }
    },
    openDialog(title, row){
      this.provider = {key: title, name: PROVIDER_OBJ[title]}
      this.dialogVisible = true

      this.isEdit = Boolean(row)
      console.log(row, title, '-----------------row')
      if (this.isEdit) {
        this.row = row || {}
        this.formatValue(row)
      }
    },
    handleClose(){
      this.dialogVisible = false
      this.formatValue({modelType: LLM, functionCalling: DEFAULT_CALLING, avatar: { key: '', path: ''}})
      this.$refs.createForm.resetFields()
      this.$refs.createForm.clearValidate()
    },
    handleSubmit() {
      this.$refs.createForm.validate(async (valid) => {
        if (valid) {
          const {apiKey, endpointUrl, functionCalling, modelType} = this.createForm
          const functionCallingObj = modelType === LLM ? {functionCalling} : {}
          const form = {
            ...this.createForm,
            provider: this.provider.key || '',
            config: {
              apiKey,
              endpointUrl,
              ...functionCallingObj
            }
          }
          delete form.apiKey
          delete form.endpointUrl
          delete form.functionCalling

          const res = this.isEdit
            ? await editModel({...form, modelId: this.row.modelId})
            : await addModel(form)
          if (res.code === 0) {
            this.$message.success(this.$t('common.message.success'))
            this.handleClose()
            this.$emit('reloadData')
          }
        }
      })
    }
  }
}
</script>
<style scoped>
.createForm {
  padding: 0 45px 0 20px;
  .avatar-uploader {
    .upload-img {
      object-fit: cover;
      width: 80px;
      height: 80px;
      border-radius: 8px;
      border: 1px solid #DCDFE6;
      display: inline-block;
      vertical-align: middle;
    }
    .upload-hint {
      display: inline-block;
      margin-left: 12px;
      color: #909399 !important;
    }
  }
}
</style>
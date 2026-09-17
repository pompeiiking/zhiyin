<template>
  <div class="add-dialog">
    <el-dialog
      title="添加MCP服务"
      :visible.sync="dialogVisible"
      width="50%"
      :show-close="false"
      :close-on-click-modal="false"
    >
      <div>
        <el-form
          :model="ruleForm"
          :rules="rules"
          ref="ruleForm"
          label-width="130px"
          class="demo-ruleForm"
        >
          <el-form-item label="服务名称" prop="name">
            <el-input v-model="ruleForm.name"></el-input>
          </el-form-item>
          <el-form-item label="服务来源" prop="from">
            <el-input v-model="ruleForm.from"></el-input>
          </el-form-item>
          <el-form-item label="功能描述" prop="desc">
            <el-input
              type="textarea"
              rows="5"
              v-model="ruleForm.desc"
            ></el-input>
          </el-form-item>
          <el-form-item label="MCP sseUrl" prop="sseUrl">
            <el-input v-model="ruleForm.sseUrl"></el-input>
          </el-form-item>
          <el-form-item label=" " style="text-align: right">
            <el-button
              type="primary"
              size="mini"
              @click="handleTools"
              :disabled="isGetMCP"
            >
              获取MCP工具
            </el-button>
          </el-form-item>
        </el-form>
        <el-divider v-if="mcpList.length > 0"></el-divider>
        <ul class="mcpList" v-if="mcpList.length > 0">
          <li v-for="(item, index) in mcpList" :key="index">{{ item.name }}</li>
        </ul>
      </div>
      <span slot="footer" class="dialog-footer">
        <el-button @click="handleCancel" size="mini">取 消</el-button>
        <el-button
          type="primary"
          size="mini"
          :disabled="mcpList.length === 0"
          @click="submitForm('ruleForm')"
        >
          确定发布
        </el-button>
      </span>
    </el-dialog>
  </div>
</template>
<script>
import { getTools, setCreate } from "@/api/mcp.js";
import { isValidURL } from "@/utils/util";

export default {
  props: ["dialogVisible"],
  data() {
    const validateUrl = (rule, value, callback) => {
      if (!isValidURL(value)) {
        callback(new Error("请再次检查Server Url格式"));
      } else {
        callback();
      }
    };
    return {
      mcpList: [],
      ruleForm: {
        name: "",
        from: "",
        sseUrl: "",
        desc: "",
      },
      rules: {
        name: [{ required: true, message: "请输入服务名称", trigger: "blur" }],
        from: [
          { required: true, message: "请输入服务来源", trigger: "blur" },
        ],
        sseUrl: [
          {
            required: true,
            message: "请输入服务Server Url",
            trigger: "blur",
          },
          { validator: validateUrl, trigger: "blur" },
        ],
        desc: [
          {
            required: true,
            message: "请输入功能描述",
            trigger: "blur",
          },
        ],
      },
    };
  },
  methods: {
    handleCancel() {
      this.$emit("handleClose", false);
      this.$refs["ruleForm"].resetFields();
      this.mcpList = [];
    },
    submitForm(formName) {
      this.$refs[formName].validate((valid) => {
        if (valid) {
          setCreate(this.ruleForm)
            .then((res) => {
              if(res.code === 0){
                this.$message.success("发布成功")
                this.handleCancel()
              }
            })
        } else {
          return false;
        }
      });
    },
    handleTools() {
      getTools({
        serverUrl: this.ruleForm.sseUrl,
      }).then((res) => {
        this.mcpList = res.data.tools;
      })
    },
  },
  computed: {
    isGetMCP() {
      if (!isValidURL(this.ruleForm.sseUrl)) {
        return true;
      } else {
        return false;
      }
    },
  },
};
</script>
<style lang="scss" scoped>
.add-dialog {
  .el-button.is-disabled {
    &:active {
      background: transparent !important;
      border-color: #ebeef5 !important;
    }
  }
  .mcpList {
    list-style: none;
    li {
      padding: 10px;
      border: 1px solid #ddd;
      border-radius: 5px;
      margin-bottom: 10px;
      background: #fff;
    }
  }
}
</style>
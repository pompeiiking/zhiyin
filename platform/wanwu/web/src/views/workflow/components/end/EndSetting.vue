<template>
  <div class="code">
    <!--输出-->
    <div class="node-params">
      <div class="params-type">
        <i class="el-icon-caret-bottom"></i>
        <span class="params-type-span">输出</span>
        <i class="el-icon-plus add-icon" @click="preAddOutputParams"></i>
      </div>
      <div class="params-form">
        <div class="form-item">
          <div class="item">参数名</div>
          <div class="item">类型</div>
          <div class="item">值</div>
        </div>
        <div v-for="(n, i) in nodeData.data.inputs" :key="`${i}ipt`">
          <div class="form-item">
            <el-input class="item" size="mini" v-model="n.name"></el-input>
            <el-select
              class="item"
              size="mini"
              popper-class="workflow-select"
              v-model="n.value.type"
              @change="(val) => selectTypeChange(val, i)"
            >
              <el-option value="generated" label="String"></el-option>
              <el-option value="ref" label="引用"></el-option>
              <!--<el-option value="Integer" label="Integer"></el-option>
                    <el-option value="Boolean" label="Boolean"></el-option>
                    <el-option value="Number" label="Number"></el-option>-->
            </el-select>
            <!--非引用-->
            <el-input
              class="item last-item"
              size="mini"
              v-if="n.value.type === 'generated'"
              v-model="n.value.content"
            ></el-input>
            <!--引用-->
            <!--<el-select class="item last-item" size="mini" v-show="n.value.type==='ref'" v-model="n.value.content.ref_var_name">
                    <el-option v-for="(m,j) in preNodeOutputs"
                               :label="m.newLabel"
                               :value="m.newContent"></el-option>
                  </el-select>-->
            <el-popover placement="bottom" width="260" trigger="click">
              <div>
                <div
                  class="popover-select-item"
                  v-for="(m, j) in preAllNode"
                  :key="`${j}pn`"
                >
                  <p class="node-name">
                    <i class="el-icon-caret-bottom"></i>{{ m.name }}
                  </p>
                  <div
                    class="node-content"
                    v-for="(p, l) in m.data.data.outputs"
                    :key="`${l}otp`"
                    @click="refValueClick(n, i, m, p, l)"
                  >
                    <span class="name">{{ p.name }}</span>
                    <span class="type">{{ p.type }}</span>
                  </div>
                </div>
              </div>
              <div
                slot="reference"
                v-show="n.value.type === 'ref'"
                class="item last-item popover-select"
              >
                {{ n.newRefContent }}
              </div>
            </el-popover>
            <i
              class="el-icon-remove-outline del-icon"
              v-if="nodeData.data.inputs.length > 1"
              @click="preDelInputsParams(i)"
            ></i>
          </div>
        </div>
      </div>
      <p v-if="nodeData.validate && JSON.parse(nodeData.validate).outputValidate === false" class="workflow-errormsg">{{JSON.parse(nodeData.validate).message}}</p>
    </div>
  </div>
</template>

<script>
import nodeMethod from "@/views/workflow/mixins/nodeMethod";

export default {
  data() {
    return {};
  },
  created() {

  },
  mixins: [nodeMethod],
  methods: {
    /*输出*/
    preAddOutputParams() {
      let itemObj = {
        desc: "",
        list_schema: null,
        name: "",
        object_schema: null,
        required: false,
        type: "string",
        value: {
          content: {
            ref_node_id: "",
            ref_var_name: "",
          },
          type: "ref",
        },
      };
      this.$set(
        this.nodeData.data.inputs,
        this.nodeData.data.inputs.length,
        itemObj
      );
    },
  },
};
</script>

<style lang="scss" scoped>
.node-params {
  padding: 10px;
  background-color: #f9f9fb;
  color: #151b26;
  border-radius: 10px;
  margin-top: 20px;
  .params-type {
    position: relative;
    .add-icon {
      position: absolute;
      right: 20px;
      top: 10px;
      font-size: 16px;
      cursor: pointer;
    }
    .params-type-span {
      margin-left: 10px;
    }
  }
  .params-content {
    margin-top: 8px;
    min-height: 40px;
    .params-content-item {
      span {
        font-size: 12px;
      }
      span:nth-child(1) {
        color: #876300;
      }
      span:nth-child(2) {
        margin-left: 6px;
        height: 20px;
        padding: 0 5px;
        white-space: nowrap;
        border-radius: 4px;
        background-color: #e8e9eb;
        color: #5c5f66;
      }
      span:nth-child(3) {
        margin-left: 6px;
        height: 20px;
        padding: 0 5px;
        white-space: nowrap;
      }
    }
  }
  .params-form {
    margin-top: 10px;
    .form-item {
      display: flex;
      gap: 5px;
      margin: 5px 0;
      .item {
        font-size: 12px;
        flex: 1;
      }
      .last-item {
        flex: 2;
        overflow:hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .del-icon {
        line-height: 30px;
      }
    }
  }
}
.code {
  height: calc(100vh - 150px);
  overflow-y: auto;
  border-bottom: 1px solid #e8e9eb;
  .code-title {
    margin-bottom: 10px;
  }
  .code-plugin {
    background-color: #333;
    color: #fff;
    height: 260px;
    margin-bottom: 20px;
    text-align: center;
    line-height: 60px;
    border-radius: 4px;
  }
  .edit {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    color: #151b26;
    border: 1px solid #e8e9eb;
    padding: 8px 0;
    border-radius: 6px;
    cursor: pointer;
    i {
      margin-right: 6px;
    }
  }
  .edit-modal {
    position: fixed;
    width: 60%;
    height: calc(100vh - 40px);
    right: 400px;
    top: 20px;
    bottom: 20px;
    background-color: #070c1480;
    z-index: 10;
  }
}
</style>

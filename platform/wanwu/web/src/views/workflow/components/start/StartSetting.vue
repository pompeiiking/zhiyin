<template>
  <div class="setting">
    <!--开始节点输入-->
    <div class="node-params" v-if="nodeData.data.outputs.length">
      <div class="params-type">
        <i class="el-icon-caret-bottom"></i>
        <span class="params-type-span">输入</span>
      </div>
      <div class="start-form">
        <div
          class="start-form-item"
          v-for="(n, i) in nodeData.data.outputs"
          :key="`${i}opts`"
        >
          <i
            v-if="nodeData.data.outputs.length > 1"
            class="el-icon-remove-outline del-icon"
            @click="preDelStartInputs(i)"
          ></i>
          <div class="item">
            <label class="item-label">参数名:</label>
            <div class="item-content">
              <el-input class="item" size="mini" v-model="n.name"></el-input>
            </div>
          </div>
          <div class="item">
            <label class="item-label">变量类型:</label>
            <div class="item-content">
              <el-select
                class="item"
                size="mini"
                v-model="n.type"
                @change="change(n.type, i)"
                popper-class="workflow-select"
              >
                <el-option value="string" label="String"></el-option>
                <el-option value="array" label="Array"></el-option>
                <el-option value="fileUrl" label="FileUrl"></el-option>
                <!--- <el-option value="Integer" label="Integer"></el-option>
                                <el-option value="Boolean" label="Boolean"></el-option>
                                <el-option value="Number" label="Number"></el-option>
                                <el-option value="ref" label="引用"></el-option>
                                -->
              </el-select>
            </div>
          </div>
          <div class="item last-item">
            <label class="item-label">参数描述:</label>
            <div class="item-content">
              <el-input
                type="textarea"
                class="item"
                size="mini"
                :rows="4"
                v-model="n.desc"
              ></el-input>
            </div>
          </div>
        </div>
      </div>
      <p
        v-if="
          nodeData.validate &&
          JSON.parse(nodeData.validate).inputValidate === false
        "
        class="workflow-errormsg"
      >
        {{ JSON.parse(nodeData.validate).message }}
      </p>
    </div>
    <el-button
      class="start-params-addbt"
      size="small"
      @click="preAddStartInputs"
      ><i class="el-icon-plus"></i>&nbsp;添加参数</el-button
    >
  </div>
</template>

<script>
export default {
  props: ["graph", "node"],
  data() {
    return {
      preNode: {},
      preNodeOutputs: {},
      nodeData: {},
    };
  },
  created() {
    this.nodeData = this.node.data;
  },
  methods: {
    change(val, index) {
      console.log(val, index);
      if (val == "string") {
        this.nodeData.data.outputs[index].list_schema = "";
      } else {
        this.nodeData.data.outputs[index].list_schema = {
          type: "string",
          object_schema: null,
          list_schema: null,
        };
      }
    },
    preAddStartInputs() {
      let item = {
        desc: "",
        list_schema: null,
        name: "",
        object_schema: null,
        required: true,
        type: "string",
        value: {
          content: "",
          type: "generated",
        },
      };
      this.$set(
        this.nodeData.data.outputs,
        this.nodeData.data.outputs.length,
        item
      );
    },
    preDelStartInputs(index) {
      this.nodeData.data.outputs.splice(index, 1);
    },
    setConfig(node) {
      this.visible = true;
      //console.log('setConfig: ',node)
      this.node = node;
      this.nodeData = node.data;

      this.preNode = node.data.preNode;

      if (node.data.preNode) {
        this.preNodeOutputs = node.data.preNode.data.outputs.map((m, j) => {
          return {
            ...m,
            newLabel: `${this.preNode.name}/${m.name}(${m.type})`,
            newContent: m.name, //JSON.stringify({ "ref_node_id": this.preNode.id, "ref_var_name": m.name })
          };
        });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.workflow-select {
  span {
    font-size: 12px;
  }
}
.setting {
  height: calc(100vh - 200px);
  overflow-y: auto;
  .node-params {
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
    .start-form {
      .start-form-item {
        position: relative;
        background-color: #f9f9fb;
        margin-top: 10px;
        padding: 20px;
        border-radius: 6px;
        .del-icon {
          position: absolute;
          top: 8px;
          right: 8px;
          padding: 2px;
        }
        .item {
          margin-top: 5px;
          display: flex;
          align-items: center;
          .item-label {
            width: 80px;
            font-size: 12px;
          }
          .item-content {
            flex: 1;
          }
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
          flex: 1;
        }
        .last-item {
          flex: 2;
        }
        .del-icon {
          line-height: 30px;
        }
      }
    }
  }
  .start-params-addbt {
    width: 100%;
    margin-top: 20px;
  }
}
</style>

<template>
  <div class="node-config" v-if="visible">
    <div class="node-box">
      <div class="config-header">
        <i class="el-icon-close close-icon" @click="preClose"></i>
        <img class="header-icon" :src="node.store.data.icon" />
        <span v-if="!editStatus" class="header-name">{{ nodeData.name }}</span>
        <el-input
          v-else
          id="edit_name"
          class="edit-input"
          size="mini"
          v-on:blur="onBlur"
          v-model="nodeData.name"
        ></el-input>

        <i class="el-icon-edit edit-icon" @click="preEditName"></i>
        <p class="desc">{{ nodeDescConfig[nodeData.type] }}</p>
      </div>

      <!--开始节点-->
      <StartSetting
        v-if="nodeData.type === 'StartNode'"
        ref="start"
        :graph="graph"
        :node="node"
      />

      <!--api-->
      <ApiSetting
        v-show="nodeData.type === 'ApiNode'"
        ref="api"
        :graph="graph"
        :node="node"
        :key="datekey"
      />
      <!--<GuiSetting
        v-show="nodeData.type === 'GUIAgentNode'"
        ref="api"
        :graph="graph"
        :node="node"
        :key="datekey"
      />-->
      <!--代码-->
      <CodeSetting
        v-show="nodeData.type === 'PythonNode'"
        ref="code"
        :graph="graph"
        :node="node"
        :key="datekey"
      />

      <!--大模型-->
      <ModelSetting
        v-show="nodeData.type === 'LLMNode'"
        ref="code"
        :graph="graph"
        :node="node"
        :key="datekey"
      />

      <!--大模型-->
      <ModelStreamSetting
        v-show="nodeData.type === 'LLMStreamingNode'"
        ref="model"
        :graph="graph"
        :node="node"
        :key="datekey"
      />

      <!--分支器-->
      <SwitchSetting
        v-show="nodeData.type === 'SwitchNode'"
        ref="code"
        :graph="graph"
        :node="node"
        :key="datekey"
        @preAddSwitch="preAddSwitch"
      />

      <!--知识库-->
      <RagSetting
        v-show="nodeData.type === 'RAGNode'"
        ref="rag"
        :graph="graph"
        :node="node"
        :key="datekey"
      />

      <!--文件生成-->
      <FilegenerateSetting
        v-show="nodeData.type === 'FileGenerateNode'"
        ref="filegenerate"
        :graph="graph"
        :node="node"
        :key="datekey"
      />

      <!--文件解析-->
      <FileparseSetting
        v-show="nodeData.type === 'FileParseNode'"
        ref="fileparse"
        :graph="graph"
        :node="node"
        :key="datekey"
      />

      <!--mcp-->
      <McpSetting
        v-show="nodeData.type === 'MCPClientNode'"
        ref="mcp"
        :graph="graph"
        :node="node"
        :key="datekey"
      />

      <!--意图识别-->
      <IntentionSetting
        v-show="nodeData.type === 'IntentionNode'"
        ref="intention"
        :graph="graph"
        :node="node"
        :models="models"
        :key="datekey"
      />

      <!--结束节点-->
      <EndSetting
        v-if="
          nodeData.type === 'EndNode' || nodeData.type === 'EndStreamingNode'
        "
        ref="end"
        :graph="graph"
        :node="node"
      />
    </div>
  </div>
</template>

<script>
import StartSetting from "./start/StartSetting";
import CodeSetting from "./code/CodeSetting";
import ApiSetting from "./api/ApiSetting";
import EndSetting from "./end/EndSetting";
import ModelSetting from "./model/ModelSetting";
import ModelStreamSetting from "./modelstream/ModelSetting";
import SwitchSetting from "./switch/SwitchSetting";
import RagSetting from "./rag/RagSetting";
import GuiSetting from "./gui/GuiSetting";
import FilegenerateSetting from "./filegenerate/index.vue";
import FileparseSetting from "./fileparse/index.vue";
import McpSetting from "./mcp/setting.vue";
import IntentionSetting from "./intention/index.vue";

import { nodeDescConfig } from "../mock/nodeConfig";

import {getModels} from "@/api/workflow";

export default {
  components: {
    StartSetting,
    CodeSetting,
    ApiSetting,
    SwitchSetting,
    EndSetting,
    ModelSetting,
    RagSetting,
    // GuiSetting,
    ModelStreamSetting,
    FilegenerateSetting,
    FileparseSetting,
    McpSetting,
    IntentionSetting,
  },
  data() {
    return {
      visible: false,
      nodeDescConfig: nodeDescConfig,
      preNode: {},
      preNodeOutputs: {},
      node: {},
      nodeData: {},
      startInputs: [],
      datekey: Date.now(),
      timer: null,
      editStatus: false,
      models:[],
      graph: ''
    };
  },
  created(){
    this.getModels()
  },
  watch: {
    "nodeData.id": {
      handler: function (newVal, oldVal) {
        console.log("watch:", newVal);
        this.$forceUpdate();
      },
      deep: true,
    },
    // "nodeData.name":{
    //   handler: function (newVal, oldVal) {
    //     this.node.name = newVal;
    //     console.log(this.node,182773)
    //   },
    // },
    // 实时保存
    "node.data": {
      handler: function (newVal, oldVal) {
        if (this.timer) {
          clearTimeout(this.timer);
        }
        let validate = this.validateNode(newVal.data);
        newVal.validate = JSON.stringify(validate);
        if (!validate.inputValidate || !validate.outputValidate) {
          return;
        }
        this.timer = setTimeout(() => {
          this.$emit("save");
        }, 1500);
      },
      deep: true,
    },
  },
  methods: {
    validateNode(data) {
      let inputMap = {};
      let outputMap = {};
      let inputValidate = true;
      let outputValidate = true;
      data.inputs &&
        data.inputs.forEach((item) => {
          if (inputMap[item.name] || (data.modelForm && data.modelForm.hasOwnProperty(item.name))) {
            inputValidate = false;
          } else {
            inputMap[item.name] = item.name;
          }
        });

      data.outputs &&
        data.outputs.forEach((item) => {
          if (outputMap[item.name]) {
            outputValidate = false;
          } else {
            outputMap[item.name] = item.name;
          }
        });
      return {
        outputValidate,
        inputValidate,
        message: inputValidate && outputValidate ? "" : "当前变量名重复",
      };
    },
    preEditName() {
      this.editStatus = true;
      this.$nextTick(() => {
        let _input = document.getElementById("edit_name");
        _input.focus();
      });
    },
    onBlur() {
      this.editStatus = false;
      this.$emit("save");
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
      this.$set(this.startInputs, this.startInputs.length, item);
    },
    setConfig(graph, node) {
      this.node = {};
      console.log("drawer node:", node);
      this.visible = true;
      this.graph = graph;

      this.node = node;
      this.nodeData = node.data;
      this.datekey = Date.now();
      // 居中连接桩
      setTimeout(() => {
        let ee = document.querySelector(
          `.x6-node[data-cell-id="${this.node.id}"] foreignObject body .dag-node`
        );
        this.node.resize(ee.offsetWidth, ee.offsetHeight);
        if (node.data.type === "SwitchNode") {
          let yList = [];
          const ports = node.port.ports;
          if (ports[0].group !== "absolute") {
            ports.shift();
          }
          const dom = document
            .getElementById(node.id)
            .getElementsByClassName("node-params");
          for (let i = 0; i < dom.length; i++) {
            if (i === 0) {
              yList[i] = 55 + dom[i].clientHeight / 2;
            } else {
              yList[i] =
                yList[i - 1] +
                dom[i - 1].clientHeight / 2 +
                dom[i].clientHeight / 2 +
                10;
            }
            node.portProp(ports[i].id, "args/y", yList[i]);
          }
        } else {
          const ports = document.querySelectorAll(".x6-port-body");
          for (let i = 0, len = ports.length; i < len; i = i + 1) {
            ports[i].style.visibility = "visible";
          }
        }
      }, 50);
    },
    preClose() {
      this.visible = false;
    },
    preAddSwitch(index) {
      this.$emit("preAddSwitch", index);
    },
    getModels() {
      // getModels().then((res) => {
      //    const {list} = res.data || {}
      //    const models = list ? list.map((item) => ({...item, modelName: item.displayName || item.model})) : []
      //    this.models = models
      // });
    },
  },
};
</script>

<style lang="scss" scoped>
.node-config {
  position: fixed;
  z-index: 10;
  width: 450px;
  height: calc(100vh - 42px);
  //top: 20px;
  bottom: 0;
  right: 0;
  padding: 20px;
  border-left: 1px solid #ddd;
  background-color: #fff;
  overflow: auto;
  .node-box {
    display: flex;
    flex-direction: column;
  }
}
.config-header {
  position: relative;
  .close-icon {
    position: absolute;
    right: 0;
    top: 0;
    font-size: 16px;
    padding: 2px;
    cursor: pointer;
  }
  .header-icon {
    vertical-align: middle;
    width: 26px;
    margin-right: 10px;
    object-fit: contain;
  }
  .header-name {
  }
  .desc {
    font-size: 12px;
    padding: 10px 0 20px 0;
    color: #151b26;
    border-bottom: 1px solid #e8e9eb;
  }
  .edit-icon {
    position: absolute;
    right: 40px;
    top: 4px;
    cursor: pointer;
  }
  .edit-input {
    width: 200px;
  }
}
/deep/.popover-select{
  width: 183px;
  -webkit-appearance: none;
  background-color: #fff;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
  box-sizing: border-box;
  color: #606266;
  display: inline-block;
  height: 28px;
  line-height: 28px;
  outline: 0;
  padding: 0 15px;
  transition: border-color .2s cubic-bezier(.645,.045,.355,1);
  cursor: pointer;
  vertical-align: middle;
  display: inline-block;
}
</style>

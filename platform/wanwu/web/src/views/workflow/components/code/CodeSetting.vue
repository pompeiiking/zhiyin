<template>
  <div class="code_box">
    <!--输入-->
    <div class="node-params">
      <div class="params-type">
        <i class="el-icon-caret-bottom"></i>
        <span class="params-type-span">输入</span>
        <i class="el-icon-plus add-icon" @click="preAddInputParams"></i>
      </div>
      <!--form-->
      <div class="params-form">
        <div class="form-item">
          <div class="item">参数名</div>
          <div class="item">类型</div>
          <div class="item last-item">值</div>
        </div>
        <div
          class="form-item"
          v-for="(n, i) in nodeData.data.inputs"
          :key="`${i}ipt`"
        >
          <el-input class="item" size="mini" v-model="n.name"></el-input>
          <el-select
            class="item"
            size="mini"
            popper-class="workflow-select"
            v-model="n.value.type"
            @change="(val) => selectTypeChange(val, i)"
          >
            <el-option value="generated" label="String"></el-option>
            <!-- <el-option value="Integer" label="Integer"></el-option>
                        <el-option value="Boolean" label="Boolean"></el-option>
                        <el-option value="Number" label="Number"></el-option>-->
            <el-option value="ref" label="引用"></el-option>
          </el-select>
          <!--非引用-->
          <el-input
            class="item last-item"
            size="mini"
            style="width: 190px"
            v-if="n.value.type == 'generated'"
            v-model="n.value.content"
          ></el-input>
          <!--引用-->
          <!-- <el-select class="item last-item" size="mini" v-if="n.value.type==='ref'"
                               v-model="n.value.content.ref_var_name" @change="(val)=>refValueChange(val,l)">
                        <div style="padding: 10px;" v-for="(p,l) in preAllNode">
                            <p>{{p.name}}</p>
                            <el-option v-for="(m,j) in p.data.data.outputs"
                                       :label="m.name+' ('+m.type+')'"
                                       :value="m.name">
                            </el-option>
                        </div>

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
                  :key="`${l}opt`"
                  @click="refValueClick(n, i, m, p, l)"
                >
                  <span class="name">{{ p.name }}</span>
                  <span class="type">{{ p.type }}</span>
                </div>
              </div>
            </div>
            <div
              slot="reference"
              v-if="n.value.type === 'ref'"
              class="item last-item popover-select"
            >
              {{ n.newRefContent }}
            </div>
          </el-popover>
          <i
            class="el-icon-remove-outline del-icon"
            @click="preDelInputsParams(i)"
          ></i>
        </div>
      </div>
      <p v-if="nodeData.validate && JSON.parse(nodeData.validate).inputValidate === false" class="workflow-errormsg">{{JSON.parse(nodeData.validate).message}}</p>
    </div>

    <!--代码-->
    <div class="code">
      <p class="code-title">代码</p>
      <div class="code-plugin">
        <CodeEditor
          :value="codeValue"
          :language="'python'"
          :readOnly="true"
        ></CodeEditor>
      </div>
      <div class="edit" @click="preEdit">
        <i class="el-icon-s-operation"></i>编辑代码
      </div>
    </div>

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
        </div>
        <div
          class="form-item"
          v-for="(n, i) in nodeData.data.outputs"
          :key="`${i}opts`"
        >
          <el-input class="item" size="mini" v-model="n.name"></el-input>
          <el-select class="item" size="mini" v-model="n.type">
            <el-option value="string" label="String"></el-option>
            <el-option value="array" label="Array"></el-option>
            <!--<el-option value="Integer" label="Integer"></el-option>
                        <el-option value="Boolean" label="Boolean"></el-option>
                        <el-option value="Number" label="Number"></el-option>-->
            <!--<el-option value="object" label="引用"></el-option>-->
          </el-select>
          <i
            class="el-icon-remove-outline del-icon"
            @click="preDelOutputsParams(i)"
          ></i>
        </div>
      </div>
      <p v-if="nodeData.validate && JSON.parse(nodeData.validate).outputValidate === false" class="workflow-errormsg">{{JSON.parse(nodeData.validate).message}}</p>
    </div>

    <div v-if="editVisible" class="edit-modal">
      <CodeEditorMask
        ref="code_editor"
        :node="node"
        @handleTake="handleTake"
        @refreshCodeValue="refreshCodeValue"
        @setOutputsData="setOutputsData"
      />
    </div>
  </div>
</template>

<script>
import { mapState } from "vuex";
import CodeEditorMask from "@/views/codeEditor";
import CodeEditor from "@/views/codeEditor/components/codeEditor.vue";

import isBase64 from "is-base64";
import { Base64 } from "js-base64";

import nodeMethod from "@/views/workflow/mixins/nodeMethod";
export default {
  components: { CodeEditorMask, CodeEditor },
  props: ["graph", "node"],
  data() {
    return {
      editVisible: false,
      settings: {},
      nodeData: {},
      preNodeOutputs: [],
      codeValue: "",
      preAllNode: [],
    };
  },
  mixins: [nodeMethod],
  computed: {
    ...mapState({
      nodeIdMap: (state) => state.workflow.nodeIdMap,
    }),
  },
  created() {
    //this.nodeData = this.node.data;
    //this.parseNodeData(this.nodeData);

    //this.settings = this.node.data.data.settings;
    this.codeValue =
      this.settings.code && isBase64(this.settings.code)
        ? Base64.decode(this.settings.code)
        : this.settings.code;

    //this.getPreNode(this.nodeData.id);
  },
  methods: {
    setOutputsData(data) {
      this.nodeData.data.outputs = data;
    },
    refreshCodeValue(newCodeValue) {
      this.node.data.data.settings.code = Base64.encode(newCodeValue);
    },
    parseNodeData(nodeData) {
      nodeData.data.inputs.forEach((m) => {
        if (m.value.type === "ref") {
          let newRefContent = m.value.content.ref_node_id
            ? `${this.nodeIdMap[m.value.content.ref_node_id]}/${
                m.value.content.ref_var_name
              }`
            : "";

          m.newRefContent = newRefContent;
        }
      });
    },
    //根据当前节点获取该节点的前一个节点
    /*getPreNode(currNodeId) {
          if (currNodeId === "startnode") {
              return;
          }
          let preNodeId = ""; //上一个节点id
          let graphData = this.graph.toJSON().cells;
          //获取匹配的节点
          let preNodeArr = graphData.filter((n) => {
              return (
                  n.shape === "dag-edge" &&
                  (n.target_node_id || n.target.cell) === currNodeId
              );
          });
          console.log('preNodeArr:',preNodeArr)
          if (preNodeArr.length) {
              let _preId = ''
              //preNodeId = preNodeArr[0].source_node_id || preNodeArr[0].source.cell;
              preNodeArr.forEach(m=>{
                  _preId = m.source_node_id || m.source.cell
                  console.log('_preId:',_preId)
                  if (_preId) {
                      //上一个节点
                      let preNode = graphData.filter((n) => {
                          return n.shape === "dag-node" && n.id === _preId;
                      })[0];

                      //判断是否有重复节点
                      let exitIds = this.preAllNode.map(p=>{
                          return p.id
                      })
                      console.log('##exitIds:',exitIds,preNode.id)
                      if(!(exitIds.includes(preNode.id))){
                          this.preAllNode.push(preNode)
                      }
                      this.getPreNode(preNode.id);
                  }
              })
          }
          /!*if (preNodeId) {
            //上一个节点
            let preNode = graphData.filter((n) => {
              return n.shape === "dag-node" && n.id === preNodeId;
            })[0];
            this.preAllNode.push(preNode);
            this.getPreNode(preNode.id);
          }*!/
      },
    selectTypeChange(val, i) {
      switch (val) {
        case "ref":
          //this.preAllNode = []
          //this.getPreNode(this.nodeData.id);
          break;
        case "generated":
          let newItem = {
              desc: "",
              extra: {
                  location: "query",
              },
              list_schema: null,
              name: this.nodeData.data.inputs[i].name,
              object_schema: null,
              required: false,
              type: "string",
              value: {
                  content: "",
                  type: "generated",
              },
              newRefContent: "",
          };
          this.$nextTick(()=>{
              this.$set(this.nodeData.data.inputs, i, newItem);
          })
          break;
      }
    },
    refValueClick(inputNode, i, refPnode, p, l) {
      let ref_node_id = refPnode.id;
      let ref_var_name = p.name;
      let pName = refPnode.name;
      let newData = {
        ...inputNode,
        value: {
          content: {
            ref_node_id,
            ref_var_name,
          },
          type: "ref",
        },
        newRefContent: `${pName}/${p.name}`,
      };
      this.$set(this.nodeData.data.inputs, i, newData);
    },*/
    preEdit() {
      this.editVisible = true;
      this.$nextTick(() => {
        this.$refs["code_editor"].setCode({
          ...this.settings,
          code: isBase64(this.settings.code)
            ? Base64.decode(this.settings.code)
            : this.settings.code,
        });
      });
    },
    handleTake() {
      this.editVisible = false;
    },
    /*输入*/
    preAddInputParams() {
      let itemObj = {
        desc: "",
        list_schema: null,
        name: "",
        object_schema: null,
        required: true,
        type: "string",
        value: {
          content: {
            ref_node_id: "",
            ref_var_name: "",
          },
          type: "ref",
        },
        newRefContent: "",
      };
      this.$set(
        this.nodeData.data.inputs,
        this.nodeData.data.inputs.length,
        itemObj
      );
      this.updatePorts();
    },
    updatePorts() {
      setTimeout(() => {
        const nodes = this.graph.getNodes();
        nodes.map((node) => {
          let ee = document.querySelector(
            `.x6-node[data-cell-id="${node.id}"] foreignObject body .dag-node`
          );
          node.resize(ee.offsetWidth, ee.offsetHeight);
          if (node.data.type === "SwitchNode") {
            let yList = [];
            const ports = node.port.ports;
            if (ports[0].group === "left") {
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
              node.portProp(node.id + i + "-right", "args/y", yList[i]);
            }
          } else {
            const ports = document.querySelectorAll(".x6-port-body");
            for (let i = 0, len = ports.length; i < len; i = i + 1) {
              ports[i].style.visibility = "visible";
            }
          }
        });
      }, 50);
    },
    /*preDelInputsParams(index) {
      this.nodeData.data.inputs.splice(index, 1);
    },*/
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
          content: "",
          type: "generated",
        },
        newRefContent: "",
      };
      this.$set(
        this.nodeData.data.outputs,
        this.nodeData.data.outputs.length,
        itemObj
      );

      this.updatePorts();
    },
    /*preDelOutputsParams(index) {
      this.nodeData.data.outputs.splice(index, 1);
    },*/
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
        flex: 1;
        font-size: 12px;
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
.code_box {
  height: calc(100vh - 151px);
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
    // text-align: center;
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
    height: calc(100vh - 40px);
    right: 450px;
    left: 0;
    top: 20px;
    bottom: 20px;
    background-color: #070c1480;
    z-index: 100;
  }
}
</style>

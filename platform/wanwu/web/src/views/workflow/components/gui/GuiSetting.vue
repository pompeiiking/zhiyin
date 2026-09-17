<template>
  <div class="api_box">
    <!-- <div class="info">
      <p class="info-title">基本信息</p>
      <div class="info-item">
        <label>接口地址</label>
        <el-tooltip
          v-if="
            nodeData.data.settings.url && nodeData.data.settings.url.length > 49
          "
          class="item"
          effect="dark"
          :content="nodeData.data.settings.url"
          placement="top"
        >
          <span>{{ nodeData.data.settings.url || "-" }}</span>
        </el-tooltip>
        <span v-else>{{ nodeData.data.settings.url || "-" }}</span>
      </div>
      <div class="info-item">
        <label>请求方式</label
        ><span class="methods">{{
          nodeData.data.settings.http_method || "-"
        }}</span>
      </div>
      <div class="info-item">
        <label>内容类型</label
        ><span>{{ nodeData.data.settings.content_type || "-" }}</span>
      </div>
      <div class="info-item"><label>鉴权方式</label><span>API Key</span></div>
    </div>
    <div class="edit-api" @click="preEdit">
      <i class="el-icon-s-operation"></i>编辑API
    </div> -->

    <!--输入-->
    <div class="node-params">
      <div class="params-type">
        <i class="el-icon-caret-bottom"></i>
        <span class="params-type-span">输入</span>
        <!-- <i class="el-icon-plus add-icon" @click="preAddInputParams"></i> -->
      </div>
      <!--form-->
      <div class="params-form">
        <div class="form-item">
          <div class="item">参数名</div>
          <div class="item">类型</div>
          <div class="item last-item">值</div>
        </div>
        <div v-for="(n, i) in nodeData.data.inputs" :key="`${i}ipt`">
          <div class="form-item" v-if="n.name">
            <!-- name -->
            <!-- <el-input class="item" size="mini" v-model="n.name"></el-input> -->
            <div class="params_name">
              <el-tooltip :content="n.name" placement="top">
                <span>{{ n.name }}</span>
              </el-tooltip>
                          
            </div>

            <!-- 类型 -->
            <el-select
              class="item"
              size="mini"
              v-model="n.value.type"
               @change="(val) => selectTypeChange(val, i,n)"
            >
              <el-option value="generated" :label="n.name == 'history'? 'Array<Object>':n.type"></el-option>
              <el-option value="ref" label="引用"></el-option>
              <!--<el-option value="Integer" label="Integer"></el-option>
                            <el-option value="Boolean" label="Boolean"></el-option>
                            <el-option value="Number" label="Number"></el-option>-->
            </el-select>
            <!-- <div class="params_type">
              <span>{{ n.type }}</span>
            </div> -->

            <!--非引用-->
            <el-input
              class="item last-item"
              size="mini"
              :type="n.type =='Integer'? 'number':'text'"
              v-if="n.value.type === 'generated' && n.name !=='history'"
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
                v-show="n.value.type === 'ref'"
                class="item last-item popover-select"
              >
                {{ n.newRefContent }}
              </div>
            </el-popover>
          </div>

          <codeEditor
                v-if="n.value.type === 'generated' && n.name =='history'"
                style="height: 200px;overflow: auto"
                :value="history"
                :language="'json'"
                @handleChange="handleChange"
                :theme="'vs'"
        ></codeEditor>
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

    <!--输出-->
    <div class="node-params">
      <div class="params-type">
        <i class="el-icon-caret-bottom"></i>
        <span class="params-type-span">输出</span>
      </div>
      <div class="params-content">
        <div
          class="params-content-item"
          v-for="(n, i) in nodeData.data.outputs"
          :key="`${i}opts`"
        >
          <span>{{ n.name }}</span>
          <span>{{ n.type }}</span>
          <span>{{ n.desc }}</span>
        </div>
      </div>
      <p
        v-if="
          nodeData.validate &&
          JSON.parse(nodeData.validate).outputValidate === false
        "
        class="workflow-errormsg"
      >
        {{ JSON.parse(nodeData.validate).message }}
      </p>
    </div>

    <!--编辑api-->
    <GuiEditor
      ref="editor"
      :node="node"
      v-if="editVisible"
      @close="closeEdit"
      @inputsChange="inputsChange"
    />
  </div>
</template>

<script>
import { runNode } from "@/api/workflow";
import GuiEditor from "./GuiEditor";
import { mapState } from "vuex";

import nodeMethod from "@/views/workflow/mixins/nodeMethod";
import codeEditor from "@/views/ArrayEditor/index.vue";

export default {
  props: ["graph", "node"],
  components: { GuiEditor,codeEditor },
  data() {
    return {
      editVisible: false,
      nodeData: {},
      preNode: {},
      preNodeOutputs: [],
      settings: {
        url: "",
      },
      preAllNode: [],
    };
  },
  mixins: [nodeMethod],
  computed: {
    ...mapState({
      nodeIdMap: (state) => state.workflow.nodeIdMap,
    }),
    history(){
      let content = this.nodeData.data.inputs[this.nodeData.data.inputs.length -1].value.content

      return content ? JSON.stringify(content): ""
    }
  },
  created() {
    // this.nodeData = this.node.data;
    // this.parseNodeData(this.nodeData);
    //
    // this.preNode = this.node.data.preNode;
    // this.getPreNode(this.nodeData.id);
  },
  watch: {
    "node.data.id": {
      handler: function (newVal, oldVal) {
        this.$forceUpdate();
      },
      deep: true,
    },
  },
  methods: {
    handleChange(val){
      this.nodeData.data.inputs[this.nodeData.data.inputs.length-1].value.content = JSON.parse(val)
      this.nodeData.inputs['history'] = JSON.parse(val)
    },
    /*parseNodeData(nodeData) {
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
    getPreNode(currNodeId) {
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
    selectTypeChange(val, i,n) {
      switch (val) {
        case "ref":
          //this.preAllNode = []
          //this.getPreNode(this.nodeData.id);
          break;
        case "generated":
          let newItem = {
              desc: "",
              extra: n.extra,
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
    /*getPreOutputs() {
      //获取前一个节点的值,preNode不会同步更新，遍历graphData匹配最新数据
      if (this.preNode) {
        let graphData = this.graph.toJSON().cells;
        let newPreNode = graphData.filter((n) => {
          return n.shape === "dag-node" && n.id === this.preNode.id;
        })[0];
        console.log("newPreNode: ", newPreNode);
        this.preNodeOutputs = newPreNode.data.outputs.map((m, j) => {
          return {
            ...m,
            pid: m.value.type === "ref" ? m.value.content.ref_node_id : "",
            newLabel: `${newPreNode.name}/${m.name}(${m.type})`,
            newContent: m.name, //JSON.stringify({ "ref_node_id": this.preNode.id, "ref_var_name": m.name }) //问题在这里 怎么获得上一个节点
          };
        });
      }
    },*/
    preEdit() {
      this.editVisible = true;
    },
    closeEdit() {
      this.editVisible = false;
    },
    inputsChange(newInputs) {
      this.nodeData.inputs = newInputs.filter((n) => {
        return n.name;
      });
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
    }
    .params-type-span {
      margin-left: 10px;
    }
  }
  .params_name {
    display: flex;
    justify-content: center;
    align-items: center;
    height: auto;
    width: 120px;
    border: 1px solid #ddd;
    background: #f5f7fa;
    color: #c0c4cc;
    line-height: 1;
    border-radius: 4px;
    padding: 3px 10px;

    span {
      white-space: nowrap; /* 允许文本换行 */
      // overflow-wrap: break-word; /* 允许长单词换行 */
      // word-break: break-all; /* 允许任意字符换行 */
      text-align: center;
      text-overflow: ellipsis;
      overflow:hidden;
    }
  }
  .params_type {
    display: flex;
    justify-content: center;
    align-items: center;
    height: auto;
    width: 110px;
    border: 1px solid #ddd;
    background: #f5f7fa;
    color: #c0c4cc;
    line-height: 1;
    border-radius: 4px;

    span {
      white-space: normal; /* 允许文本换行 */
      overflow-wrap: break-word; /* 允许长单词换行 */
      word-break: break-all; /* 允许任意字符换行 */
      text-align: center;
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
        flex: 2;
        font-size: 12px;
      }
      .last-item {
        flex: 2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .del-icon {
        line-height: 30px;
      }
    }
  }
}
.api_box {
  height: calc(100vh - 135px);
  overflow-y: auto;
  .info-title {
    font-size: 14px;
    margin: 10px 0;
  }
  .info-item {
    display: flex;
    margin: 15px 0;

    .methods {
      color: rgb(48, 191, 19);
    }
    label {
      display: block;
      flex: 1;
      color: #5c5f66;
      font-size: 12px;
    }
    span {
      display: block;
      font-size: 12px;
      flex: 3;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
  .edit-api {
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
}
.edit-modal {
  position: fixed;
  z-index: 10;
  overflow: auto;
  display: flex;
  flex-direction: column;
  width: 60%;
  height: calc(100vh - 40px);
  right: 400px;
  top: 20px;
  bottom: 20px;
  background-color: #070c1480;
  .edit-header {
    position: relative;
    padding: 14px 20px;
    border-bottom: 1px solid #eee;
    .arrow-icon {
      position: absolute;
      right: 20px;
    }
  }
  .req-box {
    flex: 1;
    padding: 14px 20px;
    .req-url {
      display: flex;
      .el-select/deep/.el-input__inner {
        background-color: #f7f7f9;
      }
      .el-input {
        margin-left: -1px;
      }
      .send-bt {
        margin: 0 5px;
      }
    }
    .req-params {
      .req-params-tabs {
        margin-top: 20px;
      }
    }
  }
  .res-box {
    height: 300px;
    border-top: 1px solid #eee;
    .res-header {
      padding: 10px 20px;
      border-bottom: 1px solid #eee;
      .right-status {
        float: right;
        display: flex;
        .status-item {
          margin-left: 10px;
          vertical-align: middle;
          span:nth-child(1) {
            color: #84868c;
          }
          span:nth-child(2) {
            color: #333;
          }
          span {
            font-size: 12px;
          }
        }
      }
    }
    .res-content {
      display: flex;
      height: 100%;
      .left,
      .right {
        flex: 1;
      }
      .left {
        /deep/.el-tabs__nav-wrap {
          padding: 0 20px;
        }
      }
    }
    .editable--input {
      padding: 20px;
      border-right: 1px solid #eee;
      min-height: 100%;
    }
  }
}
.popover-select{
  width: 160px;
}
.item-array{
  width:100%;
  margin-bottom:5px;
}
</style>

<template>
  <div class="condition-form">
    <el-form label-width="80px">
      <!--left-->
      <el-form-item label="引用变量" required>
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
                @click="refValueClick(switchItem, switchIndex, m, p, l, 'left')"
              >
                <span class="name">{{ p.name }}</span>
                <span class="type">{{ p.type }}</span>
              </div>
            </div>
          </div>
          <div
            slot="reference"
            v-show="condition.left.value.type === 'ref'"
            class="item last-item popover-select"
            style="width: 212px"
          >
            {{ condition.left.newRefContent }}
          </div>
        </el-popover>
      </el-form-item>
      <!--center-->
      <el-form-item label="条件关系" required>
        <el-select
          v-model="condition.operator"
          style="width: 212px"
          size="mini"
          placeholder="请选择"
          @change="(val) => operatorChange(val, condition)"
        >
          <el-option
            v-for="operator in switchOperatorList"
            :key="operator.value"
            :label="operator.label"
            :value="operator.value"
          >
          </el-option>
        </el-select>
      </el-form-item>
      <el-form-item label="比较变量" required>
        <el-row>
          <el-col :span="10">
            <el-select
              class="item"
              size="mini"
              popper-class="workflow-select"
              v-model="condition.right.value.type"
              @change="(val) => selectTypeChange(val, switchItem, switchIndex)"
              :disabled="disabledArr.includes(condition.operator)"
            >
              <el-option
                v-if="!integerArr.includes(condition.operator)"
                value="generated"
                label="String"
              ></el-option>
              <el-option
                v-else="integerArr.includes(condition.operator)"
                value="generated"
                label="Integer"
              ></el-option>
              <el-option value="ref" label="引用"></el-option>
            </el-select>
          </el-col>
          <!--right-->
          <el-col :span="14">
            <!--非引用-->
            <el-input
              class="item last-item"
              size="mini"
              style="width: 124px"
              v-if="
                condition.right.value.type == 'generated' &&
                !integerArr.includes(condition.operator)
              "
              :disabled="disabledArr.includes(condition.operator)"
              v-model="condition.right.value.content"
            ></el-input>
            <el-input-number
              class="item last-item"
              size="mini"
              style="width: 124px"
              v-if="
                condition.right.value.type == 'generated' &&
                integerArr.includes(condition.operator)
              "
              :disabled="disabledArr.includes(condition.operator)"
              v-model="condition.right.value.content"
            ></el-input-number>
            <!--引用-->
            <el-popover
              placement="bottom"
              width="260"
              trigger="click"
              :disabled="disabledArr.includes(condition.operator)"
            >
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
                  @click="
                    refValueClick(switchItem, switchIndex, m, p, l, 'right')
                  "
                >
                  <span class="name">{{ p.name }}</span>
                  <span class="type">{{ p.type }}</span>
                </div>
              </div>
              <div
                slot="reference"
                v-show="condition.right.value.type === 'ref'"
                class="item last-item popover-select"
                style="width: 124px"
              >
                {{ condition.right.newRefContent }}
              </div>
            </el-popover>
          </el-col>
        </el-row>
      </el-form-item>
    </el-form>
  </div>
</template>

<script>
import {
  switchLogicConfig,
  switchOperatorConfig,
  switchOperatorList,
} from "../../../mock/nodeConfig";

export default {
  props: [
    "graph",
    "node",
    "switchItem",
    "switchIndex",
    "condition",
    "conditionIndex",
  ],
  data() {
    return {
      settings: {},
      switchLogicConfig: switchLogicConfig,
      switchOperatorConfig: switchOperatorConfig,
      switchOperatorList: switchOperatorList,
      preNode: {},
      preNodeOutputs: [],
      preAllNode: [],
      integerArr: ["len_ge", "len_gt", "len_le", "len_lt"],
      disabledArr: ["empty", "not_empty"],
    };
  },
  created() {
    this.nodeData = this.node.data;
  },
  mounted() {
    this.getPreNode(this.node.id);
    console.log("@@@@preAllNode:", this.preAllNode);
  },
  methods: {
    operatorChange(val, condition) {
      if (this.integerArr.includes(val)) {
        condition.right.type = "integer";
      } else {
        condition.right.type = "string";
      }
      console.log("condition:", this.condition);
    },
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
      if (preNodeArr.length) {
        let _preId = "";
        //preNodeId = preNodeArr[0].source_node_id || preNodeArr[0].source.cell;
        preNodeArr.forEach((m) => {
          _preId = m.source_node_id || m.source.cell;
          console.log("_preId:", _preId);
          if (_preId) {
            //上一个节点
            let preNode = graphData.filter((n) => {
              return n.shape === "dag-node" && n.id === _preId;
            })[0];

            //判断是否有重复节点
            let exitIds = this.preAllNode.map((p) => {
              return p.id;
            });
            console.log("##exitIds:", exitIds, preNode.id);
            if (!exitIds.includes(preNode.id)) {
              this.preAllNode.push(preNode);
            }
            this.getPreNode(preNode.id);
          }
        });
      }
      /*if (preNodeId) {
                  //上一个节点
                  let preNode = graphData.filter((n) => {
                    return n.shape === "dag-node" && n.id === preNodeId;
                  })[0];
                  this.preAllNode.push(preNode);
                  this.getPreNode(preNode.id);
                }*/
    },
    selectTypeChange(val, switchItem, switchIndex) {
      console.log(
        "vvvv:",
        switchItem,
        "分支坐标:",
        switchIndex,
        "条件坐标:",
        this.conditionIndex
      );
      switch (val) {
        case "ref":
          break;
        case "generated":
          let oriCondition = switchItem.conditions[this.conditionIndex];
          let oriConditionRight = {
            ...oriCondition.right,
            value: {
              content: "",
              type: "generated",
            },
            newRefContent: ``,
          };
          let newData = {
            ...oriCondition,
            right: oriConditionRight,
          };
          this.$set(
            this.nodeData.data.inputs[switchIndex].conditions,
            this.conditionIndex,
            newData
          );
          break;
      }
    },
    /*参数说明， inputNode:input.conditions   i:switchIndex  */
    refValueClick(inputNode, i, refPnode, p, l, direction) {
      /*
                * {
                    "operator": "eq",
                    "left": {
                        "name": "qqqq",
                        "type": "string",
                        "desc": "",
                        "required": false,
                        "value": {
                            "type": "ref",
                            "content": {
                                "ref_node_id": "3412b5e2-6cb7-4c7e-b0db-93a353b4ec91",
                                "ref_var_name": "dsa"
                            }
                        },
                        "object_schema": null,
                        "list_schema": null
                    },
                    "right": {
                        "name": "wwww",
                        "type": "string",
                        "desc": "",
                        "object_schema": null,
                        "list_schema": null,
                        "required": false,
                        "value": {
                            "type": "literal",
                            "content": 12312312312
                        }
                    }
                },
                * */
      console.log(inputNode, i, refPnode, p, l);
      let ref_node_id = refPnode.id;
      let ref_var_name = p.name;
      let pName = refPnode.name;
      let oriCondition = inputNode.conditions[this.conditionIndex];
      let newData = {};

      switch (direction) {
        case "left":
          let oriConditionLeft = {
            ...oriCondition.left,
            value: {
              content: {
                ref_node_id,
                ref_var_name,
              },
              type: "ref",
            },
            newRefContent: `${pName}/${p.name}`,
          };
          newData = {
            ...oriCondition,
            left: oriConditionLeft,
          };
          break;
        case "right":
          let oriConditionRight = {
            ...oriCondition.right,
            value: {
              content: {
                ref_node_id,
                ref_var_name,
              },
              type: "ref",
            },
            newRefContent: `${pName}/${p.name}`,
          };
          newData = {
            ...oriCondition,
            right: oriConditionRight,
          };
          break;
      }
      console.log("!!!newData:", newData);
      this.$set(
        this.nodeData.data.inputs[i].conditions,
        this.conditionIndex,
        newData
      );
      console.log("!!!refValueClick:", i, this.nodeData.data.inputs[i]);
      //this.$emit('refValueClick',i,this.nodeData.data.inputs[i])
    },
    preDelInputsParams(index) {
      this.nodeData.data.inputs.splice(index, 1);
    },
    preDelOutputsParams(index) {
      this.nodeData.data.outputs.splice(index, 1);
    },
  },
};
</script>

<style lang="scss" scoped>
.condition-form {
}
</style>

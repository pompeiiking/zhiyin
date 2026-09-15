<template>
  <div class="model_box">
    <!--模型-->
    <div class="model-box">
      <p class="params-type-span">条件分支</p>
    </div>

    <!--输入-->
    <!--条件-->
    <div
            v-for="(n, i) in nodeData.data.inputs"
            :key="`${i}ips`"
            class="node-params switch-item"
    >
      <div class="params-type">
        <i class="el-icon-caret-bottom"></i>
        <span class="params-type-span">{{
          i === 0
            ? "如果"
            : i === nodeData.data.inputs.length - 1
            ? "否则"
            : "否则如果"
        }}</span>
        <i
                class="el-icon-remove-outline del-icon"
                v-if="i !== 0 && i !== nodeData.data.inputs.length - 1"
                @click="preDelInputParams(i)"
        ></i>
      </div>
      <div class="conditions-box" v-if="i !== nodeData.data.inputs.length - 1">
        <div v-for="(m, j) in n.conditions" :key="`${j}cds`" class="conditions">
          <el-popover placement="bottom" width="320" trigger="click">
            <!--弹出框-->
            <ConditionForm
                    @refValueClick="refValueClick"
                    :graph="graph"
                    :node="node"
                    :switchItem="n"
                    :switchIndex="i"
                    :condition="m"
                    :conditionIndex="j"
            />
            <div slot="reference">
              <el-row class="condition-item">
                <el-col :span="8" class="left">{{
                  m.left.newRefContent
                  }}</el-col>
                <el-col :span="8" class="center">{{
                  switchOperatorConfig[m.operator] || "请选择"
                  }}</el-col>
                <el-col :span="8" class="right" v-show="!(disabledArr.includes(m.operator))">
                  <span v-if="m.right.value.type === 'ref'">{{
                    m.right.newRefContent
                  }}</span>
                  <span v-if="m.right.value.type === 'generated'">{{
                    m.right.value.content
                  }}</span>
                </el-col>
                <el-col :span="2"></el-col>
              </el-row>
            </div>
          </el-popover>
          <i
                  class="el-icon-remove-outline condition-item-del-icon"
                  @click.stop="preDelCondition(n, i, m, j)"
          ></i>
        </div>
        <el-row class="switch-item-bt-box">
          <el-col :span="8">
            <el-button
                    class="switch-item-bt"
                    icon="el-icon-plus"
                    size="mini"
                    @click="preAddCondition(n, i)"
            >添加条件</el-button
            >
          </el-col>
          <el-col :span="8" v-show="n.conditions && n.conditions.length > 1">
            <el-button
                    class="switch-item-bt"
                    size="mini"
                    @click="preChangeLogic(n, i)"
            >且<i class="el-icon-sort sort-icon"></i>或</el-button
            >
          </el-col>
        </el-row>
        <!--连接线-->
        <div class="line" v-show="n.conditions && n.conditions.length > 1">
          <span :class="['line-span', n.logic]">{{
            switchLogicConfig[n.logic]
          }}</span>
        </div>
      </div>
    </div>

    <!--添加分支-->
    <el-button
            class="add-switch-bt"
            size="mini"
            icon="el-icon-plus"
            @click="preAddSwitch"
    >添加分支</el-button
    >
  </div>
</template>

<script>
    import { mapState } from "vuex";
    import { switchLogicConfig, switchOperatorConfig } from "../../mock/nodeConfig";
    import ConditionForm from "./components/ConditionForm";

    function refreshNode(node) {
        // 获取当前节点的位置
        const pos = node.getPosition();

        // 更新节点位置，强制重绘节点
        node.transition({
            x: pos.x + 1, // 改变x位置
            y: pos.y, // 保持y位置不变
            duration: 0, // 设置为0可以立即完成过渡，即强制刷新
        });
    }

    export default {
        components: { ConditionForm },
        props: ["graph", "node"],
        data() {
            return {
                editVisible: true,
                settings: {},
                switchLogicConfig: switchLogicConfig,
                switchOperatorConfig: switchOperatorConfig,
                nodeData: {},
                preNode: {},
                preNodeOutputs: [],
                preAllNode: [],
                disabledArr:['empty','not_empty'],
            };
        },
        computed: {
            ...mapState({
                nodeIdMap: (state) => state.workflow.nodeIdMap,
            }),
        },
        created() {
            console.log("@@@@this.node:", this.node);
            this.nodeData = this.node.data;
            this.parseNodeData(this.nodeData);
        },
        methods: {
            refValueClick(switchIndex, newData) {
                console.log(switchIndex, newData);
                this.$set(this.node.data.data.inputs, switchIndex, newData);
                this.$forceUpdate();
            },
            preAddSwitch() {
                let lastItem = this.nodeData.data.inputs[this.nodeData.data.inputs.length-1]
                let newItem = {
                    logic: "and",
                    target_node_id: "",
                    conditions: [],
                }
                this.$set(this.nodeData.data.inputs,this.nodeData.data.inputs.length-1,newItem)
                this.nodeData.data.inputs.push(lastItem)

                this.$emit("preAddSwitch", this.nodeData.data.inputs.length);
                setTimeout(() => {
                    let port = this.node.port.ports;
                    if (port[0].group === "left") {
                        port.shift();
                    }
                    let lastPort = port[port.length - 1];

                    const edges = [];
                    this.graph.getEdges().forEach((edge) => {
                        const sourcePortId = edge.getSourcePortId();
                        const targetPortId = edge.getTargetPortId();
                        if (sourcePortId === lastPort.id || targetPortId === lastPort.id) {
                            edges.push(edge);
                        }
                    });
                    console.log(port.length);

                    this.node.addPort({
                        group: "absolute",
                        id: this.node.id + port.length + "-right",
                        args: {
                            x: "100%",
                            y: lastPort.args.y + 50,
                        },
                    });
                    if (edges.length > 0) {
                        let newPort = this.node.port.ports;
                        console.log(newPort.length);
                        edges[0].setSource({
                            cell: this.node.id,
                            port: newPort[newPort.length - 1].id,
                        });
                    }
                    let ee = document.querySelector(
                        `.x6-node[data-cell-id="${this.node.id}"] foreignObject body .dag-node`
                    );
                    this.node.resize(ee.offsetWidth, ee.offsetHeight);
                    const portsdom = document.querySelectorAll(".x6-port-body");
                    for (let i = 0, len = portsdom.length; i < len; i = i + 1) {
                        portsdom[i].style.visibility = "visible";
                    }
                }, 10);
            },
            parseNodeData(nodeData) {
                nodeData.data.inputs.forEach((m) => {
                    m.conditions && m.conditions.forEach((p) => {
                        if (p.left.value.type === "ref") {
                            console.log("!!!! ref", p.left.value.content.ref_node_id);
                            let newRefContent = p.left.value.content.ref_node_id
                                ? `${this.nodeIdMap[p.left.value.content.ref_node_id]}/${
                                    p.left.value.content.ref_var_name
                                    }`
                                : "";
                            p.left.newRefContent = newRefContent;
                        }
                        if (p.right.value.type === "ref") {
                            let newRefContent = p.right.value.content.ref_node_id
                                ? `${this.nodeIdMap[p.right.value.content.ref_node_id]}/${
                                    p.right.value.content.ref_var_name
                                    }`
                                : "";
                            p.right.newRefContent = newRefContent;
                        }
                    });
                });
            },
            preAddCondition(n, i) {
                n.conditions.push({
                    operator: "",
                    left: {
                        name: "",
                        type: "string",
                        desc: "",
                        required: false,
                        value: {
                            type: "ref",
                            content: {
                                ref_node_id: "",
                                ref_var_name: "",
                            },
                        },
                        object_schema: null,
                        list_schema: null,
                    },
                    right: {
                        name: "",
                        type: "integer",
                        desc: "",
                        object_schema: null,
                        list_schema: null,
                        required: false,
                        value: {
                            type: "ref",
                            content: {
                                ref_node_id: "",
                                ref_var_name: "",
                            },
                        },
                    },
                });

                setTimeout(() => {
                    let ee = document.querySelector(
                        `.x6-node[data-cell-id="${this.node.id}"] foreignObject body .dag-node`
                    );
                    this.node.resize(ee.offsetWidth, ee.offsetHeight);
                    const portsdom = document.querySelectorAll(".x6-port-body");
                    for (let i = 0, len = portsdom.length; i < len; i = i + 1) {
                        portsdom[i].style.visibility = "visible";
                    }
                    let yList = [];
                    const ports = this.node.port.ports;
                    if (ports[0].group === "left") {
                        ports.shift();
                    }
                    const dom = document
                        .getElementById(this.node.id)
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
                    }
                    for (let i = 0; i < ports.length; i++) {
                        this.node.portProp(ports[i].id, "args/y", yList[i]);
                    }
                }, 50);
            },
            preDelInputParams(index) {
                this.nodeData.data.inputs.splice(index, 1);

                let port = JSON.parse(JSON.stringify(this.node.port.ports));

                if (port[0].group === "left") {
                    port.shift();
                }
                let lastPort = port[port.length - 1];
                // port.shift();
                // port.pop();
                let edgesMap = {};
                let edgesArr = [];
                const edges = this.graph.getEdges().filter((edge) => {
                    const target = edge.getTarget();
                    const source = edge.getSource();
                    const sourcePortId = edge.getSourcePortId();
                    const targetPortId = edge.getTargetPortId();
                    edgesMap[source.port] = edge;
                    if (sourcePortId === lastPort.id || targetPortId === lastPort.id) {
                        edgesArr.push(edge);
                    }
                    return target.port === port[index].id || source.port === port[index].id;
                });
                setTimeout(() => {
                    setTimeout(() => {
                        setTimeout(() => {
                            port.forEach((iport, poindex) => {
                                if (
                                    poindex > index &&
                                    edgesMap[iport.id] &&
                                    poindex != port.length - 1
                                ) {
                                    edgesMap[iport.id].setSource({
                                        cell: this.node.id,
                                        port: port[poindex - 1].id,
                                    });
                                }
                            });
                            edges[0].delSource = 'condition'
                            this.graph.removeEdge(edges[0]);
                        }, 10);
                        if (edgesMap[port[port.length - 1].id]) {
                            edgesMap[port[port.length - 1].id].setSource({
                                cell: this.node.id,
                                port: port[port.length - 2].id,
                            });
                        }
                        this.node.removePort(port[port.length - 1].id);
                        // this.node.scale(1,1)
                        // refreshNode(cnode)
                    }, 10);
                }, 50);
            },
            preDelCondition(n, i, m, j) {
                this.nodeData.data.inputs[i].conditions.splice(j, 1);
                setTimeout(() => {
                    let ee = document.querySelector(
                        `.x6-node[data-cell-id="${this.node.id}"] foreignObject body .dag-node`
                    );
                    this.node.resize(ee.offsetWidth, ee.offsetHeight);
                    const portsdom = document.querySelectorAll(".x6-port-body");
                    for (let i = 0, len = portsdom.length; i < len; i = i + 1) {
                        portsdom[i].style.visibility = "visible";
                    }
                    let yList = [];
                    const ports = this.node.port.ports;
                    if (ports[0].group === "left") {
                        ports.shift();
                    }
                    const dom = document
                        .getElementById(this.node.id)
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
                    }
                    for (let i = 0; i < ports.length; i++) {
                        this.node.portProp(ports[i].id, "args/y", yList[i]);
                    }
                }, 50);
            },
            preChangeLogic(n, i) {
                n.logic = n.logic === "or" ? "and" : "or";
            },
            selectTypeChange(val, i) {
                switch (val) {
                    case "ref":
                        this.preAllNode = [];
                        this.getPreNode(this.nodeData.id);
                        break;
                    case "generated":
                        let newItem = {
                            desc: "",
                            extra: {
                                location: "body",
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
                        this.$nextTick(() => {
                            this.$set(this.nodeData.data.inputs, i, newItem);
                        });

                        break;
                }
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
      .del-icon {
        position: absolute;
        right: 12px;
        top: 2px;
        font-size: 16px;
      }
      .params-type-span {
        margin-left: 10px;
      }
    }
  }
  .switch-item {
    position: relative;
    .conditions-box {
      padding-left: 22px;
      position: relative;
      .conditions {
        margin-top: 10px;
        position: relative;
        .condition-item-del-icon {
          position: absolute;
          right: 10px;
          top: 12px;
        }
        .condition-item {
          position: relative;
          background-color: #f2f2f4;
          border: 1px solid #e8e9eb;
          padding: 5px;
          border-radius: 6px;
          .left,
          .right {
            background-color: #fff;
            padding: 2px 6px;
            border-radius: 4px;
            display: inline-block;
            height: 24px;
            font-size: 12px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .center {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .center,
          .del-icon {
            text-align: center;
            line-height: 24px;
            font-size: 12px;
          }
        }
      }

      .switch-item-bt-box {
        margin-top: 10px;
        .el-col {
          margin-right: 5px;
        }
        .switch-item-bt {
          color: #2c7eea;
          margin-right: 5px;
        }
        .sort-icon {
          transform: rotate(90deg);
        }
      }
      .line {
        position: absolute;
        top: 14px;
        bottom: 12px;
        left: 7px;
        width: 10px;
        border: 1px solid #d4d6d9;
        border-right: rgba(0, 0, 0, 0);
        border-radius: 4px 0 0 4px;
        .line-span {
          position: absolute;
          top: 50%;
          left: -10px;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 20px;
          height: 20px;
          transform: translateY(-50%);
          border-radius: 4px;
          font-size: 12px;
        }
        .or {
          color: #ff9326;
          background: #fff4e6;
        }
        .and {
          color: #2468f2;
          background: #e6f0ff;
        }
      }
    }
  }

  .add-switch-bt {
    width: 100%;
    margin-top: 10px;
  }
</style>

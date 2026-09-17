<template>
  <div class="workflow">
    <div class="workflow-header">
      <div class="header-left">
        <i class="el-icon-arrow-left" @click="$router.go(-1)" />
        <span
          >{{ this.detail.configName }}
          <i class="el-icon-edit" @click="preCreate"></i
        ></span>
      </div>
      <!--<div class="header-right">
        <el-button
          :type="executeSuccess ? 'primary' : 'plain'"
          :disabled="!executeSuccess"
          @click="publish"
          size="mini"
          >发布</el-button
        >
      </div>-->
    </div>
    <div class="container" id="container"></div>
    <NodeConfig
      ref="config"
      @save="preSave(true)"
      @preAddSwitch="preAddSwitch"
    />
    <div class="footer-setting">
      <el-popover
        v-model="visibleNode"
        placement="top"
        width="200"
        trigger="manual"
        :visible-arrow="false"
        popper-class="workflow_popover"
        class="addNode_box"
      >
        <div class="node-items">
          <div @click="createMCP()" class="node-items-box">
            <span> <img :src="iconObj.MCPClientNode" />&nbsp; MCP </span>
            <div class="nodeSelectDesc">可快捷调用MCP工具</div>
          </div>
          <div @click="preAddNode('IntentionNode')" class="node-items-box">
            <span> <img :src="iconObj.IntentionNode" />&nbsp; 意图识别 </span>
            <div class="nodeSelectDesc">
              识别用户的输入意图，并分配到不同分支执行
            </div>
          </div>
          <div @click="preAddNode('api')" class="node-items-box">
            <span> <img :src="iconObj.ApiNode" />&nbsp; API </span>
            <div class="nodeSelectDesc">{{$t('workFlow.nodeSelectDesc1')}}</div>
          </div>
          <div @click="preAddNode('code')" class="node-items-box">
            <span> <img :src="iconObj.PythonNode" />&nbsp; {{$t('workFlow.code')}} </span>
            <div class="nodeSelectDesc">
              {{$t('workFlow.nodeSelectDesc2')}}
            </div>
          </div>
          <div
            v-if="isStream"
            @click="preAddNode('modelstream')"
            class="node-items-box"
          >
            <span>
              <img :src="iconObj.LLMStreamingNode" />&nbsp; {{$t('workFlow.modelstream')}}
            </span>
            <div class="nodeSelectDesc">
               {{$t('workFlow.nodeSelectDesc6')}}
            </div>
          </div>
          <div @click="preAddNode('model')" class="node-items-box">
            <span> <img :src="iconObj.LLMNode" />&nbsp; {{$t('workFlow.model')}} </span>
            <div class="nodeSelectDesc">
              {{$t('workFlow.nodeSelectDesc3')}}
            </div>
          </div>
          <div @click="preAddNode('switch')" class="node-items-box">
            <span> <img :src="iconObj.SwitchNode" />&nbsp; {{$t('workFlow.splitter')}} </span>
            <div class="nodeSelectDesc">
              {{$t('workFlow.nodeSelectDesc4')}}
            </div>
          </div>
          <div @click="preAddNode('rag')" class="node-items-box">
            <span> <img :src="iconObj.RAGNode" />&nbsp; {{$t('workFlow.knowLedge')}} </span>
            <div class="nodeSelectDesc">
              {{$t('workFlow.nodeSelectDesc5')}}
            </div>
          </div>
          <!--<div @click="preAddNode('gui')" class="node-items-box">
            <span>
              <img :src="iconObj.GUIAgentNode" />&nbsp; GUI 智能体节点
            </span>
            <div class="nodeSelectDesc">
              通过视觉技术解析用户图形界面上的图像信息，并模拟人类操作行为来执行相应任务，与计算机系统进行交互的智能体
            </div>
          </div>-->
          <div @click="preAddNode('filegenerate')" class="node-items-box">
            <span>
              <img :src="iconObj.FileGenerateNode" />&nbsp; 文档生成
            </span>
            <div class="nodeSelectDesc">
              输入文本内容，可以生成docx、pdf、txt格式的文档
            </div>
          </div>
          <div @click="preAddNode('fileparse')" class="node-items-box">
            <span> <img :src="iconObj.FileParseNode" />&nbsp; 文档解析 </span>
            <div class="nodeSelectDesc">
              输入txt、pdf、docx、xlsx、csv、pptx等格式文档的URL，可以解析提取出文档的文本内容
            </div>
          </div>
        </div>
        <el-button
          slot="reference"
          class="add-bt"
          type="primary"
          icon="el-icon-circle-plus"
          size="mini"
          @click="visibleNode = !visibleNode"
          >{{$t('workFlow.addNode')}}</el-button
        >
      </el-popover>
      <!-- <el-button
        class="add-bt"
        type="success"
        size="mini"
        @click="preSave(false)"
        >保存</el-button
      >-->
      <span class="segmentation"></span>
      <el-tooltip
        class="item"
        effect="dark"
        :content="!folt ? $t('workFlow.collapseNode') : $t('workFlow.expandNode')"
        placement="top"
      >
        <el-button
          class="debug-bt folt"
          type="danger"
          size="mini"
          v-if="!folt"
          @click="handleSetFolt(true)"
        >
          <i class="el-icon-download"></i>
          <i
            class="el-icon-download"
            style="transform: rotate(180deg); margin-top: -5px"
          ></i>
        </el-button>
        <el-button
          class="debug-bt folt"
          type="danger"
          size="mini"
          v-else
          @click="handleSetFolt(false)"
        >
          <i class="el-icon-upload2"></i>
          <i
            class="el-icon-upload2"
            style="transform: rotate(180deg); margin-top: -5px"
          ></i>
        </el-button>
      </el-tooltip>
      <el-tooltip class="item" effect="dark" :content="$t('workFlow.mapCenter')" placement="top">
        <el-button
          class="debug-bt"
          type="danger"
          size="mini"
          @click="handleCenterView"
          icon="el-icon-full-screen"
        ></el-button>
      </el-tooltip>

      <el-popover
        placement="top"
        width="200"
        :value="scaleVisible"
        trigger="click"
        popper-class="workflow_popover_scale"
        class="scale_box"
      >
        <div class="node-items">
          <div
            @click="zoom(item.value, item.label)"
            v-for="(item, index) in scaleList"
            :key="index"
            class="node-items-box"
          >
            {{ item.label }}
          </div>
        </div>
        <el-button
          slot="reference"
          class="scale-btn"
          size="mini"
          icon="el-icon-arrow-down"
          @click="showScale"
        >
          {{ graphScale }}
        </el-button>
      </el-popover>
      <span class="segmentation"></span>
      <el-button
        class="debug-bt"
        type="danger"
        size="mini"
        @click="preDebug"
        icon="el-icon-video-play"
        >{{$t('workFlow.debugging')}}</el-button
      >
      <el-tooltip
        class="item"
        effect="dark"
        :content="$t('workFlow.searchResult')"
        placement="top"
      >
        <el-button
          class="debug-bt"
          type="danger"
          size="mini"
          :disabled="JSON.stringify(lastDebugResult) === '{}'"
          @click="preGetLastDebug"
          icon="el-icon-time"
        ></el-button>
      </el-tooltip>
      <el-popover
        placement="top"
        width="180"
        trigger="hover"
        :visible-arrow="false"
        popper-class="workflow_popover_publish"
        class="publish_box"
      >
        <div>
          {{$t('workFlow.publishText')}}
        </div>
        <el-button
          slot="reference"
          class="add-bt"
          type="primary"
          size="mini"
          @click="doPublish"
        >
          {{$t('workFlow.publishButton')}}
        </el-button>
      </el-popover>
    </div>

    <!--调试-->
    <DebugModal
      ref="debug"
      @execute="getWorkFlowStatus"
      @doDebug="doDebug"
      @cancelRun="cancelRun"
    />
    <CreateForm
      ref="create_ref"
      type="edit"
      :editForm="detail"
      @save="preSave(false)"
    />
    <PublishForm ref="publish_ref" @refreshTable="$router.go(-1)" />
    <!--隐藏 token 和 mcp 相关-->
    <!--<AppSelect ref="app-select" @getToken="setToken" />-->
    <McpCreate v-if="" ref="mcpcreate" @createMcp="addMcp" />
    <div id="minimap"></div>
  </div>
</template>

<script>
import { mapState, mapActions } from "vuex";
//前端mock数据
import { mockData } from "./mock/res";
import {
  apiNode_initData,
  pythonNode_initData,
  LLMNode_initData,
  LLMStreamingNode_initData,
  SwitchNode_initData,
  ragNode_initData,
  LLMNodeDescObj,
  filegenerate_initData,
  fileparse_initData,
  guiNode_initData,
  mcp_initData,
  intention_initData,
} from "./mock/nodeConfig";
import { initGraphData } from "./mock/initGraphData";
import { nodeResult } from "./components/run/result";

import { Graph, Path } from "@antv/x6";
import { register } from "@antv/x6-vue-shape";
import { Selection } from "@antv/x6-plugin-selection";

import DagNode from "./components/common/DagNode.vue";
import NodeConfig from "./components/NodeDrawer";
import DebugModal from "./components/run/DebugDrawer";
import McpCreate from "./components/mcp/create.vue";

import CreateForm from "../workflowList/components/createForm.vue";
import PublishForm from "../workflowList/components/publishForm.vue";
import { MiniMap } from "@antv/x6-plugin-minimap";
import { Scroller } from "@antv/x6-plugin-scroller";
import AppSelect from "./components/common/app.vue";

import {
  getWorkFlow,
  saveWorkFlow,
  runWorkFlow,
  getWorkFlowStatus,
  publishWorkFlow,
} from "@/api/workflow";
import {i18n} from "@/lang"
export default {
  components: {
    NodeConfig,
    DebugModal,
    CreateForm,
    AppSelect,
    PublishForm,
    McpCreate,
  },
  data() {
    return {
      isStream: this.$route.query.isStream == "true",
      graphWidth: 0,
      visibleNode: false,
      copyNode: null,
      node: null,
      first: false,
      activeFlot: ["3"],
      folt: false,
      workflowId: "",
      detail: {},
      cells: [],
      graph: null,
      timer: null,
      iconObj: {
        ApiNode: require("./components/img/api.png"),
        PythonNode: require("./components/img/code.png"),
        LLMNode: require("./components/img/model.png"),
        LLMStreamingNode: require("./components/img/model.png"),
        StartNode: require("./components/img/start.png"),
        EndNode: require("./components/img/end.png"),
        EndStreamingNode: require("./components/img/end.png"),
        SwitchNode: require("./components/img/switch.png"),
        RAGNode: require("./components/img/rag.png"),
        GUIAgentNode: require("./components/img/gui.png"),
        FileGenerateNode: require("./components/img/filegenerate.png"),
        FileParseNode: require("./components/img/fileparse.png"),
        MCPClientNode: require("./components/img/MCP.png"),
        IntentionNode: require("./components/img/IntentionNode.png"),
      },
      canvasData: {},
      graphScale: "0",
      scaleVisible: false,
      scaleList: [
        { label: "200%", value: 2 },
        { label: "150%", value: 1.5 },
        { label: "100%", value: 1 },
        { label: "50%", value: 0.5 },
      ],
      executeSuccess: false,
    };
  },
  computed: {
    ...mapState({
      nodeIdMap: (state) => state.workflow.nodeIdMap,
      lastDebugResult: (state) => state.workflow.lastDebugResult,
    }),
  },
  created() {
    sessionStorage.setItem("activeNode", ["1", "2"]);
    this.workflowId = this.$route.query.id;
  },
  mounted() {
    this.registerCustomNode();
    this.registerEdge();
    this.registerConnector();

    this.newGraph();
    this.getWorkFlowData();
  },
  methods: {
    ...mapActions("workflow", [
      "setNodeIdMap",
      "setactiveName",
      "setLastDebugResult",
    ]),
    async doPublish() {
      const params = {
        workflowID: this.workflowId,
      }
      const res = await publishWorkFlow(params);
      if (res.code === 0) {
        this.$message.success(this.$t('list.publicSuccess'))
        this.$router.push({path: '/appSpace/workflow'})
      }
    },
    initNodeData(node_id, node_name, Node_initData, leftPort, rightPort) {
      let graphData = this.graph.toJSON().cells;
      let apiNodes = graphData.filter((n, i) => {
        return n.shape === "dag-node" && n.id.indexOf(node_id) > -1;
      });
      //重置初始化数据
      let _init_id = apiNodes.length
        ? `${node_id}_` + new Date().getTime()
        : `${node_id}_`;

      //判断api名称后缀,有重复的自动+1
      let suffixArr = apiNodes.map((n) => {
        return n.name;
      });
      let _init_name = apiNodes.length
        ? suffixArr.includes(`${node_name}_` + apiNodes.length)
          ? `${node_name}_` + (apiNodes.length + 1)
          : `${node_name}_` + apiNodes.length
        : `${node_name}`;

      this.nodeIdMap[_init_id] = _init_name;
      this.setNodeIdMap(this.nodeIdMap); //保存节点之间互相引用时的映射关系

      Node_initData.data.name = _init_name;
      Node_initData.data.id = _init_id;

      Node_initData.zIndex = 1002;

      leftPort && (Node_initData.ports[0].id = _init_id + "-left");
      rightPort && (Node_initData.ports[1].id = _init_id + "-right");

      let _node_initData = JSON.parse(
        JSON.stringify({
          ...Node_initData,
          id: _init_id,
          name: _init_name,
        })
      );
      _node_initData.x = this.graphWidth / 2 - 190;
      _node_initData.y = -100;
      this.cells.push(this.graph.addNode(_node_initData));
    },
    createMCP() {
      this.$refs.mcpcreate.openDialog();
    },
    addMcp(inputs, form, mcp_node) {
      console.log("inputs", inputs);
      console.log("form", form);
      console.log("mcp_node", mcp_node);

      let mcpnodeData = JSON.parse(JSON.stringify(mcp_initData));
      mcpnodeData.data.data.inputs = inputs;
      mcpnodeData.data.data.settings.mcp_server_url = form.mcpServerUrl;
      mcpnodeData.data.data.settings.mcp_name = form.mcpName;
      mcpnodeData.data.data.settings.mcp_desc = form.mcpDesc;
      mcpnodeData.data.data.settings.mcp_tool_name = mcp_node;

      this.initNodeData("mcpnode", "MCP", mcpnodeData, true, true);
      this.visibleNode = false;
    },
    preAddNode(nodeType) {
      let graphData = this.graph.toJSON().cells;
      switch (nodeType) {
        case "api":
          this.initNodeData("apinode", "API", apiNode_initData, true, true);
          break;
        case "code":
          this.initNodeData(
            "pythonnode",
            i18n.t('workFlow.code'),
            pythonNode_initData,
            true,
            true
          );

          break;
        case "model":
          this.initNodeData(
            "llmnode",
            i18n.t('workFlow.modelNode'),
            LLMNode_initData,
            true,
            true
          );

          break;
        case "modelstream":
          this.initNodeData(
            "llmstreamingnode",
            i18n.t('workFlow.modelNodeStream'),
            LLMStreamingNode_initData,
            true,
            true
          );
          break;
        case "IntentionNode":
          this.initNodeData(
            "IntentionNode",
            "意图识别",
            intention_initData,
            true,
            false
          );
          break;
        case "switch":
          this.initNodeData(
            "switchnode",
            i18n.t('workFlow.splitterCode'),
            SwitchNode_initData,
            true,
            false
          );

          break;
        case "rag":
          this.initNodeData("ragnode", i18n.t('workFlow.knowLedge'), ragNode_initData, true, true);

          break;
        case "gui":
          this.initNodeData(
            "guinode",
            i18n.t('workFlow.GUI'),
            guiNode_initData,
            true,
            true
          );
          break;
        case "filegenerate":
          this.initNodeData(
            "filegeneratenode",
            "文档生成",
            filegenerate_initData,
            true,
            true
          );
          break;
        case "fileparse":
          this.initNodeData(
            "fileparsenode",
            "文档解析",
            fileparse_initData,
            true,
            true
          );
          break;
      }
      // this.graph.resetCells(this.cells);
      this.first = true;
      this.$nextTick(() => {
        let arr = this.getAllNodes(this.graph);
        for (let i = 0; i < arr.length; i++) {
          arr[i].removeTools();
        }
      });
      this.visibleNode = false;
    },
    zoom(value, label) {
      this.graph.zoomTo(value);
      this.graphScale = label;
      this.scaleVisible = false;
    },
    showScale() {
      this.$nextTick(() => {
        setTimeout(() => {
          this.scaleVisible = true;
        });
      });
    },
    //判断有几个连接桩
    setConnectors(n) {
      console.log("setConnectors nnnnn:", n);
      let portsItems = [];
      switch (n.type) {
        case "StartNode":
          portsItems = [
            {
              id: n.id + "-right",
              group: "right",
            },
          ];
          break;
        case "EndNode":
        case "EndStreamingNode":
          portsItems = [
            {
              id: n.id + "-left",
              group: "left",
            },
          ];
          break;
        case "SwitchNode":
        case "IntentionNode":
          portsItems = [
            {
              id: n.id + "-left",
              group: "left",
            },
          ];
          break;
        default:
          portsItems = [
            {
              id: n.id + "-left",
              group: "left",
            },
            {
              id: n.id + "-right",
              group: "right",
            },
          ];
          break;
      }
      return portsItems;
    },
    //获取后端数据
    async getWorkFlowData() {
      let res = await getWorkFlow({
        workflowID: this.workflowId,
      });
      //let res = mockData
      this.detail = res.data;

      let nodesData = [];
      let edgesData = [];
      let nodeNamesObj = {}; //缓存nodeid和nodeName的对应关系

      //判断是否是新建
      if (Object.keys(res.data.workflowSchema).length === 0) {
        nodesData = initGraphData.nodes;
        edgesData = initGraphData.edges;
      } else {
        nodesData = res.data.workflowSchema.nodes.map((n) => {
          nodeNamesObj[n.id] = n.name;
          //大模型特殊处理
          if (n.type === "LLMNode" || n.type === "LLMStreamingNode") {
            let _modelForm = {};
            n.data.inputs.forEach((m) => {
              if (
                ["input", "temperature", "top_p", "presence_penalty"].includes(
                  m.name
                )
              ) {
                _modelForm[m.name] = m.value.content;
              }
            });
            _modelForm.model = n.data.settings.model || "";
            n.data["modelForm"] = _modelForm;

            n.data.inputs = n.data.inputs.filter((p) => {
              return ![
                "input",
                "temperature",
                "top_p",
                "presence_penalty",
              ].includes(p.name);
            });
          }
          return n;
        });
        edgesData = res.data.workflowSchema.edges;
      }
      this.graphWidth = nodesData.length * 380 + nodesData.length * 80;
      this.graphScale =
        ((window.innerWidth / this.graphWidth) * 100).toFixed(0) + "%";

      this.graph.zoomTo((window.innerWidth / this.graphWidth).toFixed(2)); //this.nodeIdMap = nodeNamesObj;
      this.setNodeIdMap(nodeNamesObj);
      this.makeCanvasData(nodesData, edgesData);
    },
    //组装画布数据
    makeCanvasData(nodesData, edgesData) {
      let xMap = {};
      let yMap = {};
      let startId = "";
      let yIndexRecord = {};

      // 找到开始节点
      nodesData.map((n) => {
        if (n.type == "StartNode") {
          startId = n.id;
          xMap[n.id] = 0;
          yMap[n.id] = 0;
        }

        // 初始化的情况
        if (
          (n.type == "EndNode" || n.type == "EndStreamingNode") &&
          nodesData.length == 2
        ) {
          xMap[n.id] = 1;
          yMap[n.id] = 0;
        }
      });

      // 递归排序
      function findChild(id, index) {
        edgesData.forEach((n) => {
          if (n.source_node_id == id) {
            // if(!xMap[n.target_node_id]){
            xMap[n.target_node_id] = index;
            if (yIndexRecord[index] !== undefined) {
              yIndexRecord[index]++;
            } else {
              yIndexRecord[index] = 0;
            }
            yMap[n.target_node_id] = yIndexRecord[index];
            findChild(n.target_node_id, index + 1);
            // }
          }
          if (n.target_node_id == id && id == startId) {
            xMap[n.source_node_id] = index;
            yMap[n.source_node_id] = yIndexRecord[index] || 0;
          }
        });
      }

      findChild(startId, 1);
      // 重新校准y轴
      let yIndexRecordValidate = {};

      for (let o in xMap) {
        if (yIndexRecordValidate[xMap[o]] === undefined) {
          yIndexRecordValidate[xMap[o]] = 0;
          yMap[o] = 0;
        } else {
          yIndexRecordValidate[xMap[o]]++;
          yMap[o] = yIndexRecordValidate[xMap[o]];
        }
      }

      // let yIndexRecordLength = Object.keys(yIndexRecord).length;
      // for(let o =0;o<yIndexRecordLength;o++){

      // }

      //组装节点
      let _nodesData = nodesData.map((n, i) => {
        let x = xMap[n.id] !== undefined ? xMap[n.id] * 460 : 460;
        if (yMap[n.id] === undefined) {
          yIndexRecord[1] === undefined
            ? (yIndexRecord[1] = 0)
            : yIndexRecord[1]++;
        }
        let y =
          yMap[n.id] !== undefined ? yMap[n.id] * 300 : yIndexRecord[1] * 300;
        console.log({
          ...n,
          shape: "dag-node",
          x, // 连线间隔8
          y,
          id: n.id,
          icon: this.iconObj[n.type],
          ports: this.setConnectors(n),

          //将开始节点的output改为input，将输出节点的output改为input
          data: {
            ...n,
            //inputs:n.data.inputs,//n.type==='StartNode'?n.data.outputs:(n.type==='EndNode'?[]:n.data.inputs),
            //outputs:n.data.outputs,//n.type==='EndNode'?n.data.inputs:(n.type==='StartNode'?[]:n.data.outputs),
            preNode: i > 0 ? nodesData[i - 1] : null, //这样取的话开始和结束节点的inputs和outputs相反
            nodeIdMap: this.nodeIdMap,
          },
        });
        return {
          ...n,
          shape: "dag-node",
          // x: x + 799, // 连线间隔8
          // y: y + 200,
          x,
          y,
          id: n.id,
          icon: this.iconObj[n.type],
          ports: this.setConnectors(n),
          zIndex: 1000,
          //将开始节点的output改为input，将输出节点的output改为input
          data: {
            ...n,
            //inputs:n.data.inputs,//n.type==='StartNode'?n.data.outputs:(n.type==='EndNode'?[]:n.data.inputs),
            //outputs:n.data.outputs,//n.type==='EndNode'?n.data.inputs:(n.type==='StartNode'?[]:n.data.outputs),
            preNode: i > 0 ? nodesData[i - 1] : null, //这样取的话开始和结束节点的inputs和outputs相反
            nodeIdMap: this.nodeIdMap,
          },
        };
      });
      //组装连线
      let _edgesData = edgesData.map((n, i) => {
        return {
          ...n,
          shape: "dag-edge",
          zIndex: -1,
          source: {
            cell: n.source_node_id,
            port: n.source_port,
          },
          target: {
            cell: n.target_node_id,
            port: n.target_port,
          },
        };
      });

      let graphData = _nodesData.concat(_edgesData);
      this.canvasData = graphData;
      this.initNode(graphData);
      this.graph.centerContent();
    },
    // 初始化节点/边
    initNode(data, id) {
      let graph = this.graph;
      this.cells = [];
      data.forEach((item) => {
        if (item.shape === "dag-node") {
          this.cells.push(graph.createNode(item));
        } else {
          this.cells.push(graph.createEdge(item));
        }
      });
      graph.resetCells(this.cells);
      if (id) {
        const cell = this.graph.getCellById(id);
        this.graph.unselect(cell);
        // this.graph.resetSelection(cell);
      }
    },
    //初始化画布
    newGraph() {
      // 获取容器的中心点;
      // const width = document.getElementById("container").offsetWidth;
      // const height = document.getElementById("container").offsetHeight;
      // const centerX = width / 2;
      // const centerY = height / 2;
      // console.log(centerX, centerY);
      let graph = new Graph({
        container: document.getElementById("container"),
        // autoResize: true, // 开启会导致部分场景页面抖动
        grid: {
          //背景网格
          visible: true,
          // type: "doubleMesh",
          // args: [
          //   {
          //     color: "#eee", // 主网格线颜色
          //     thickness: 1, // 主网格线宽度
          //   },
          //   {
          //     color: "#ddd", // 次网格线颜色
          //     thickness: 1, // 次网格线宽度
          //     factor: 4, // 主次网格线间隔
          //   },
          // ],
        },
        // width: window.innerWidth - 90,
        // height: window.innerHeight - 40,
        // transform: {
        //   x: centerX,
        //   y: centerY,
        //   // 如果需要缩放，可以在这里设置scale
        // },
        autoResize: true,
        background: {
          color: "#F2F7FA",
        },
        panning: {
          enabled: true,
          eventTypes: ["leftMouseDown", "mouseWheel"],
        },
        mousewheel: {
          enabled: true,
          // modifiers: "ctrl",
          guard: (e) => {
            this.graphScale = (graph.zoom() * 100).toFixed() + "%";
            return true;
          },
          factor: 1.1,
          maxScale: 1.5,
          minScale: 0.5,
        },
        highlighting: {
          magnetAdsorbed: {
            name: "stroke",
            args: {
              attrs: {
                fill: "#fff",
                stroke: "#31d0c6",
                strokeWidth: 4,
              },
            },
          },
        },
        connecting: {
          snap: true,
          allowBlank: false,
          allowLoop: false,
          highlight: true,
          connector: "algo-connector", //注册的曲线
          connectionPoint: "anchor",
          anchor: "center",
          /*validateMagnet({ magnet }) {
                          return magnet.getAttribute('port-group') !== 'left'
                        },*/
          createEdge() {
            return graph.createEdge({
              shape: "dag-edge",
              attrs: {
                line: {
                  //strokeDasharray: '5 5',  //虚线
                },
              },
              zIndex: -2,
            });
          },
          validateMagnet({ magnet }) {
            // 节点上方的连接桩无法创建连线
            return magnet.getAttribute("port-group") !== "left";
          },
        },
      });
      graph.use(
        new Selection({
          enabled: true,
          multiple: true,
          // rubberband: true,
          movable: true,
          showNodeSelectionBox: false,
        })
      );
      /*graph.use(
        new Scroller({
          pageWidth: 1200,
          // pageHeight: window.innerHeight,
          enabled: true,
          pageVisible: false,
          pageBreak: false,
          pannable: false,
          autoResize: true,
          // pannable: true, //是否启用画布平移能力
        })
      );*/
      this.graph = graph;
      window.graph = graph;
      graph.on("edge:mouseenter", ({ edge }) => {
        if (edge.hasTool("button-remove")) {
          edge.removeTool("button-remove");
        }
        const nodeLeft = edge.getSourcePoint();
        const nodeRight = edge.getTargetPoint();
        edge.addTools({
          name: "button-remove",
          args: {
            distance: 0,
            offset: {
              x: (nodeRight.x - nodeLeft.x) / 2 + 4,
              y: (nodeRight.y - nodeLeft.y) / 2,
            },
          },
          onClick: (view) => {
            edge.removeTools();
            if (edge.hasTool("button-remove")) {
              edge.removeTool("button-remove");
            }
            graph.removeEdge(edge);
            var button = document.getElementsByClassName(
              "x6-graph-svg-decorator"
            );
            if (button[0]) {
              button[0].innerHTML = "";
            }
          },
        });
        edge.attr({
          line: {
            stroke: "#409EFF",
            strokeWidth: 3,
          },
        });
      });
      graph.on("edge:mouseleave", ({ edge }) => {
        edge.removeTools("button-remove");
        edge.attr({
          line: {
            stroke: "#8f8f8f",
            strokeWidth: 2,
          },
        });
      });

      graph.on("node:mouseenter", (node) => {
        node.e.stopPropagation();
        node.e.preventDefault();
        let ports = node.node.getPorts();
        ports.forEach((port) => {
          node.node.setPortProp(port.id, ["attrs", "circle"], {
            fill: "#2468f2",
            stroke: "#2468f2",
            r: 7,
          });
        });
      });
      graph.on("node:mouseleave", (node) => {
        node.e.stopPropagation();
        node.e.preventDefault();
        const ports = node.node.getPorts();
        ports.forEach((port) => {
          node.node.setPortProp(port.id, ["attrs", "circle"], {
            fill: "#8f8f8f",
            stroke: "#8f8f8f",
            r: 2,
          });
        });
      });
      graph.on("node:removed", (node) => {
        //e.stopPropagation();
        this.onNodeDelete(node);
        this.debouncedSave();
        this.$refs["debug"].preClose();
        this.$refs["config"].preClose();
      });
      graph.on("edge:removed", ({ edge }) => {
        edge.removeTools();
        graph.removeEdge(edge);
        var button = document.getElementsByClassName(
          "x6-graph-svg-decorator"
        )[0];
        if (button) {
          button.innerHTML = "";
        }
        this.$refs["debug"].preClose();
        this.$refs["config"].preClose();
        // let dom = document.getElementsByClassName("x6-node-selected")[0];
        // if (dom) {
        //   dom.classList.remove("x6-node-selected");
        // }

        console.log("删除连线:", edge);
        //如果是分支器节点，删除conditions的target_node_id
        if (edge.source.cell.indexOf("switchnode") > -1) {
          const switchNodeId = edge.store.data.source.cell;
          const portId = edge.store.data.source.port;
          let elem = graph.getCellById(switchNodeId);
          if (!elem) {
            return;
          }

          const switchRightPorts = graph
            .getCellById(switchNodeId)
            .port.ports.filter((item) => {
              if (/-right/.test(item.id)) {
                return item;
              }
            });
          const index = switchRightPorts.findIndex(
            (item) => item.id === portId
          ); // -1 是去除左边连接点，左边连接点默认是 0

          if (edge.delSource !== "condition") {
            let graphData = this.graph.toJSON().cells;
            let nodeData = graphData.filter((n, i) => {
              return n.shape === "dag-node";
            });
            nodeData.forEach((n) => {
              if (n.id === edge.store.data.source_node_id) {
                // graph.getCellById(edge.store.data.source_node_id)
                let item = n.data.data.inputs[index];
                console.log(graph.getCellById(edge.store.data.source_node_id));
                let _item = {
                  ...item,
                  target_node_id: "",
                };
                this.$set(n.data.data.inputs, index, _item);
              }
            });
            this.initNode(graphData, edge.store.data.source_node_id);
          }
        }

        if (
          edge.store.data.source_node_id
            .toLowerCase()
            .indexOf("intentionnode") > -1
        ) {
          const switchNodeId = edge.store.data.source.cell;
          const portId = edge.store.data.source.port;
          let elem = graph.getCellById(switchNodeId);
          if (!elem) {
            return;
          }

          const switchRightPorts = graph
            .getCellById(switchNodeId)
            .port.ports.filter((item) => {
              if (/-right/.test(item.id)) {
                return item;
              }
            });
          const index = switchRightPorts.findIndex(
            (item) => item.id === portId
          ); // -1 是去除左边连接点，左边连接点默认是 0

          if (edge.delSource !== "condition") {
            let graphData = this.graph.toJSON().cells;
            let nodeData = graphData.filter((n, i) => {
              return n.shape === "dag-node";
            });
            nodeData.forEach((n) => {
              if (n.id === edge.store.data.source_node_id) {
                // graph.getCellById(edge.store.data.source_node_id)
                n.data.data.settings.intentions[index].target_node_id = "";
              }
            });
            this.initNode(graphData, edge.store.data.source_node_id);
          }
        }

        this.debouncedSave();
        // 在这里处理边移除的逻辑
        this.initNode(
          this.graph.toJSON().cells,
          edge.store.data.source_node_id
        );
        // var button = document.getElementsByClassName(
        //   "x6-graph-svg-decorator"
        // )[0];
        // if (button) {
        //   button.innerHTML = "";
        // }
        setTimeout(() => {
          this.updatePorts();
        }, 10);
      });
      // 监听选择变化事件
      graph.on("selection:changed", ({ selected }) => {
        // selected 是当前选中的元素数组
        console.log("当前选中的元素:", selected);
        /*if (selected.length > 0) {
          this.node = selected[0];
        }*/
      });
      //连线事件
      graph.on("edge:connected", ({ edge }) => {
        this.$refs["debug"].preClose();
        this.$refs["config"].preClose();
        graph.stopBatch(edge.store.previous.id, { abortConnection: true });
        edge.store.data.source_node_id = edge.store.data.source.cell;
        edge.store.data.target_node_id = edge.store.data.target.cell;

        // ************** 获取节点右边连接点下标位置 ***************************
        const switchNodeId = edge.store.data.source.cell;
        const portId = edge.store.data.source.port;

        const switchRightPorts = graph
          .getCellById(switchNodeId)
          .port.ports.filter((item) => {
            if (/-right/.test(item.id)) {
              return item;
            }
          });
        const index = switchRightPorts.findIndex((item) => item.id === portId); // -1 是去除左边连接点，左边连接点默认是 0

        // const TargetNodeId = edge.store.data.target.cell;
        // const node = graph.getCellById(TargetNodeId);
        // 指定节点ID
        const nodeId = edge.store.data.target.cell;

        // 获取所有边并过滤出连接指定节点的边
        const connectedEdges = graph.getEdges().filter((edge) => {
          const sourceId = edge.getSourceCellId();
          const targetId = edge.getTargetCellId();
          return sourceId === nodeId || targetId === nodeId;
        });
        let isOnline = [];
        // 输出连接的所有节点id
        connectedEdges.forEach((edges, i) => {
          let res = edges.store.data.source.cell.includes("switchnode");

          let portLeft = nodeId + "-left";
          if (edges.target.port === portLeft && res) {
            edges.source.cell !== isOnline[0] &&
              isOnline.push(edges.source.cell);
          }
        });
        if (isOnline.length > 1) {
          // 清除当前的连线;
          graph.removeEdge(edge);
          setTimeout(() => {
            var button = document.getElementsByClassName(
              "x6-graph-svg-decorator"
            );
            if (button[0]) {
              button[0].innerHTML = "";
            }
          }, 10);

          return false; // 阻止创建连线
        }

        // ************** end ***************************
        //如果是分支器节点，保存一下目标节点
        if (edge.store.data.source_node_id.indexOf("switchnode") > -1) {
          edge.target_node_id = edge.store.data.target_node_id;
          let graphData = this.graph.toJSON().cells;
          let nodeData = graphData.filter((n, i) => {
            return n.shape === "dag-node";
          });
          nodeData.forEach((n) => {
            if (n.id === edge.store.data.source_node_id) {
              let item = n.data.data.inputs[index];
              let _item = {
                ...item,
                target_node_id: edge.store.data.target_node_id,
              };
              this.$set(n.data.data.inputs, index, _item);
            }
          });
          this.initNode(graphData, edge.store.data.source_node_id);
        }

        //如果是分支器节点，保存一下目标节点

        if (
          edge.store.data.source_node_id
            .toLowerCase()
            .indexOf("intentionnode") > -1
        ) {
          edge.target_node_id = edge.store.data.target_node_id;
          let graphData = this.graph.toJSON().cells;
          let nodeData = graphData.filter((n, i) => {
            return n.shape === "dag-node";
          });
          nodeData.forEach((n) => {
            if (n.id === edge.store.data.source_node_id) {
              n.data.data.settings.intentions[index].target_node_id =
                edge.store.data.target_node_id;
            }
          });
          this.initNode(graphData, edge.store.data.source_node_id);
        }

        //连完线以后重置一下关联关系
        //this.initNode(this.graph.toJSON().cells); //废弃 会导致线覆盖在节点之上，无法实现多分支； zIndex设置无效
        this.cells.push(graph.createEdge(edge.store.data));
        setTimeout(() => {
          // var button = document.getElementsByClassName(
          //   "x6-graph-svg-decorator"
          // );
          // if (button[0]) {
          //   button[0].innerHTML = "";
          // }
          // this.initNode(this.graph.toJSON().cells);
        }, 50);
        this.debouncedSave();
      });

      //节点点击事件
      graph.on("edge:click", ({}) => {
        this.visibleNode = false;
        // edge.removeTools();
        // graph.removeEdge(edge);

        this.$refs["debug"].preClose();
        this.$refs["config"].preClose();
      });
      graph.on("node:port:click", ({}) => {
        // edge.removeTools();
        // graph.removeEdge(edge);

        this.$refs["debug"].preClose();
        this.$refs["config"].preClose();
      });
      graph.on("node:click", ({ e, node, view }) => {
        this.visibleNode = false;
        this.node = node;
        this.$refs["config"].setConfig(this.graph, node);
        this.$refs["debug"].preClose();
        node.position(node.getBBox().center);
      });
      graph.on("blank:click", (args) => {
        this.visibleNode = false;

        // args 包含事件的相关信息
        setTimeout(() => {
          this.$refs["debug"].preClose();
          this.$refs["config"].preClose();
          var button = document.getElementsByClassName(
            "x6-graph-svg-decorator"
          );
          if (button[0]) {
            button[0].innerHTML = "";
          }
        }, 50);
      });
      // 画布更新事件
      graph.on(
        "render:done",
        () => {
          // this.setPorts();
          if (!this.first) {
            // setTimeout(() => {
            this.setPorts();
            this.first = true;
            // }, 3000);
            //   this.first = true;
          }
        }
        // }
      );
      graph.on("node:added", (args) => {
        const node = args.node; // 获取添加的节点实例
        setTimeout(() => {
          if (
            node.data.type === "SwitchNode" ||
            node.data.type === "IntentionNode"
          ) {
            let yList = [];
            let yStart = 55;
            if (node.data.type === "IntentionNode") {
              const startDom = document
                .getElementById(node.id)
                .getElementsByClassName("node-params")[0];
              yStart = yStart + startDom.clientHeight + 45;
            }
            const dom = document
              .getElementById(node.id)
              .getElementsByClassName("switch-item");
            for (let i = 0; i < dom.length; i++) {
              if (i === 0) {
                yList[i] = yStart + dom[i].clientHeight / 2;
              } else {
                yList[i] =
                  yList[i - 1] +
                  dom[i - 1].clientHeight / 2 +
                  dom[i].clientHeight / 2 +
                  5;
              }
              node.addPort({
                group: "absolute",
                id: node.id + i + "-right",
                args: {
                  x: "100%",
                  y: yList[i],
                },
              });
            }
          } else {
            let ee = document.querySelector(
              `.x6-node[data-cell-id="${node.id}"] foreignObject body .dag-node`
            );
            console.log(
              `.x6-node[data-cell-id="${node.id}"] foreignObject body .dag-node`
            );
            node.resize(ee.offsetWidth, ee.offsetHeight);
            const ports = document.querySelectorAll(".x6-port-body");
            for (let i = 0, len = ports.length; i < len; i = i + 1) {
              ports[i].style.visibility = "visible";
            }
          }
        }, 50);
      });

      graph.on("node:ports:removed", (obj) => {
        // setTimeout(() => {
        let ee = document.querySelector(
          `.x6-node[data-cell-id="${obj.node.id}"] foreignObject body .dag-node`
        );
        obj.node.resize(ee.offsetWidth, ee.offsetHeight);
        const ports = document.querySelectorAll(".x6-port-body");
        for (let i = 0, len = ports.length; i < len; i = i + 1) {
          ports[i].style.visibility = "visible";
        }
        // }, 50);
      });
      graph.on("node:ports:added", (obj) => {
        // setTimeout(() => {
        console.log(obj);
        if (obj.added.length === 2) {
          const node = obj.node;
          let lastPortID =
            "switchnode_" + (obj.node.port.ports.length - 3) + "-right";

          const edges = [];
          this.graph.getEdges().forEach((edge) => {
            const sourcePortId = edge.getSourcePortId();
            const targetPortId = edge.getTargetPortId();
            if (sourcePortId === lastPortID || targetPortId === lastPortID) {
              edges.push(edge);
            }
          });
          console.log(edges);
          if (edges.length > 0) {
            let newPort = node.port.ports;
            edges[0].setSource({
              cell: node.id,
              port: newPort[newPort.length - 1].id,
            });
          }
          let ee = document.querySelector(
            `.x6-node[data-cell-id="${node.id}"] foreignObject body .dag-node`
          );
          node.resize(ee.offsetWidth, ee.offsetHeight);
          const portsdom = document.querySelectorAll(".x6-port-body");
          for (let i = 0, len = portsdom.length; i < len; i = i + 1) {
            portsdom[i].style.visibility = "visible";
          }
        }
        // }, 50);
      });
      // this.graph.fitView();
      /*const mini = new MiniMap({
        container: document.getElementById("minimap"),
        // width: window.innerWidth,
        // height: window.innerHeight,
        width: 200,
        height: 120,
        scalable: true,
        // maxScale: 2,
        // graph,
        minScale: 0.5,
        graphOptions: {
          // cell: {
          //   attrs: {
          //     body: {
          //       stroke: "#8f8f8f",
          //       fill: "#fff",
          //     },
          //   },
          // },
          // createCellView(cell) {
          //   // 可以返回三种类型数据
          //   // 1. null: 不渲染
          //   // 2. undefined: 使用 X6 默认渲染方式
          //   // 3. CellView: 自定义渲染
          //   if (cell.isEdge()) {
          //     // return null;
          //   }
          //   if (cell.isNode()) {
          //     // return cell.attr({
          //     //   body: {
          //     //     stroke: "#8f8f8f",
          //     //     // strokeWidth: 7,
          //     //     fill: "#fff",
          //     //     // rx: 6,
          //     //     // ry: 6,
          //     //   },
          //     // });
          //   }
          // },
        },
      });
      graph.use(mini);
      // mini.init();

      graph.on("scale", () => {
        // mini.update(graph);
      });

      graph.on("translate", () => {
        // mini.update(graph);
      });

      graph.on("change:size", () => {
        // mini.update(graph);
      });*/
    },
    onNodeDelete(node) {
      let graphData = this.graph.toJSON().cells;
      //判断没有上个节点的，将输入的引用值清空
      graphData.forEach((n) => {
        console.log(n.source_node_id, node.node.id);
        if (n.shape === "dag-node") {
          n.data.data.inputs.forEach((m) => {
            if (
              m.value.type === "ref" &&
              m.value.content.ref_node_id === node.node.id
            ) {
              m.value.content.ref_node_id = "";
              m.value.content.ref_var_name = "";
            }
          });
        }
        //从this.cells里移除
        this.cells.forEach((m, j) => {
          if (node.node.id === m.id) {
            this.cells.splice(j, 1);
          }
        });
      });
      //连完线以后重置一下关联关系
      this.initNode(this.graph.toJSON().cells);
    },
    // 获取所有节点
    getAllNodes(graph) {
      return graph.getNodes();
    },
    //注册自定义工作流
    registerCustomNode() {
      register({
        shape: "dag-node",
        width: 380,
        height: 150,
        component: DagNode,
        zIndex: 10,
        attrs: {
          body: {
            stroke: "#8f8f8f",
            strokeWidth: 7,
            fill: "#fff",
            rx: 6,
            ry: 6,
          },
        },
        ports: {
          groups: {
            left: {
              position: "left",
              attrs: {
                circle: {
                  r: 2,
                  magnet: true,
                  stroke: "#8f8f8f",
                  strokeWidth: 2,
                  fill: "#8f8f8f",
                },
              },
            },
            right: {
              position: "right",
              attrs: {
                circle: {
                  r: 2,
                  magnet: true,
                  stroke: "#8f8f8f",
                  strokeWidth: 2,
                  fill: "#8f8f8f",
                },
              },
            },
            absolute: {
              position: "absolute",
              attrs: {
                circle: {
                  r: 2,
                  magnet: true,
                  stroke: "#8f8f8f",
                  strokeWidth: 2,
                  fill: "#8f8f8f",
                },
              },
            },
          },
        },
      });
    },
    //注册连接线
    registerEdge() {
      Graph.registerEdge(
        "dag-edge",
        {
          inherit: "edge",
          zIndex: -1,
          attrs: {
            line: {
              stroke: "#8f8f8f",
              strokeWidth: 2,
              targetMarker: {
                name: "block", // 实心箭头
              },
              sourceMarker: null,
            },
          },
        },
        true
      );
    },
    //注册连接桩
    registerConnector() {
      // 注册连线
      Graph.registerConnector(
        "algo-connector",
        (sourcePoint, targetPoint) => {
          const hgap = Math.abs(targetPoint.x - sourcePoint.x);
          const path = new Path();
          path.appendSegment(
            Path.createSegment("M", sourcePoint.x - 4, sourcePoint.y)
          );
          path.appendSegment(
            Path.createSegment("L", sourcePoint.x + 12, sourcePoint.y)
          );
          // 水平三阶贝塞尔曲线
          path.appendSegment(
            Path.createSegment(
              "C",
              sourcePoint.x < targetPoint.x
                ? sourcePoint.x + hgap / 2
                : sourcePoint.x - hgap / 2,
              sourcePoint.y,
              sourcePoint.x < targetPoint.x
                ? targetPoint.x - hgap / 2
                : targetPoint.x + hgap / 2,
              targetPoint.y,
              targetPoint.x - 6,
              targetPoint.y
            )
          );
          path.appendSegment(
            Path.createSegment("L", targetPoint.x + 2, targetPoint.y)
          );

          return path.serialize();
        },
        true
      );
    },

    getCanvasGraphData() {
      let graphData = this.graph.toJSON().cells;
      console.log("#####getCanvasGraphData", graphData);

      let nodeData = graphData.filter((n, i) => {
        return n.shape === "dag-node";
      });

      let nodes = nodeData.map((n) => {
        return {
          id: n.id,
          name: n.data.name,
          type: n.type,
          data: {
            outputs: n.data.data.outputs,
            inputs: n.data.data.inputs,
            settings: n.data.data.settings,
            modelForm: n.data.data.modelForm, //大模型
          },
          validate: n.data.validate,
          /*data: {
            outputs: n.data.data.outputs.filter((n) => {
              return n.name;
            }),
            inputs: n.data.data.inputs.filter((n) => {
              return n.name;
            }),
            settings: n.data.data.settings,
          },*/
        };
      });

      let edgesData = graphData.filter((n) => {
        return n.shape === "dag-edge" || n.shape === "edge";
      });

      let edges = edgesData.map((m) => {
        return {
          source_node_id: m.source.cell,
          source_port: m.source.port,
          target_node_id: m.target.cell,
          target_port: m.target.port,
        };
      });

      //按照边的连线顺序连线  //todo: edges为空时判断不生效
      /*let sortNodes = [];
      let endNode = {};
      let sortNodesMap = {}
      edges.forEach((n) => {
        nodes.forEach((m) => {
          if (m.id === n.source_node_id && !sortNodesMap[m.id]) {
            sortNodesMap[m.id] = m
            sortNodes.push(m);
          }
          if (m.type === "EndNode") {
            endNode = m;
          }
        });
      });
      sortNodes.push(endNode);
      return { nodes: sortNodes, edges };*/
      return { nodes, edges };
    },
    debouncedSave() {
      if (this.timer) {
        clearTimeout(this.timer);
      }
      this.timer = setTimeout(() => {
        this.preSave(true);
      }, 1500);
    },
    async preSave(isHideMessage) {
      let workflowSchema = this.getCanvasGraphData();

      // 如果schmea没有变更，就不出发保存

      // console.log(JSON.stringify(workflowSchema) , this.oldSchmea,isHideMessage,(JSON.stringify(workflowSchema)=== this.oldSchmea))

      if (JSON.stringify(workflowSchema) === this.oldSchmea && isHideMessage) {
        return;
      } else {
        this.oldSchmea = JSON.stringify(workflowSchema);
      }

      this.executeSuccess = false;
      console.log("@@@workflowSchema:", workflowSchema);

      let params = {
        configName: this.detail.configName,
        configENName: this.detail.configENName,
        configDesc: this.detail.configDesc,
        workflowID: this.workflowId,
        workflowSchema,
      };

      workflowSchema.nodes.forEach((n) => {
        //模型节点特殊处理
        if (n.type === "LLMNode" || n.type === "LLMStreamingNode") {
          for (var key in n.data.modelForm) {
            if (key !== "model") {
              n.data.inputs.push({
                name: key,
                desc: LLMNodeDescObj[key], //"重复惩罚, 用通过对已生成的token增加惩罚，减少重复生成的现象，值越大表示惩罚越大",
                type: "float",
                list_schema: null,
                object_schema: null,
                value: {
                  content: n.data.modelForm[key],
                  type: "generated",
                },
                extra: {
                  location: "body",
                },
              });
            }
          }
          n.data.settings.model = n.data.modelForm.model;
          delete n.data.modelForm;
        }
        //分支器节点特殊处理
        /*if (n.type === "SwitchNode") {
          workflowSchema.edges.forEach((m) => {
            if (m.source_node_id === n.id) {
              n.data.inputs.forEach((k) => {
                k.target_node_id = m.source_node_id;
              });
            }
          });
        }*/
      });

      let res = await saveWorkFlow(params);
      if (res.code === 0 && !isHideMessage) {
        this.$message.success("画布保存成功");
      }
    },
    preCreate() {
      this.$refs["create_ref"].openDialog();
    },
    async preDebug() {
      this.$refs["config"].preClose();
      let workflowSchema = this.getCanvasGraphData();
      let hasToken = false;
      workflowSchema.nodes.forEach((item) => {
        if (item.type == "StartNode") {
          if (item.data.settings.staticAuthToken) {
            hasToken = true;
            return;
          }
        }
      });
      // 取消 token 相关
      /*if (!hasToken) {
        this.$refs["app-select"].openDialog();
        return;
      }*/

      this.$refs["debug"].openDialog(workflowSchema);
    },
    setToken(token) {
      const nodes = this.getAllNodes(this.graph);
      nodes.forEach((item) => {
        if (item.store.data.type == "StartNode") {
          this.$set(
            item.store.data.data.data.settings,
            "staticAuthToken",
            token
          );
        }
      });
      this.preSave(true);
    },
    async doDebug(data) {
      //渲染节点
      let workflowSchema = this.getCanvasGraphData();
      this.oldSchmea = JSON.stringify(workflowSchema);
      //先loading
      let loadingArr = JSON.parse(JSON.stringify(workflowSchema.nodes)).map(
        (n) => {
          return {
            ...n,
            node_id: n.id,
            node_status: "loading",
            inputs: {},
            node_execute_cost: "",
            node_message: "",
            outputs: {},
          };
        }
      );
      this.showNodeStatus(loadingArr);
      //模型节点特殊处理
      workflowSchema.nodes.forEach((n) => {
        if (n.type === "LLMNode" || n.type === "LLMStreamingNode") {
          for (var key in n.data.modelForm) {
            if (key != "model") {
              n.data.inputs.push({
                name: key,
                desc: LLMNodeDescObj[key], //"重复惩罚, 用通过对已生成的token增加惩罚，减少重复生成的现象，值越大表示惩罚越大",
                type: "float",
                list_schema: null,
                object_schema: null,
                value: {
                  content: n.data.modelForm[key],
                  type: "generated",
                },
                extra: {
                  location: "body",
                },
              });
            }
          }

          n.data.settings.model = n.data.modelForm.model;
          delete n.data.modelForm;
        }
        if (n.type === "GUIAgentNode") {
          for (let i = 0; i < n.data.inputs.length; i++) {
            n.data.inputs[i].extra.location = "body";
          }
        }
      });

      if (this.isStream) {
        this.$refs.debug.doSend({
          workflowSchema,
          data,
          workflowID: this.workflowId,
        });
        return;
      }
      let res = await runWorkFlow({
        workflowSchema,
        data,
        workflowID: this.workflowId,
      });
      if (res.code === 0) {
        setTimeout(() => {
          this.getWorkFlowStatus(res.executeID);
        }, 500);
      } else {
        //解除loading
        let loadingArr = JSON.parse(JSON.stringify(workflowSchema.nodes)).map(
          (n) => {
            return {
              ...n,
              node_id: n.id,
              node_status: "",
            };
          }
        );
        this.showNodeStatus(loadingArr);
      }
    },
    async getWorkFlowStatus(executeID) {
      let res = await getWorkFlowStatus({ executeID });
      this.$refs["debug"].setDebugResult(res.data.result);
      this.showNodeStatus(res.data.result.node_result);
      //把上次运行结果放在store里
      this.setLastDebugResult(res.data.result);
      if (res.data.result && res.data.result.execute_status == "success") {
        this.executeSuccess = true;
      }
    },
    cancelRun() {
      let workflowSchema = this.getCanvasGraphData();
      console.log("取消运行:", workflowSchema);
      //先loading
      let loadingArr = JSON.parse(JSON.stringify(workflowSchema.nodes)).map(
        (n) => {
          return {
            ...n,
            node_id: n.id,
            node_status: "",
          };
        }
      );
      this.showNodeStatus(loadingArr);
      this.$refs["debug"].preClose();
    },
    // 显示节点状态
    showNodeStatus(statusList) {
      console.log("statusList:", statusList);
      statusList.forEach((n) => {
        const { node_id } = n;
        let graph = this.graph;
        let dagNode = graph.getCellById(node_id);
        const data = dagNode.getData();
        delete data.node_status;
        delete data.res_inputs;
        delete data.res_outputs;
        dagNode.setData({
          ...data,
          ...n,
          node_status: n.node_status,
          res_inputs: n.inputs,
          res_outputs: n.outputs,
        });
        console.log("this.node:", dagNode);
      });
      console.log("this.cells:", this.cells);

      //this.graph.resetCells(this.cells); //this.cells不是最新的数据
      this.initNode(this.graph.toJSON().cells);
    },
    //查看上次运行结果
    preGetLastDebug() {
      if (JSON.stringify(this.lastDebugResult) !== "{}") {
        this.showNodeStatus(this.lastDebugResult.node_result);
      }
    },
    // 居中视图
    handleCenterView() {
      this.graph.centerContent();
    },
    handleSetFolt(val) {
      this.folt = val;
      sessionStorage.setItem("activeNode", val ? ["3"] : ["1", "2"]);
      setTimeout(() => {
        this.updatePorts();
      }, 101);
      // this.activeFlot = val ? ["3"] : ["1", "2"];
      // console.log(this.activeFlot);
    },
    setPorts(n) {
      const nodes = this.getAllNodes(this.graph);
      nodes.map((node) => {
        let ee = document.querySelector(
          `.x6-node[data-cell-id="${node.id}"] foreignObject body .dag-node`
        );
        node.resize(ee.offsetWidth, ee.offsetHeight);
        const ports = document.querySelectorAll(".x6-port-body");
        for (let i = 0, len = ports.length; i < len; i = i + 1) {
          ports[i].style.visibility = "visible";
        }
        // console.log(node.id);
        if (
          node.data.type === "SwitchNode" ||
          node.data.type === "IntentionNode"
        ) {
          let yList = [];
          let yStart = 55;
          if (node.data.type === "IntentionNode") {
            const startDom = document
              .getElementById(node.id)
              .getElementsByClassName("node-params")[0];
            yStart = yStart + startDom.clientHeight + 45;
          }
          const dom = document
            .getElementById(node.id)
            .getElementsByClassName("switch-item");
          for (let i = 0; i < dom.length; i++) {
            if (i === 0) {
              yList[i] = yStart + dom[i].clientHeight / 2;
            } else {
              yList[i] =
                yList[i - 1] +
                dom[i - 1].clientHeight / 2 +
                dom[i].clientHeight / 2 +
                10;
            }
            node.addPort({
              group: "absolute",
              id: node.id + i + "-right",
              args: {
                x: "100%",
                y: yList[i],
              },
            });
          }
        } else {
        }
      });
    },
    updatePorts() {
      const nodes = this.getAllNodes(this.graph);
      nodes.map((node) => {
        let ee = document.querySelector(
          `.x6-node[data-cell-id="${node.id}"] foreignObject body .dag-node`
        );
        node.resize(ee.offsetWidth, ee.offsetHeight);
        if (
          node.data.type === "SwitchNode" ||
          node.data.type === "IntentionNode"
        ) {
          let yList = [];
          let yStart = 55;
          if (node.data.type === "IntentionNode") {
            const startDom = document
              .getElementById(node.id)
              .getElementsByClassName("node-params")[0];
            yStart = yStart + startDom.clientHeight + 45;
          }
          const ports = node.port.ports;
          if (ports[0].group === "left") {
            ports.shift();
          }
          const dom = document
            .getElementById(node.id)
            .getElementsByClassName("switch-item");
          for (let i = 0; i < dom.length; i++) {
            if (i === 0) {
              yList[i] = yStart + dom[i].clientHeight / 2;
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
    },
    publish() {
      this.$refs["publish_ref"].openDialog({
        id: this.workflowId,
      });
    },
    preAddSwitch(index) {},
  },
};
</script>

<style lang="scss">
@import "@/style/workflow.scss";
.workflow-list {
  padding: 0 !important;
}
.workflow,
.container {
  width: 100%;
  height: 100%;
}
.footer-setting {
  width: 380px;
  display: flex;
  justify-content: space-between;
  padding: 5px 10px;
  position: fixed;
  bottom: 20px;
  left: 0;
  right: 0;
  margin: auto;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 12px;
  box-shadow: 0 4px 16px #99999f;

  i {
    font-weight: bold;
  }
  .addNode_box {
    margin-right: 10px;
  }
  .el-button--mini {
    padding: 5px;
  }
  .segmentation {
    display: inline-block;
    width: 1px;
    height: 30px;
    background: #e8e9eb;
  }
}
.node-items {
  border: 1px solid #ddd;
  & + div {
    border-top: 1px solid #ddd;
    padding: 10px;
    cursor: pointer;
    margin-bottom: 10px;
  }
}
.workflow-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  background: #fff;
  border-bottom: 1px solid #ddd;
  padding: 15px 20px;
  height: 47px;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  i {
    cursor: pointer;
  }
  .el-icon-arrow-left {
    float: left;
  }
  .title_box {
    display: flex;
  }
  .header-left {
    display: flex;
    align-items: center;
    > span {
      padding-left: 10px;
    }
  }
}
.x6-node {
  .dag-node {
    &:hover {
      box-shadow: 0 0 10px #ccc;
    }
  }
}
.x6-node-selected {
  .dag-node {
    box-shadow: 0 0 10px rgba(36, 104, 242, 0.4) !important;
    border: 1.5px solid #2468f2;
  }
}
.scale-btn {
  margin: 0 !important;
  // border: none;
  background: transparent !important;
  color: #333 !important;
  border: 0 !important;
  &:hover {
    cursor: pointer;
    color: #333;
    background: #f7f7f9 !important;
  }
  span {
    font-size: 12px;
  }
}
.scale-btn:focus {
  background: none !important;
}
.folt {
  padding-bottom: 2.5px;
  padding-top: 2.5px;
  span {
    display: flex;
    flex-direction: column;
    transform: scale(0.8);
  }
}
#minimap {
  position: absolute;
  left: 20px;
  bottom: 20px;
  border: 1px solid #d4d6d9;
  border-radius: 8px;

  // width: 200px;
  // height: 150px;
  .x6-widget-minimap-viewport {
    width: 100px !important;
    height: 50px !important;
    border: 2px solid #8f8f8f;
  }

  .x6-widget-minimap-viewport-zoom {
    border: 2px solid #8f8f8f;
  }
}
// .x6-graph-scroller-content {
//   width: 100vw !important;
//   height: 100vh !important;
// }
.x6-graph-scroller {
  &::-webkit-scrollbar {
    width: 0;
    height: 0;
  }
}
.x6-widget-minimap {
  background: #f7f7f9;
  border-radius: 8px;

  .x6-graph {
    background: #fff;
  }
}
.footer-setting {
  .scale-btn {
    span, .el-icon-arrow-down {
      color: #333 !important;
    }
  }
  .el-button {
    span {
      vertical-align: text-top;
    }
    i {
      font-size: 16px;
      font-weight: bold !important; /*图标加粗*/
    }
  }
  .el-button--mini {
    padding: 0 5px;
  }
}
.is-disabled {
  i {
    color: #9c9fa4 !important;
  }
}
</style>

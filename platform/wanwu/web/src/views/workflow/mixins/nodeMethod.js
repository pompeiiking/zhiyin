import { mapState } from "vuex";
export default {
    props: ["graph", "node"],
    data() {
        return {
            settings: {},
            nodeData: {},
            preNode: {},
            preNodeOutputs: [],
            preAllNode: [],
        };
    },
    computed: {
        ...mapState({
            nodeIdMap: (state) => state.workflow.nodeIdMap,
        }),
    },
    created() {
        this.nodeData = this.node.data;


        this.settings = this.node.data.data.settings;
        this.preNode = this.node.data.preNode;
    },
    mounted(){
        this.getPreNode(this.nodeData.id);
    },
    methods: {
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
            if (preNodeArr.length) {
                let _preId = ''
                //preNodeId = preNodeArr[0].source_node_id || preNodeArr[0].source.cell;
                preNodeArr.forEach(m=>{
                    _preId = m.source_node_id || m.source.cell
                    if (_preId) {
                        //上一个节点
                        let preNode = graphData.filter((n) => {
                            return n.shape === "dag-node" && n.id === _preId;
                        })[0];


                        if(preNode.data  && preNode.data.name && preNode.data.name != preNode.name){
                            preNode.name = preNode.data.name
                        }
                        

                        //判断是否有重复节点
                        let exitIds = this.preAllNode.map(p=>{
                            return p.id
                        })
                        //console.log('##exitIds:',exitIds,preNode.id)
                        if(!(exitIds.includes(preNode.id))){
                            this.preAllNode.push(preNode)
                        }
                        this.getPreNode(preNode.id);
                    }
                })
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

        selectTypeChange(val, i) {
            switch (val) {
                case "ref":
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
                    this.nodeData.data.inputs[i].value.content = '';
                    this.$set(this.nodeData.data.inputs, i, newItem);
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
        },
        preDelInputsParams(index) {
            this.nodeData.data.inputs.splice(index, 1);
            this.updatePorts()
        },
        preDelOutputsParams(index) {
            this.nodeData.data.outputs.splice(index, 1);
            this.updatePorts()
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
    }
};

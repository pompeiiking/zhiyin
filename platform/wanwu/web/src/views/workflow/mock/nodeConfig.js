import {i18n} from "@/lang"
const vuex = JSON.parse(localStorage.getItem("access_cert"));
export const apiNode_initData = {
    "id": "apinode",
    "name": "API",
    "type": "ApiNode",
    "shape": "dag-node",
    "x": 40,
    "y": 40,
    "icon": require('../components/img/api.png'),
    ports:[{
        id: 'apinode-left',
        group: 'left',
    },
    {
        id: 'apinode-right',
        group: 'right',
    }],
    "data": {
        "id": "apinode",
        "name": "API",
        "type": "ApiNode",
        "shape": "dag-node",
        "x": 40,
        "y": 40,
        "icon": require('../components/img/api.png'),
        "data": {
            "inputs": [
                {
                    "desc": "",
                    "list_schema": null,
                    "name": "",
                    "object_schema": null,
                    "required": false,
                    "type": "string",
                    "value": {
                        "content": {
                            "ref_node_id": "",
                            "ref_var_name": ""
                        },
                        "type": "ref"
                    }
                }
            ],
            "outputs": [
            ],
            "settings": {
                "content_type": "application/json",
                "headers": {},
                "http_method": "GET",
                "url": ""
            }
        },
    },
}

export const pythonNode_initData = {
    "id": "pythonnode",
    "name": i18n.t('workFlow.code'),
    "type": "PythonNode",
    "shape": "dag-node",
    "x": 40,
    "y": 40,
    "icon": require('../components/img/code.png'),
    ports:[{
        id: 'pythonnode-left',
        group: 'left',
    },
    {
        id: 'pythonnode-right',
        group: 'right',
    }],
    "data":{
        "id": "pythonnode",
        "name": i18n.t('workFlow.code'),
        "type": "PythonNode",
        "shape": "dag-node",
        "x": 40,
        "y": 40,
        "icon": require('../components/img/code.png'),
        "data": {
            "inputs": [

            ],
            "outputs": [

            ],
            "settings": {
                "code":"IyDlrprkuYnkuIDkuKogbWFpbiDlh73mlbDvvIznlKjmiLflj6rog73lnKhtYWlu5Ye95pWw6YeM5YGa5Luj56CB5byA5Y+R44CCDQojIOWFtuS4re+8jOWbuuWumuS8oOWFpSBwYXJhbXMg5Y+C5pWw77yI5a2X5YW45qC85byP77yJ77yM5a6D5YyF5ZCr5LqG6IqC54K56YWN572u55qE5omA5pyJ6L6T5YWl5Y+Y6YeP44CCDQojIOWFtuS4re+8jOWbuuWumui/lOWbniBvdXRwdXRfcGFyYW1zIOWPguaVsO+8iOWtl+WFuOagvOW8j++8ie+8jOWug+WMheWQq+S6huiKgueCuemFjee9rueahOaJgOaciei+k+WHuuWPmOmHj+OAgg0KIyDov5DooYznjq/looMgUHl0aG9uMy4NCg0KIyBtYWluIOWHveaVsO+8jOWbuuWumuS8oOWFpSBwYXJhbXMg5Y+C5pWwDQpkZWYgbWFpbihwYXJhbXMpOg0KICAgICMg55So5oi36Ieq5a6a5LmJ6YOo5YiGLi4uLi4uDQoNCiAgICAjIOWbuuWumui/lOWbniBvdXRwdXRfcGFyYW1zIOWPguaVsA0KICAgIG91dHB1dF9wYXJhbXMgPSB7DQogICAgICAgIyDnlKjmiLfoh6rlrprkuYnpg6jliIYuLi4uLi4NCiAgICB9DQogICAgcmV0dXJuIG91dHB1dF9wYXJhbXMNCg==",
                "language": "Python"
            }
        }
    }


}

export const LLMNode_initData =  {
    "id": "llmnode",
    "type": "LLMNode",
    "name": i18n.t('workFlow.modelNode'),
    "shape": "dag-node",
    "x": 40,
    "y": 40,
    "icon": require('../components/img/model.png'),
    ports:[{
        id: 'llmnode-left',
        group: 'left',
    },
        {
            id: 'llmnode-right',
            group: 'right',
        }],
    "data": {
        "id": "llmnode",
        "type": "LLMNode",
        "name":i18n.t('workFlow.modelNode'),
        "shape": "dag-node",
        "x": 40,
        "y": 40,
        "icon": require('../components/img/model.png'),
        "data":{
            "inputs": [
                {
                    "name": "",
                    "desc": "",
                    "type": "string",
                    "list_schema": null,
                    "object_schema": null,
                    "value": {
                        "content": "",
                        "type": "generated"
                    },
                    "extra": {
                        "location": "body"
                    }
                }
            ],
            "outputs": [
                // 注意，输出固定只有一个content字段，数组长度固定是1
                {
                    "name": "content",
                    "desc": i18n.t('workFlow.modelResult'),
                    "type": "string",
                    "list_schema": null,
                    "object_schema": null,
                    "value": {
                        "content": "",
                        "type": "generated"
                    }
                }
            ],
            "settings": {
                "model": "",
                "headers": {},
                "content_type": "application/json"
            },
            //多样性 前端用
            "modelForm":{
                "input":'',
                "temperature":0.5,
                "top_p":0.5,
                "presence_penalty":1,
                "model":""
            }
        }
    }
}

export const LLMStreamingNode_initData =  {
    "id": "llmstreamingnode",
    "type": "LLMStreamingNode",
    "name": i18n.t('workFlow.modelNodeStream'),
    "shape": "dag-node",
    "x": 40,
    "y": 40,
    "icon": require('../components/img/model.png'),
    ports:[{
        id: 'llmstreamingnode-left',
        group: 'left',
    },
        {
            id: 'llmstreamingnode-right',
            group: 'right',
        }],
    "data": {
        "id": "llmstreamingnode",
        "type": "LLMStreamingNode",
        "name": i18n.t('workFlow.modelNodeStream'),
        "shape": "dag-node",
        "x": 40,
        "y": 40,
        "icon": require('../components/img/model.png'),
        "data":{
            "inputs": [
                {
                    "name": "",
                    "desc": "",
                    "type": "string",
                    "list_schema": null,
                    "object_schema": null,
                    "value": {
                        "content": "",
                        "type": "generated"
                    },
                    "extra": {
                        "location": "body"
                    }
                }
            ],
            "outputs": [
                // 注意，输出固定只有一个content字段，数组长度固定是1
                {
                    "name": "content",
                    "desc": i18n.t('workFlow.modelResult'),
                    "type": "string",
                    "list_schema": null,
                    "object_schema": null,
                    "value": {
                        "content": "",
                        "type": "generated"
                    }
                }
            ],
            "settings": {
                "model": "",
                "headers": {},
                "content_type": "application/json"
            },
            //多样性 前端用
            "modelForm":{
                "input":'',
                "temperature":0.5,
                "top_p":0.5,
                "presence_penalty":1,
                "model":""
            }
        }
    }
}

export const SwitchNode_initData = {
    "id": "switchnode",
    "type": "SwitchNode",
    "name": i18n.t('workFlow.splitter'),
    "shape": "dag-node",
    "x": 40,
    "y": 40,
    "icon": require('../components/img/switch.png'),
    ports:[{
        id: 'switchnode-left',
        group: 'left',
    }],
    "data": {
        "id": "switchnode",
        "type": "SwitchNode",
        "name": i18n.t('workFlow.splitter'),
        "shape": "dag-node",
        "x": 0,
        "y": 0,
        "icon": require('../components/img/switch.png'),
        "data":{
            "inputs": [
                {
                    "logic": "and",
                    "target_node_id": "",
                    "conditions": []
                },
                {
                    "logic": "and",
                    "target_node_id": "",
                    "conditions": []
                },
            ],
            "outputs": [],
            "settings": {},
        }
    }
}


export const ragNode_initData = {
    "id": "ragnode",
    "name": i18n.t('workFlow.knowLedge'),
    "type": "RAGNode",
    "shape": "dag-node",
    "x": 40,
    "y": 40,
    "icon": require('../components/img/rag.png'),
    ports:[{
        id: 'ragnode-left',
        group: 'left',
    },
        {
            id: 'ragnode-right',
            group: 'right',
        }],
    "data":{
        "id": "ragnode",
        "name": i18n.t('workFlow.knowLedge'),
        "type": "RAGNode",
        "shape": "dag-node",
        "x": 40,
        "y": 40,
        "icon": require('../components/img/rag.png'),
        "data": {
            "inputs": [
                {
                    "name": "query",
                    "desc": i18n.t('workFlow.userInout'),
                    "type": "string",
                    "list_schema": null,
                    "object_schema": null,
                    "value": {
                        "content": "",
                        "type": "generated"
                    },
                    "extra": {
                        "location": "body"
                    }
                },
                {
                    "name": "threshold",
                    "desc": i18n.t('workFlow.filterthreDesc'),
                    "type": "float",
                    "list_schema": null,
                    "object_schema": null,
                    "value": {
                        "content": 0.4,
                        "type": "generated"
                    },
                    "extra": {
                        "location": "body"
                    }
                },
                {
                    "name": "top_k",
                    "desc": i18n.t('workFlow.knowledgeNumDesc'),
                    "type": "integer",
                    "list_schema": null,
                    "object_schema": null,
                    "value": {
                        "content": 5,
                        "type": "generated"
                    },
                    "extra": {
                        "location": "body"
                    }
                }
            ],
            "outputs": [
                {
                    "name": "content",
                    "desc": i18n.t('workFlow.ragResult'),
                    "type": "string",
                    "list_schema": null,
                    "object_schema": null,
                    "value": {
                        "content": "",
                        "type": "generated"
                    }
                },
                {
                    "name": "prompt",
                    "desc": "prompt",
                    "type": "string",
                    "list_schema": null,
                    "object_schema": null,
                    "value": {
                        "content": "",
                        "type": "generated"
                    }
                }
            ],
            "settings": {
                "headers": {
                },
                // 知识库列表
                "knowledgeBase": [],
                // 当前用户ID
                "userId": JSON.parse(
                    localStorage.getItem("access_cert")
                ).user.userInfo.uid,
                "content_type": "application/json"
            }
        }
    }
}

export const guiNode_initData = {
    "id": "guinode",
    "name": i18n.t('workFlow.GUI'),
    "type": "GUIAgentNode",
    "shape": "dag-node",
    "x": 40,
    "y": 40,
    "icon": require('../components/img/gui.png'),
    ports:[{
        id: 'guinode-left',
        group: 'left',
    },
    {
        id: 'guinode-right',
        group: 'right',
    }],
    "data": {
        "id": "guinode",
        "name": i18n.t('workFlow.GUI'),
        "type": "GUIAgentNode",
        "shape": "dag-node",
        "x": 40,
        "y": 40,
        "icon": require('../components/img/gui.png'),
        "data": {
            "inputs": [
                // {
                //     "desc": "算法名称，默认gui_agent_v1",
                //     "list_schema": null,
                //     "name": "algo",
                //     "object_schema": null,
                //     "required": false,
                //     "type": "string",
                //     "value": {
                //         "content": '',
                //         "type": "generated"
                //     },
                //     "extra": {
                //             "location": "body"
                //         }
                // },
                {
                    "desc": i18n.t('workFlow.GUIDesc'),
                    "list_schema": null,
                    "name": "platform",
                    "object_schema": null,
                    "required": false,
                    "type": "string",
                    "value": {
                        "content": '',
                        "type": "generated"
                    },
                    "extra": {
                            "location": "body"
                        }
                },
                // {
                //     "desc": "屏幕布局导出的xml文件",
                //     "list_schema": null,
                //     "name": "current_screenshot_xml",
                //     "object_schema": null,
                //     "required": false,
                //     "type": "string",
                //     "value": {
                //         "content": {
                //             "ref_node_id": "",
                //             "ref_var_name": ""
                //         },
                //         "type": "generated"
                //     },
                        // "extra": {
                        //     "location": "body"
                        // }
                // },
                {
                    "desc": i18n.t('workFlow.GUIDesc1'),
                    "list_schema": null,
                    "name": "current_screenshot",
                    "object_schema": null,
                    "required": false,
                    // "type": "string(base64)",
                    "type": "string(base64)",
                    "value": {
                        "content": '',
                        "type": "generated"
                    },
                    "extra": {
                            "location": "body"
                        }
                },
                {
                    "desc": i18n.t('workFlow.GUIDesc2'),
                    "list_schema": null,
                    "name": "current_screenshot_width",
                    "object_schema": null,
                    "required": false,
                    "type": "Integer",
                    "value": {
                        "content": '',
                        "type": "generated"
                    },
                    "extra": {
                            "location": "body"
                        }
                },
                {
                    "desc": i18n.t('workFlow.GUIDesc3'),
                    "list_schema": null,
                    "name": "current_screenshot_height",
                    "object_schema": null,
                    "required": false,
                    "type": "Integer",
                    "value": {
                        "content": '',
                        "type": "generated"
                    },
                    "extra": {
                            "location": "body"
                        }
                },
                {
                    "desc": i18n.t('workFlow.currentTask'),
                    "list_schema": null,
                    "name": "task",
                    "object_schema": null,
                    "required": false,
                    "type": "string",
                    "value": {
                        "content": '',
                        "type": "generated"
                    },
                    "extra": {
                            "location": "body"
                        }
                },
                {
                    "desc": i18n.t('workFlow.currentTaskTip'),
                    "list_schema": {
                        "type": "string",
                        "object_schema": null,
                        "list_schema": null
                    },
                    "name": "history",
                    "object_schema": null,
                    "required": false,
                    "type": "array",
                    "value": {
                        "content": '',
                        "type": "generated"
                    },
                    "extra": {
                            "location": "body"
                        }
                }
            ],
            "outputs": [
                {
                    "desc": i18n.t('workFlow.status_code'),
                    "list_schema": null,
                    "name": "code",
                    "object_schema": null,
                    "required": false,
                    "type": "Integer",
                    "value": {
                        "content": '',
                        // "type": "ref"
                        "type": "generated"
                    }
                },
                {
                    "desc": i18n.t('workFlow.tipInfo'),
                    "list_schema": null,
                    "name": "message",
                    "object_schema": null,
                    "required": false,
                    "type": "string",
                    "value": {
                        "content": '',
                        "type": "generated"
                        // "type": "ref"
                    },
                },
                {
                    "desc": i18n.t('workFlow.answerText'),
                    "list_schema": null,
                    "name": "content",
                    "object_schema": null,
                    "required": false,
                    "type": "string",
                    "value": {
                        "content": '',
                        "type": "generated"
                        // "type": "ref"
                    }
                },
                {
                    "desc": i18n.t('workFlow.tokenNum'),
                    "list_schema": null,
                    "name": "usage",
                    "object_schema": null,
                    "required": false,
                    "type": "string",
                    "value": {
                        "content": '',
                        "type": "generated"
                        // "type": "ref"
                    }
                },
            ],
            "settings": {
                "content_type": "application/json",
                "headers": {
                    "Authorization": "Bearer " + vuex.user.token
                },
            }
        },
    },
}

export const filegenerate_initData = {
    "id": "filegeneratenode",
    "type": "FileGenerateNode",
    "name": "API:URL转文件内容",
    "shape": "dag-node",
    "x": 40,
    "y": 40,
    "icon": require('../components/img/filegenerate.png'),
    ports:[{
        id: 'FileGenerateNode-left',
        group: 'left',
    },
        {
            id: 'FileGenerateNode-right',
            group: 'right',
        }],
    "data": {
        "id": "filegeneratenode",
        "type": "FileGenerateNode",
        "name": "API:URL转文件内容",
        "shape": "dag-node",
        "x": 40,
        "y": 40,
        "icon": require('../components/img/filegenerate.png'),
        "data":{
            "inputs": [
                    {
                        "name": "title",
                        "desc": "生成文件的标题",
                        "type": "string",
                        "list_schema": null,
                        "object_schema": null,
                        "value": {
                            "content": "",
                            "type": "generated"
                        },
                        "extra": {
                            "location": "body"
                        }
                    },
                    {
                        "name": "text",
                        "desc": "Markdown格式的文档内容",
                        "type": "string",
                        "list_schema": null,
                        "object_schema": null,
                        "value": {
                            "content": "",
                            "type": "generated"
                        },
                        "extra": {
                            "location": "body"
                        }
                    },
                    {
                        "name": "format",
                        "desc": "请选择目标格式",
                        "type": "string",
                        "list_schema": null,
                        "object_schema": null,
                        "value": {
                            "content": '',
                            "type": "generated"
                        },
                        "extra": {
                            "location": "body"
                        }
                    }
                ],
            "outputs": [
                // 注意，输出固定只有一个content字段，数组长度固定是1
                {
                    "name": "file_url",
                    "desc": "文档链接",
                    "type": "string",
                    "list_schema": null,
                    "object_schema": null,
                    "value": {
                        "content": null,
                        "type": "generated"
                    }
                }
            ],
            "settings": {
                "headers": {},
            },
        }
    }
}

export const fileparse_initData = {
    "id": "fileparsenode",
    "type": "FileParseNode",
    "name": "API:URL转文件内容",
    "shape": "dag-node",
    "x": 40,
    "y": 40,
    "icon": require('../components/img/fileparse.png'),
    ports:[{
        id: 'FileParseNode-left',
        group: 'left',
    },
        {
            id: 'FileParseNode-right',
            group: 'right',
        }],
    "data": {
        "id": "fileparsenode",
        "type": "FileParseNode",
        "name": "API:文件内容转URL",
        "shape": "dag-node",
        "x": 40,
        "y": 40,
        "icon": require('../components/img/fileparse.png'),
        "data":{
            "inputs": [
                    {
                        "name": "file_url",
                        "desc": "文件链接",
                        "type": "string",
                        "list_schema": null,
                        "object_schema": null,
                        "value": {
                            "content": "",
                            "type": "generated"
                        },
                        "extra": {
                            "location": "body"
                        }
                    }
                ],
            "outputs": [
                // 注意，输出固定只有一个content字段，数组长度固定是1
                {
                    "name": "text",
                    "desc": "请求返回",
                    "type": "string",
                    "list_schema": null,
                    "object_schema": null,
                    "value": {
                        "content": "",
                        "type": "generated"
                    }
                }
            ],
            "settings": {
                "headers": {},
            },
        }
    }
}

export const mcp_initData = {
    "id": "mcpnode",
    "type": "MCPClientNode",
    "name": "MCP",
    "shape": "dag-node",
    "x": 40,
    "y": 40,
    "icon": require('../components/img/MCP.png'),
    ports:[{
        id: 'MCPClientNode-left',
        group: 'left',
    },
        {
            id: 'MCPClientNode-right',
            group: 'right',
        }],
    "data": {
        "id": "mcpnode",
        "type": "MCPClientNode",
        "name": "MCP",
        "shape": "dag-node",
        "x": 40,
        "y": 40,
        "icon": require('../components/img/MCP.png'),
        "data":{
            "inputs": [
                   
                ],
            "outputs": [
                // 注意，输出固定只有一个content字段，数组长度固定是1
                {
                    "name": "result",
                    "desc": "mcp tool返回的结果",
                    "type": "object",
                    "list_schema": null,
                    "object_schema": null,
                    "value": {
                        "content": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "..."
                                }
                            ],
                            "isError": false
                        },
                        "type": "generated"
                    }
                }
            ],
            "settings": {
                "headers": {},
                "mcp_server_url": "",
                "mcp_name": "",
                "mcp_desc": "",
                "content_type": "application/json"
            },
        }
    }
}

export const LLMNodeDescObj = {
    "input":"用户提示词输入",
    "temperature":"温度, 较高的数值会使输出更加随机，而较低的数值会使其更加集中和确定，建议该参数和多样性只设置1个",
    "top_p":"多样性, 影响输出文本的多样性，取值越大，生成文本的多样性越强，建议该参数和温度只设置1个",
    "presence_penalty":"重复惩罚, 用通过对已生成的token增加惩罚，减少重复生成的现象，值越大表示惩罚越大",
}

export const intention_initData = {
    "id": "IntentionNode",
    "type": "IntentionNode",
    "name": "意图识别",
    "shape": "dag-node",
    "x": 40,
    "y": 40,
    "icon": require('../components/img/IntentionNode.png'),
    ports:[{
        id: 'IntentionNode-left',
        group: 'left',
    }],
    "data": {
        "id": "IntentionNode",
        "type": "IntentionNode",
        "name": "意图识别",
        "shape": "dag-node",
        "x": 0,
        "y": 0,
        "icon": require('../components/img/IntentionNode.png'),
        "data":{
            "inputs": [
                {
                "name": "query",
                "type": "string",
                "desc": "",
                "required": true,
                "value": {
                    "content": "",
                    "type": "generated"
                },
                "object_schema": null,
                "list_schema": null
                }
            ],
            "outputs": [
                {
                    "name": "classification",
                    "type": "string",
                    "desc": "",
                    "object_schema": null,
                    "list_schema": null,
                    "required": false,
                    "value": {
                      "type": "generated",
                      "content": null
                    }
                  },
                  // 意图分支顺序，第X个意图
                  {
                    "name": "classificationID",
                    "type": "integer",
                    "desc": "",
                    "object_schema": null,
                    "list_schema": null,
                    "required": false,
                    "value": {
                      "type": "generated",
                      "content": null
                    },
                  }
            ],
            "settings": {
                "model":{
                    "model_name": "",
                    "reasoning_model": false, // 预留，前端不使用
                    "temperature": 0.064,
                    "top_p": 0.01,
                    "chat_history": false, // 预留，前端不使用
                    "system": "" // 附加提示词
                },
                "intentions":[
                    {
                        "name": "意图1",
                        "desc": "",
                        "global_selected": true, // 预留，前端不使用
                        "target_node_id": "",
                        "sentences": [],
                        "params": []
                    },
                    {
                        "name": "其他意图",
                        "desc": "",
                        "global_selected": true, // 预留，前端不使用
                        "target_node_id": "",
                        "sentences": [],
                        "params": []
                    },
                ],
                "lite_mode": false
            },
        }
    }
}


export const nodeDescConfig = {
    'StartNode':'工作流运行的起点。定义此工作流所需的输入参数。自定义的参数，会在工作流被应用调用时，由思考模型根据参数描述从用户输入的原始内容中抽取并传入。',
    'EndNode':'工作流的最终节点，输出工作流运行后的最终结果。',
    'EndStreamingNode': '工作流的最终节点，输出工作流运行后的最终结果。',
    'APINode':'配置外部 API 服务，并调用该服务。',
    'PythonNode':'编写代码，处理输入输出变量来生成返回值。',
    'LLMNode':'调用大语言模型，根据输入参数和提示词生成回复。',
    'SwitchNode':'连接多个下游分支节点，若设定条件成立则运行对应的条件分支，若均不成立则运行“否则”分支。',
    'RAGNode':'根据输入的参数，在选定的知识库中检索相关片段并召回，返回切片列表。',
    'GUIAgentNode':'通过视觉技术解析用户图形界面上的图像信息，并模拟人类操作行为来执行相应任务，与计算机系统进行交互的智能体。',
    'FileGenerateNode':'输入文本内容，可以生成docx、pdf、txt格式的文档。',
    'FileParseNode':'输入txt、pdf、docx、xlsx、csv、pptx等格式文档的URL，可以解析提取出文档的文本内容。',
    'MCPClientNode':'可快捷调用MCP工具',
    'IntentionNode':'识别用户的输入意图，并分配到不同分支执行',
}

export const switchLogicConfig = {
    'and':i18n.t('switchLogicConfig.and'),
    'or':i18n.t('switchLogicConfig.or')
}

export const switchOperatorConfig = {
    'eq':i18n.t('switchOperatorConfig.eq'),
    'not_eq':i18n.t('switchOperatorConfig.not_eq'),
    'len_ge':i18n.t('switchOperatorConfig.len_ge'),
    'len_gt':i18n.t('switchOperatorConfig.len_gt'),
    'len_le':i18n.t('switchOperatorConfig.len_le'),
    'len_lt':i18n.t('switchOperatorConfig.len_lt'),
    'empty':i18n.t('switchOperatorConfig.empty'),
    'not_empty':i18n.t('switchOperatorConfig.not_empty'),
    'in':i18n.t('switchOperatorConfig.in'),
    'not_in':i18n.t('switchOperatorConfig.not_in'),
}

export const switchOperatorList =
    [
        {value:'eq',label:i18n.t('switchOperatorConfig.eq')},
        {value:'not_eq',label:i18n.t('switchOperatorConfig.not_eq')},
        {value:'len_ge',label:i18n.t('switchOperatorConfig.len_ge')},
        {value:'len_gt',label:i18n.t('switchOperatorConfig.len_gt')},
        {value:'len_le',label:i18n.t('switchOperatorConfig.len_le')},
        {value:'len_lt',label:i18n.t('switchOperatorConfig.len_lt')},
        {value:'empty',label:i18n.t('switchOperatorConfig.empty')},
        {value:'not_empty',label:i18n.t('switchOperatorConfig.not_empty')},
        {value:'in',label:i18n.t('switchOperatorConfig.in')},
        {value:'not_in',label:i18n.t('switchOperatorConfig.not_in')},
    ]

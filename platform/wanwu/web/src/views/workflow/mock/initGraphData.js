export const initGraphData = {
    "edges": [],
    "nodes": [
        {
            "data": {
                "inputs": [],
                "outputs": [
                    {
                        "desc": "\u5174\u8da3\u70b9\u540d\u79f0\uff0c\u4f8b\u5982\u57ce\u5e02\u3001\u53bf\u57ce\u7b49",
                        "list_schema": null,
                        "name": "pois",
                        "object_schema": null,
                        "required": true,
                        "type": "string",
                        "value": {
                            "content": "",
                            "type": "generated"
                        }
                    },
                    {
                        "desc": "\u5174\u8da3\u70b9\u5468\u8fb9\u76f8\u5173\u7684\u5173\u952e\u8bcd\uff0c\u4f8b\u5982\u5496\u5561\u9986\u3001\u8425\u4e1a\u5385\u7b49",
                        "list_schema": null,
                        "name": "keywords",
                        "object_schema": null,
                        "required": true,
                        "type": "string",
                        "value": {
                            "content": "",
                            "type": "generated"
                        }
                    }
                ],
                "settings": {}
            },
            "id": "startnode",
            "name": "\u5f00\u59cb",
            "type": "StartNode",
            "shape": "dag-node",
        },
        {
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
                "outputs": [],
                "settings": {
                    "content": "",
                    "streaming": false,
                    "terminate_plan": "direct"
                }
            },
            "id": "endnode",
            "name": "\u7ed3\u675f",
            "type": "EndNode",
            "shape": "dag-node",
        },
    ]
}

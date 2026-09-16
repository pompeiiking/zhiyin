export const mockData = {
    "code": 0,
    "data": {
        "configDesc": "\u6d4b\u8bd5\u753b\u5e03\u6d4b\u8bd5\u753b\u5e03\u6d4b\u8bd5\u753b\u5e03",
        "configENName": "test",
        "configName": "\u6d4b\u8bd5\u753b\u5e03",
        "workflowSchema": {
            "edges": [
                {
                    "source_node_id": "startnode",
                    "target_node_id": "apinode"
                },
                {
                    "source_node_id": "apinode",
                    "target_node_id": "pythonnode"
                },
                {
                    "source_node_id": "pythonnode",
                    "target_node_id": "endnode"
                }
            ],
            "nodes": [
                {
                    "data": {
                        "inputs": [],
                        "outputs": [
                            {
                                "desc": "\u5174\u8da3\u70b9\u540d\u79f0\uff0c\u4f8b\u5982\u57ce\u5e02\u3001\u53bf\u57ce\u7b49",
                                "list_schema": null,
                                "name": "poi",
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
                    'node_status':'success',
                    'res_inputs':{},
                    "res-outputs": {
                        "keywords": "\u96cd\u548c\u5bab",
                        "pois": "\u5317\u4eac"
                    }
                },
                {
                    "data": {
                        "inputs": [
                            {
                                "desc": "",
                                "extra": {
                                    "location": "query"
                                },
                                "list_schema": null,
                                "name": "key",
                                "object_schema": null,
                                "required": false,
                                "type": "string",
                                "value": {
                                    "content": "77b5f0d102c848d443b791fd469b732d",
                                    "type": "generated"
                                }
                            },
                            {
                                "desc": "",
                                "extra": {
                                    "location": "query"
                                },
                                "list_schema": null,
                                "name": "keywords",
                                "object_schema": null,
                                "required": false,
                                "type": "string",
                                "value": {
                                    "content": {
                                        "ref_node_id": "startnode",
                                        "ref_var_name": "keywords"
                                    },
                                    "type": "ref"
                                }
                            },
                            {
                                "desc": "",
                                "extra": {
                                    "location": "query"
                                },
                                "list_schema": null,
                                "name": "pois",
                                "object_schema": null,
                                "required": false,
                                "type": "string",
                                "value": {
                                    "content": {
                                        "ref_node_id": "startnode",
                                        "ref_var_name": "poi"
                                    },
                                    "type": "ref"
                                }
                            }
                        ],
                        "outputs": [
                            {
                                "desc": "",
                                "list_schema": null,
                                "name": "pois",
                                "object_schema": null,
                                "required": false,
                                "type": "list",
                                "value": {
                                    "content": "",
                                    "type": "generated"
                                }
                            }
                        ],
                        "settings": {
                            "content_type": "application/json",
                            "headers": {},
                            "http_method": "GET",
                            "url": "https://restapi.amap.com/v5/place/text"
                        }
                    },
                    "id": "apinode",
                    "name": "API",
                    "type": "ApiNode",
                    "res_inputs": {
                        "key": "77b5f0d102c848d443b791fd469b732d",
                        "keywords": "\u96cd\u548c\u5bab",
                        "pois": "\u5317\u4eac"
                    },
                    "node_status": "success",
                    "res_outputs": {
                        "count": "10",
                        "info": "OK",
                        "infocode": "10000",
                        "pois": [
                            {
                                "adcode": "110101",
                                "address": "\u96cd\u548c\u5bab\u5927\u885728\u53f7(\u96cd\u548c\u5bab\u5730\u94c1\u7ad9F\u4e1c\u5357\u53e3\u6b65\u884c250\u7c73)",
                                "adname": "\u4e1c\u57ce\u533a",
                                "citycode": "010",
                                "cityname": "\u5317\u4eac\u5e02",
                                "distance": "",
                                "id": "B000A7BGMG",
                                "location": "116.417296,39.947239",
                                "name": "\u96cd\u548c\u5bab",
                                "parent": "",
                                "pcode": "110000",
                                "pname": "\u5317\u4eac\u5e02",
                                "type": "\u98ce\u666f\u540d\u80dc;\u98ce\u666f\u540d\u80dc;\u98ce\u666f\u540d\u80dc",
                                "typecode": "110200"
                            },
                            {
                                "adcode": "110101",
                                "address": "\u4e1c\u57ce\u533a",
                                "adname": "\u4e1c\u57ce\u533a",
                                "citycode": "010",
                                "cityname": "\u5317\u4eac\u5e02",
                                "distance": "",
                                "id": "B0KUNRUG3X",
                                "location": "116.417359,39.947978",
                                "name": "\u96cd\u548c\u5bab",
                                "parent": "",
                                "pcode": "110000",
                                "pname": "\u5317\u4eac\u5e02",
                                "type": "\u5730\u540d\u5730\u5740\u4fe1\u606f;\u70ed\u70b9\u5730\u540d;\u70ed\u70b9\u5730\u540d",
                                "typecode": "190700"
                            },
                            {
                                "adcode": "110101",
                                "address": "2\u53f7\u7ebf;5\u53f7\u7ebf",
                                "adname": "\u4e1c\u57ce\u533a",
                                "citycode": "010",
                                "cityname": "\u5317\u4eac\u5e02",
                                "distance": "",
                                "id": "BV10006563",
                                "location": "116.417537,39.949333",
                                "name": "\u96cd\u548c\u5bab(\u5730\u94c1\u7ad9)",
                                "parent": "",
                                "pcode": "110000",
                                "pname": "\u5317\u4eac\u5e02",
                                "type": "\u4ea4\u901a\u8bbe\u65bd\u670d\u52a1;\u5730\u94c1\u7ad9;\u5730\u94c1\u7ad9",
                                "typecode": "150500"
                            },
                            {
                                "adcode": "110101",
                                "address": "\u96cd\u548c\u5bab\u5927\u885728\u53f7\u96cd\u548c\u5bab(\u96cd\u548c\u5bab\u5730\u94c1\u7ad9F\u4e1c\u5357\u53e3\u6b65\u884c310\u7c73)",
                                "adname": "\u4e1c\u57ce\u533a",
                                "citycode": "010",
                                "cityname": "\u5317\u4eac\u5e02",
                                "distance": "",
                                "id": "B000A9PHUD",
                                "location": "116.417536,39.945388",
                                "name": "\u96cd\u548c\u5bab\u552e\u7968\u5904",
                                "parent": "B000A7BGMG",
                                "pcode": "110000",
                                "pname": "\u5317\u4eac\u5e02",
                                "type": "\u751f\u6d3b\u670d\u52a1;\u552e\u7968\u5904;\u516c\u56ed\u666f\u70b9\u552e\u7968\u5904",
                                "typecode": "070306"
                            },
                            {
                                "adcode": "110101",
                                "address": "\u4e1c\u57ce\u533a",
                                "adname": "\u4e1c\u57ce\u533a",
                                "citycode": "010",
                                "cityname": "\u5317\u4eac\u5e02",
                                "distance": "",
                                "id": "BZDCPW028K",
                                "location": "116.417717,39.945057",
                                "name": "\u96cd\u548c\u5bab\u5927\u8857",
                                "parent": "",
                                "pcode": "110000",
                                "pname": "\u5317\u4eac\u5e02",
                                "type": "\u5730\u540d\u5730\u5740\u4fe1\u606f;\u4ea4\u901a\u5730\u540d;\u9053\u8def\u540d",
                                "typecode": "190301"
                            },
                            {
                                "adcode": "110101",
                                "address": "\u96cd\u548c\u5bab\u5927\u885728\u53f7\u96cd\u548c\u5bab(\u96cd\u548c\u5bab\u5730\u94c1\u7ad9F\u4e1c\u5357\u53e3\u6b65\u884c490\u7c73)",
                                "adname": "\u4e1c\u57ce\u533a",
                                "citycode": "010",
                                "cityname": "\u5317\u4eac\u5e02",
                                "distance": "",
                                "id": "B0FFHGBBCL",
                                "location": "116.417302,39.947282",
                                "name": "\u96cd\u548c\u5bab\u96cd\u548c\u95e8",
                                "parent": "B000A7BGMG",
                                "pcode": "110000",
                                "pname": "\u5317\u4eac\u5e02",
                                "type": "\u98ce\u666f\u540d\u80dc;\u98ce\u666f\u540d\u80dc\u76f8\u5173;\u65c5\u6e38\u666f\u70b9",
                                "typecode": "110000"
                            },
                            {
                                "adcode": "110101",
                                "address": "\u4e1c\u57ce\u533a",
                                "adname": "\u4e1c\u57ce\u533a",
                                "citycode": "010",
                                "cityname": "\u5317\u4eac\u5e02",
                                "distance": "",
                                "id": "B0FFFAABIN",
                                "location": "116.413362,39.949171",
                                "name": "\u96cd\u548c\u5bab\u6865",
                                "parent": "",
                                "pcode": "110000",
                                "pname": "\u5317\u4eac\u5e02",
                                "type": "\u5730\u540d\u5730\u5740\u4fe1\u606f;\u4ea4\u901a\u5730\u540d;\u7acb\u4ea4\u6865",
                                "typecode": "190306"
                            },
                            {
                                "adcode": "110101",
                                "address": "\u96cd\u548c\u5bab\u5927\u885728\u53f7(\u96cd\u548c\u5bab\u5730\u94c1\u7ad9F\u4e1c\u5357\u53e3\u6b65\u884c300\u7c73)",
                                "adname": "\u4e1c\u57ce\u533a",
                                "citycode": "010",
                                "cityname": "\u5317\u4eac\u5e02",
                                "distance": "",
                                "id": "B0FFG6Q1IR",
                                "location": "116.417207,39.945516",
                                "name": "\u96cd\u548c\u5bab-\u724c\u697c",
                                "parent": "B000A7BGMG",
                                "pcode": "110000",
                                "pname": "\u5317\u4eac\u5e02",
                                "type": "\u98ce\u666f\u540d\u80dc;\u98ce\u666f\u540d\u80dc\u76f8\u5173;\u65c5\u6e38\u666f\u70b9",
                                "typecode": "110000"
                            },
                            {
                                "adcode": "110101",
                                "address": "\u96cd\u548c\u5bab\u5927\u885728\u53f7\u96cd\u548c\u5bab\u5185(\u96cd\u548c\u5bab\u5730\u94c1\u7ad9F\u4e1c\u5357\u53e3\u6b65\u884c460\u7c73)",
                                "adname": "\u4e1c\u57ce\u533a",
                                "citycode": "010",
                                "cityname": "\u5317\u4eac\u5e02",
                                "distance": "",
                                "id": "B0FFHW1TDM",
                                "location": "116.416944,39.946840",
                                "name": "\u96cd\u548c\u5bab-\u9f13\u697c",
                                "parent": "B000A7BGMG",
                                "pcode": "110000",
                                "pname": "\u5317\u4eac\u5e02",
                                "type": "\u98ce\u666f\u540d\u80dc;\u98ce\u666f\u540d\u80dc\u76f8\u5173;\u65c5\u6e38\u666f\u70b9",
                                "typecode": "110000"
                            },
                            {
                                "adcode": "110101",
                                "address": "\u96cd\u548c\u5bab\u5927\u885728\u53f7\u96cd\u548c\u5bab\u666f\u533a\u5185",
                                "adname": "\u4e1c\u57ce\u533a",
                                "citycode": "010",
                                "cityname": "\u5317\u4eac\u5e02",
                                "distance": "",
                                "id": "B0FFJ2TBJ8",
                                "location": "116.417555,39.947398",
                                "name": "\u96cd\u548c\u5bab\u6e38\u5ba2\u670d\u52a1\u4e2d\u5fc3",
                                "parent": "B000A7BGMG",
                                "pcode": "110000",
                                "pname": "\u5317\u4eac\u5e02",
                                "type": "\u751f\u6d3b\u670d\u52a1;\u4fe1\u606f\u54a8\u8be2\u4e2d\u5fc3;\u670d\u52a1\u4e2d\u5fc3",
                                "typecode": "070201"
                            }
                        ],
                        "status": "1"
                    }
                },
                {
                    "data": {
                        "inputs": [
                            {
                                "desc": "",
                                "list_schema": null,
                                "name": "pois",
                                "object_schema": null,
                                "required": true,
                                "type": "list",
                                "value": {
                                    "content": {
                                        "ref_node_id": "apinode",
                                        "ref_var_name": "pois"
                                    },
                                    "type": "ref"
                                }
                            }
                        ],
                        "outputs": [
                            {
                                "desc": "",
                                "list_schema": null,
                                "name": "key0",
                                "object_schema": null,
                                "required": false,
                                "type": "string",
                                "value": {
                                    "content": "",
                                    "type": "generated"
                                }
                            }
                        ],
                        "settings": {
                            "code": "IyDlrprkuYnkuIDkuKogbWFpbiDlh73mlbDvvIzkvKDlhaUgcGFyYW1zIOWPguaVsOOAgnBhcmFtcyDkuK3ljIXlkKvkuoboioLngrnphY3nva7nmoTovpPlhaXlj5jph4/jgIIKIyDpnIDopoHlrprkuYnkuIDkuKrlrZflhbjkvZzkuLrovpPlh7rlj5jph48KIyDlvJXnlKjoioLngrnlrprkuYnnmoTlj5jph4/vvJpwYXJhbXNbJ+WPmOmHj+WQjSddCiMg6L+Q6KGM546v5aKDIFB5dGhvbjPvvJvpooTnva4gUGFja2FnZe+8mk51bVB5CgpkZWYgbWFpbihwYXJhbXMpOgoKICAgICMg5Yib5bu65LiA5Liq5a2X5YW45L2c5Li66L6T5Ye65Y+Y6YePCiAgICBvdXRwdXRfb2JqZWN0ID17CiAgICAKICAgICAgICAjIOW8leeUqOiKgueCueWumuS5ieeahCBjaXR5IOWPmOmHjwogICAgICAgICJrZXkwIjogcGFyYW1zWydwb2lzJ11bMF1bImFkZHJlc3MiXSwKCiAgICB9CiAgICByZXR1cm4gICBvdXRwdXRfb2JqZWN0",
                            "language": "Python"
                        }
                    },
                    "id": "pythonnode",
                    "name": "\u4ee3\u7801",
                    "type": "PythonNode",
                    "res_inputs": {
                        "params": {
                            "pois": [
                                {
                                    "adcode": "110101",
                                    "address": "\u96cd\u548c\u5bab\u5927\u885728\u53f7(\u96cd\u548c\u5bab\u5730\u94c1\u7ad9F\u4e1c\u5357\u53e3\u6b65\u884c250\u7c73)",
                                    "adname": "\u4e1c\u57ce\u533a",
                                    "citycode": "010",
                                    "cityname": "\u5317\u4eac\u5e02",
                                    "distance": "",
                                    "id": "B000A7BGMG",
                                    "location": "116.417296,39.947239",
                                    "name": "\u96cd\u548c\u5bab",
                                    "parent": "",
                                    "pcode": "110000",
                                    "pname": "\u5317\u4eac\u5e02",
                                    "type": "\u98ce\u666f\u540d\u80dc;\u98ce\u666f\u540d\u80dc;\u98ce\u666f\u540d\u80dc",
                                    "typecode": "110200"
                                },
                                {
                                    "adcode": "110101",
                                    "address": "\u4e1c\u57ce\u533a",
                                    "adname": "\u4e1c\u57ce\u533a",
                                    "citycode": "010",
                                    "cityname": "\u5317\u4eac\u5e02",
                                    "distance": "",
                                    "id": "B0KUNRUG3X",
                                    "location": "116.417359,39.947978",
                                    "name": "\u96cd\u548c\u5bab",
                                    "parent": "",
                                    "pcode": "110000",
                                    "pname": "\u5317\u4eac\u5e02",
                                    "type": "\u5730\u540d\u5730\u5740\u4fe1\u606f;\u70ed\u70b9\u5730\u540d;\u70ed\u70b9\u5730\u540d",
                                    "typecode": "190700"
                                },
                                {
                                    "adcode": "110101",
                                    "address": "2\u53f7\u7ebf;5\u53f7\u7ebf",
                                    "adname": "\u4e1c\u57ce\u533a",
                                    "citycode": "010",
                                    "cityname": "\u5317\u4eac\u5e02",
                                    "distance": "",
                                    "id": "BV10006563",
                                    "location": "116.417537,39.949333",
                                    "name": "\u96cd\u548c\u5bab(\u5730\u94c1\u7ad9)",
                                    "parent": "",
                                    "pcode": "110000",
                                    "pname": "\u5317\u4eac\u5e02",
                                    "type": "\u4ea4\u901a\u8bbe\u65bd\u670d\u52a1;\u5730\u94c1\u7ad9;\u5730\u94c1\u7ad9",
                                    "typecode": "150500"
                                },
                                {
                                    "adcode": "110101",
                                    "address": "\u96cd\u548c\u5bab\u5927\u885728\u53f7\u96cd\u548c\u5bab(\u96cd\u548c\u5bab\u5730\u94c1\u7ad9F\u4e1c\u5357\u53e3\u6b65\u884c310\u7c73)",
                                    "adname": "\u4e1c\u57ce\u533a",
                                    "citycode": "010",
                                    "cityname": "\u5317\u4eac\u5e02",
                                    "distance": "",
                                    "id": "B000A9PHUD",
                                    "location": "116.417536,39.945388",
                                    "name": "\u96cd\u548c\u5bab\u552e\u7968\u5904",
                                    "parent": "B000A7BGMG",
                                    "pcode": "110000",
                                    "pname": "\u5317\u4eac\u5e02",
                                    "type": "\u751f\u6d3b\u670d\u52a1;\u552e\u7968\u5904;\u516c\u56ed\u666f\u70b9\u552e\u7968\u5904",
                                    "typecode": "070306"
                                },
                                {
                                    "adcode": "110101",
                                    "address": "\u4e1c\u57ce\u533a",
                                    "adname": "\u4e1c\u57ce\u533a",
                                    "citycode": "010",
                                    "cityname": "\u5317\u4eac\u5e02",
                                    "distance": "",
                                    "id": "BZDCPW028K",
                                    "location": "116.417717,39.945057",
                                    "name": "\u96cd\u548c\u5bab\u5927\u8857",
                                    "parent": "",
                                    "pcode": "110000",
                                    "pname": "\u5317\u4eac\u5e02",
                                    "type": "\u5730\u540d\u5730\u5740\u4fe1\u606f;\u4ea4\u901a\u5730\u540d;\u9053\u8def\u540d",
                                    "typecode": "190301"
                                },
                                {
                                    "adcode": "110101",
                                    "address": "\u96cd\u548c\u5bab\u5927\u885728\u53f7\u96cd\u548c\u5bab(\u96cd\u548c\u5bab\u5730\u94c1\u7ad9F\u4e1c\u5357\u53e3\u6b65\u884c490\u7c73)",
                                    "adname": "\u4e1c\u57ce\u533a",
                                    "citycode": "010",
                                    "cityname": "\u5317\u4eac\u5e02",
                                    "distance": "",
                                    "id": "B0FFHGBBCL",
                                    "location": "116.417302,39.947282",
                                    "name": "\u96cd\u548c\u5bab\u96cd\u548c\u95e8",
                                    "parent": "B000A7BGMG",
                                    "pcode": "110000",
                                    "pname": "\u5317\u4eac\u5e02",
                                    "type": "\u98ce\u666f\u540d\u80dc;\u98ce\u666f\u540d\u80dc\u76f8\u5173;\u65c5\u6e38\u666f\u70b9",
                                    "typecode": "110000"
                                },
                                {
                                    "adcode": "110101",
                                    "address": "\u4e1c\u57ce\u533a",
                                    "adname": "\u4e1c\u57ce\u533a",
                                    "citycode": "010",
                                    "cityname": "\u5317\u4eac\u5e02",
                                    "distance": "",
                                    "id": "B0FFFAABIN",
                                    "location": "116.413362,39.949171",
                                    "name": "\u96cd\u548c\u5bab\u6865",
                                    "parent": "",
                                    "pcode": "110000",
                                    "pname": "\u5317\u4eac\u5e02",
                                    "type": "\u5730\u540d\u5730\u5740\u4fe1\u606f;\u4ea4\u901a\u5730\u540d;\u7acb\u4ea4\u6865",
                                    "typecode": "190306"
                                },
                                {
                                    "adcode": "110101",
                                    "address": "\u96cd\u548c\u5bab\u5927\u885728\u53f7(\u96cd\u548c\u5bab\u5730\u94c1\u7ad9F\u4e1c\u5357\u53e3\u6b65\u884c300\u7c73)",
                                    "adname": "\u4e1c\u57ce\u533a",
                                    "citycode": "010",
                                    "cityname": "\u5317\u4eac\u5e02",
                                    "distance": "",
                                    "id": "B0FFG6Q1IR",
                                    "location": "116.417207,39.945516",
                                    "name": "\u96cd\u548c\u5bab-\u724c\u697c",
                                    "parent": "B000A7BGMG",
                                    "pcode": "110000",
                                    "pname": "\u5317\u4eac\u5e02",
                                    "type": "\u98ce\u666f\u540d\u80dc;\u98ce\u666f\u540d\u80dc\u76f8\u5173;\u65c5\u6e38\u666f\u70b9",
                                    "typecode": "110000"
                                },
                                {
                                    "adcode": "110101",
                                    "address": "\u96cd\u548c\u5bab\u5927\u885728\u53f7\u96cd\u548c\u5bab\u5185(\u96cd\u548c\u5bab\u5730\u94c1\u7ad9F\u4e1c\u5357\u53e3\u6b65\u884c460\u7c73)",
                                    "adname": "\u4e1c\u57ce\u533a",
                                    "citycode": "010",
                                    "cityname": "\u5317\u4eac\u5e02",
                                    "distance": "",
                                    "id": "B0FFHW1TDM",
                                    "location": "116.416944,39.946840",
                                    "name": "\u96cd\u548c\u5bab-\u9f13\u697c",
                                    "parent": "B000A7BGMG",
                                    "pcode": "110000",
                                    "pname": "\u5317\u4eac\u5e02",
                                    "type": "\u98ce\u666f\u540d\u80dc;\u98ce\u666f\u540d\u80dc\u76f8\u5173;\u65c5\u6e38\u666f\u70b9",
                                    "typecode": "110000"
                                },
                                {
                                    "adcode": "110101",
                                    "address": "\u96cd\u548c\u5bab\u5927\u885728\u53f7\u96cd\u548c\u5bab\u666f\u533a\u5185",
                                    "adname": "\u4e1c\u57ce\u533a",
                                    "citycode": "010",
                                    "cityname": "\u5317\u4eac\u5e02",
                                    "distance": "",
                                    "id": "B0FFJ2TBJ8",
                                    "location": "116.417555,39.947398",
                                    "name": "\u96cd\u548c\u5bab\u6e38\u5ba2\u670d\u52a1\u4e2d\u5fc3",
                                    "parent": "B000A7BGMG",
                                    "pcode": "110000",
                                    "pname": "\u5317\u4eac\u5e02",
                                    "type": "\u751f\u6d3b\u670d\u52a1;\u4fe1\u606f\u54a8\u8be2\u4e2d\u5fc3;\u670d\u52a1\u4e2d\u5fc3",
                                    "typecode": "070201"
                                }
                            ]
                        }
                    },
                    "node_status": "success",
                    "res_outputs": {
                        "key0": "\u96cd\u548c\u5bab\u5927\u885728\u53f7(\u96cd\u548c\u5bab\u5730\u94c1\u7ad9F\u4e1c\u5357\u53e3\u6b65\u884c250\u7c73)",
                        "key1": "116.417296,39.947239"
                    }
                },
                {
                    "data": {
                        "inputs": [
                            {
                                "desc": "",
                                "list_schema": null,
                                "name": "key0",
                                "object_schema": null,
                                "required": false,
                                "type": "string",
                                "value": {
                                    "content": {
                                        "ref_node_id": "pythonnode",
                                        "ref_var_name": "key0"
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
                    "res_inputs": {
                        "key0": "\u96cd\u548c\u5bab\u5927\u885728\u53f7(\u96cd\u548c\u5bab\u5730\u94c1\u7ad9F\u4e1c\u5357\u53e3\u6b65\u884c250\u7c73)",
                        "key1": "116.417296,39.947239"
                    },
                    "node_status": "success",
                    "res_outputs": {}
                },
            ]
        }
    },
    "msg": ""
}

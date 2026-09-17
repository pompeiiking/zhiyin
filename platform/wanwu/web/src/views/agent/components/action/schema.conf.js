export const schemaConfig = {
    json:
        '{\n' +
        '            "openapi": "3.0.0",\n' +
        '            "info":\n' +
        '                {\n' +
        '                    "title": "心知天气API",\n' +
        '                    "version": "1.0.0",\n' +
        '                    "description": "提供当前天气信息的API，包括温度、天气状况等。"\n' +
        '                },\n' +
        '            "servers":\n' +
        '                [\n' +
        '                    {"url": "https://api.seniverse.com/v3"}\n' +
        '                ],\n' +
        '            "paths":\n' +
        '                {\n' +
        '                    "/weather/now.json": {\n' +
        '                        "get": {\n' +
        '                            "summary": "天气查询工具",\n' +
        '                            "operationId": "getWeatherNow",\n' +
        '                            "description": "根据地点获取当前的天气情况，包括温度和天气状况描述。",\n' +
        '                            "parameters": [{\n' +
        '                                "name": "location",\n' +
        '                                "description": "查询的地点，可以是城市名、邮编等。",\n' +
        '                                "in": "query",\n' +
        '                                "required": true,\n' +
        '                                "schema": {"type": "string"}\n' +
        '                            }],\n' +
        '                            "responses": {\n' +
        '                                "200": {\n' +
        '                                    "description": "成功获取天气信息",\n' +
        '                                    "content": {\n' +
        '                                        "application/json": {\n' +
        '                                            "schema": {\n' +
        '                                                "type": "object",\n' +
        '                                                "properties": {\n' +
        '                                                    "location": {"type": "string"},\n' +
        '                                                    "text": {"type": "string"},\n' +
        '                                                    "code": {"type": "string"},\n' +
        '                                                    "temperature": {"type": "string"}\n' +
        '                                                }\n' +
        '                                            }\n' +
        '                                        }\n' +
        '                                    }\n' +
        '                                },\n' +
        '                                "default": {\n' +
        '                                    "description": "请求失败时的错误信息",\n' +
        '                                    "content": {\n' +
        '                                        "application/json": {\n' +
        '                                            "schema": {\n' +
        '                                                "type": "object",\n' +
        '                                                "properties": {"error": {"type": "string"}}\n' +
        '                                            }\n' +
        '                                        }\n' +
        '                                    }\n' +
        '                                }\n' +
        '                            }\n' +
        '                        }\n' +
        '                    }\n' +
        '                }\n' +
        '        }',
    yaml:'openapi: 3.0.0\n' +
        'info:\n' +
        '  title: 心知天气API\n' +
        '  version: 1.0.0\n' +
        '  description: 提供当前天气信息的API，包括温度、天气状况等。\n' +
        'servers:\n' +
        '  - url: https://api.seniverse.com/v3\n' +
        'paths:\n' +
        '  /weather/now.json:\n' +
        '    get:\n' +
        '      summary: 天气查询工具\n' +
        '      operationId: getWeatherNow\n' +
        '      description: 根据地点获取当前的天气情况，包括温度和天气状况描述。\n' +
        '      parameters:\n' +
        '        - name: location\n' +
        '          description: 查询的地点，可以是城市名、邮编等。\n' +
        '          in: query\n' +
        '          required: true\n' +
        '          schema:\n' +
        '            type: string\n' +
        '      responses:\n' +
        '        \'200\':\n' +
        '          description: 成功获取天气信息\n' +
        '          content:\n' +
        '            application/json:\n' +
        '              schema:\n' +
        '                type: object\n' +
        '                properties:\n' +
        '                  location:\n' +
        '                    type: string\n' +
        '                  text:\n' +
        '                    type: string\n' +
        '                  code:\n' +
        '                    type: string\n' +
        '                  temperature:\n' +
        '                    type: string\n' +
        '        default:\n' +
        '          description: 请求失败时的错误信息\n' +
        '          content:\n' +
        '            application/json:\n' +
        '              schema:\n' +
        '                type: object\n' +
        '                properties:\n' +
        '                  error:\n' +
        '                    type: string'


}

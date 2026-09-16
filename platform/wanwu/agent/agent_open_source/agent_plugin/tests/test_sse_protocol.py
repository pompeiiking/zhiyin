import ast
import json
from pathlib import Path
import unittest

from agent_plugin.sse_protocol import (
    consume_action_event,
    empty_action_output_event,
    make_action_event,
    parse_action_event,
)


class ActionSSEProtocolTest(unittest.TestCase):
    def test_success_event_is_framed_and_parseable(self):
        raw = make_action_event("首片", "model-a")
        self.assertTrue(raw.startswith("data:"))
        self.assertTrue(raw.endswith("\n\n"))
        event = parse_action_event(raw.strip())
        self.assertEqual(event["data"]["choices"][0]["message"]["content"], "首片")

    def test_error_event_is_terminal_and_structurally_complete(self):
        raw = make_action_event("", "model-a", code=1, message="模型失败", finish_reason="stop")
        event = parse_action_event(raw.strip())
        self.assertEqual(event["code"], 1)
        self.assertEqual(event["msg"], "模型失败")
        self.assertEqual(event["data"]["choices"][0]["finish_reason"], "stop")
        self.assertEqual(event["data"]["usage"]["total_tokens"], 0)

    def test_empty_line_is_ignored_and_bad_json_fails(self):
        self.assertIsNone(parse_action_event(""))
        with self.assertRaises(ValueError):
            parse_action_event("data:{bad")

    def test_action_infer_does_not_pre_read_single_event(self):
        source = Path(__file__).parents[1].joinpath("http_action_server.py").read_text(encoding="utf-8")
        action_infer = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "action_infer")
        action_infer.decorator_list = []

        class Request:
            def get_json(self):
                return {"input": "q", "model_name": "model", "plugin_list": [],
                        "function_calls_list": [], "action_type": "action", "history": []}

        class Response:
            def __init__(self, response, content_type):
                self.response = response
                self.content_type = content_type

        events = iter(["data:one\n\n"])
        namespace = {
            "json": json, "request": Request(), "Response": Response, "stream_with_context": lambda stream: stream,
            "plugin_config": lambda *args: events, "API_KEY": "key", "MODEL_NAME": "model",
            "logger": type("Logger", (), {"info": lambda *args: None})(),
        }
        exec(compile(ast.Module(body=[action_infer], type_ignores=[]), "http_action_server.py", "exec"), namespace)
        response = namespace["action_infer"]()
        self.assertEqual(next(response.response), "data:one\n\n")

    def test_empty_action_output_is_a_terminal_error_event(self):
        event = parse_action_event(empty_action_output_event("model-a").strip())
        self.assertEqual(event["code"], 1)
        self.assertEqual(event["data"]["choices"][0]["finish_reason"], "stop")

    def test_action_consumer_turns_invalid_and_error_events_into_terminal_errors(self):
        def error_event(message):
            return {"code": 1, "message": message or "Action 执行失败", "finish": 1}

        cases = [
            "event:result",
            "data:{bad",
            'data:{"code": 0, "data": {"choices": [], "usage": {}}}',
            make_action_event("", "model-a", code=1, message="模型失败", finish_reason="stop").strip(),
        ]
        for line in cases:
            result, terminal = consume_action_event(line, {}, error_event)
            self.assertTrue(terminal)
            self.assertEqual(result["code"], 1)
            self.assertEqual(result["finish"], 1)

    def test_plugin_config_empty_output_uses_terminal_event_production_branch(self):
        source = Path(__file__).parents[1].joinpath("http_action_server.py").read_text(encoding="utf-8")
        plugin_config = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "plugin_config")

        class ReActChat:
            def __init__(self, **kwargs):
                pass

            def run(self, messages):
                return iter([[json.dumps({"action_code": 99})]])

        logger = type("Logger", (), {"info": lambda *args: None, "exception": lambda *args: None})()
        emitted_models = []

        def terminal_event(model, usage):
            emitted_models.append(model)
            return empty_action_output_event(model, usage)

        namespace = {
            "json": json, "ReActChat": ReActChat, "get_chat_model": lambda config: object(),
            "openapi_schema_convert": lambda *args: None, "add_openapi_plugin_to_additional_tool": lambda *args: [],
            "logger": logger, "make_action_event": make_action_event,
            "empty_action_output_event": terminal_event,
        }
        exec(compile(ast.Module(body=[plugin_config], type_ignores=[]), "http_action_server.py", "exec"), namespace)
        events = list(namespace["plugin_config"]("key", "q", [], [], "action", [], "model-a", ""))
        self.assertEqual(emitted_models, ["model-a"])
        self.assertEqual(len(events), 1)
        event = parse_action_event(events[0].strip())
        self.assertEqual(event["code"], 1)
        self.assertEqual(event["data"]["choices"][0]["finish_reason"], "stop")

    def test_server_action_loop_turns_bad_events_terminal_and_stops_processing(self):
        source = Path(__file__).parents[2].joinpath("server_open.py").read_text(encoding="utf-8")
        agent_start = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "agent_start")
        agent_start.decorator_list = []

        class Request:
            headers = {"X-Uid": "user"}

            def get_json(self):
                return {"input": "q", "model": "model-a", "model_url": "", "plugin_list": [{}]}

        class Response:
            def __init__(self, response, mimetype):
                self.response = response
                self.mimetype = mimetype

        class HTTPResponse:
            def __init__(self, lines):
                self.lines = lines

            def __bool__(self):
                return True

            def iter_lines(self, decode_unicode=True):
                return iter(self.lines)

        def agent_error_event(message):
            return {
                "code": 1, "message": message or "Action 执行失败", "response": "", "finish": 1,
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "search_list": [], "gen_file_url_list": [],
            }

        class Requests:
            def __init__(self, lines):
                self.lines = lines

            def post(self, *args, **kwargs):
                return HTTPResponse(self.lines)

        cases = [
            "event:result",
            "data:{bad",
            'data:{"code": 0, "data": {"choices": [], "usage": {}}}',
            make_action_event("", "model-a", code=1, message="模型失败", finish_reason="stop").strip(),
        ]
        for line in cases:
            namespace = {
                "json": json, "os": __import__("os"), "request": Request(), "Response": Response,
                "stream_with_context": lambda fn: fn, "requests": Requests([line, make_action_event("unexpected", "model-a").strip()]),
                "consume_action_event": consume_action_event, "agent_error_event": agent_error_event,
                "logger": type("Logger", (), {"info": lambda *args: None, "exception": lambda *args: None})(),
            }
            exec(compile(ast.Module(body=[agent_start], type_ignores=[]), "server_open.py", "exec"), namespace)
            output = list(namespace["agent_start"]().response)
            self.assertEqual(len(output), 1)
            event = json.loads(output[0][5:])
            self.assertEqual(event["code"], 1)
            self.assertEqual(event["finish"], 1)
            self.assertEqual(event["usage"]["total_tokens"], 0)

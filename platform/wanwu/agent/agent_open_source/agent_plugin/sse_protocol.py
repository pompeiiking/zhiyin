import json


def make_action_event(content, model, code=0, message="ok", finish_reason="", usage=None):
    usage = usage or {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0}
    payload = {
        "code": code,
        "data": {
            "choices": [{"finish_reason": finish_reason, "index": 0,
                         "message": {"content": content, "role": "assistant"}}],
            "model": model,
            "object": "chat.completion",
            "usage": usage,
        },
        "msg": message,
    }
    return "data:" + json.dumps(payload, ensure_ascii=False) + "\n\n"


def parse_action_event(line):
    line = line.strip()
    if not line:
        return None
    if not line.startswith("data:"):
        raise ValueError("Action response is not an SSE data event")
    return json.loads(line[5:])


def empty_action_output_event(model, usage=None):
    return make_action_event(
        "",
        model,
        code=1,
        message="Action 执行失败",
        finish_reason="stop",
        usage=usage,
    )


def consume_action_event(line, answer, error_event):
    try:
        datajson = parse_action_event(line)
        if datajson is None:
            return None, False
        if datajson["code"] != 0:
            return error_event(datajson.get("msg")), True

        choice = datajson["data"]["choices"][0]
        content_str = choice["message"]["content"]
        usage = datajson["data"]["usage"]
        answer["code"] = datajson["code"]
        answer["message"] = datajson["msg"]
        if isinstance(content_str, dict):
            if "search_list" in content_str:
                answer["search_list"] = content_str.get("search_list")
            if "gen_file_url_list" in content_str:
                answer["gen_file_url_list"] = content_str.get("gen_file_url_list")
            answer["response"] = content_str.get("response")
        else:
            answer["response"] = content_str
        answer["finish"] = 0 if choice["finish_reason"] == "" else 1
        answer["usage"]["completion_tokens"] = usage["completion_tokens"]
        answer["usage"]["prompt_tokens"] = usage["prompt_tokens"]
        answer["usage"]["total_tokens"] = usage["total_tokens"]
        return answer, False
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        return error_event(str(exc)), True

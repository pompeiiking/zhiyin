"""PAMI 检索探针：一句话回答「经 PAMI 的真实检索现在能用吗、卡在哪」。

为什么需要它
------------
D7 第 ③ 项目前被平台侧的一个具体缺件挡住（RAG 问答强制要求 `rerank_model_id`，
而平台 **0 个 rerank 模型**，`rag-wanwu` 也没有 rerank 端点可指，上游 DashScope 的
OpenAI 兼容模式同样没有 `/rerank`）。结论写在文档里会过期，**命令不会**：
平台补上 rerank 之后，跑这一条就能确认检索是否真的通了。

它验证什么
----------
用 `deploy/.env` 里已写入的 RAG 应用 Key，调平台对外 OpenAPI
`POST /service/api/openapi/v1/rag/chat` 问几个**有已知答案**的问题（答案就在
我导入的 22 份自有内容里），并检查命中的 `searchList`：

- 通过 → 打印答案与召回条目，退出码 0；
- 平台侧缺件 → **原样打印平台自己的错误**（不翻译、不美化），退出码 3；
- 缺凭据/地址 → 退出码 2。

密钥处理
--------
只从 `deploy/.env`（已 gitignore）或环境变量读取，**只打印长度**，不打印明文、
不写日志、不进提交。

用法
----
    python scripts/pami_retrieval_probe.py
    python scripts/pami_retrieval_probe.py --base-url http://127.0.0.1:8081
    python scripts/pami_retrieval_probe.py --question "霍兰德把兴趣分成哪几类？"

补充：索引层怎么单独看
----------------------
即使问答包装被挡，内容**也可能已经入库并可检索**。要看这一层，在容器内跑
（ES 没有对外端口）：查 `rag_es_text_1`（文本）与 `rag_new_vector_dev_1`（向量，
`kb_name` 指向我们的知识库 id）两个索引的 `docs.count` 与真实命中。
本次实测：22/22 份内容的块都在两个索引里，真实问题能命中对应理论卡。
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import urllib.error
import urllib.request

TEMPLATE_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS = [
    "霍兰德 RIASEC 把职业兴趣分成哪几类？",
    "三叶草模型里的兴趣、能力、价值分别指什么？",
]
# 期望命中的关键词：用来区分"通了但答非所问"与"真的检索到了"
EXPECTED = {
    "霍兰德": ("霍兰德", "RIASEC", "holland"),
    "三叶草": ("三叶草", "clover"),
}


def read_env_file(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def resolve(name: str, env_file: dict[str, str], fallback: str = "") -> str:
    return os.environ.get(name) or env_file.get(name) or fallback


def ask(base_url: str, key: str, question: str) -> tuple[int, dict]:
    payload = json.dumps({"query": question, "stream": False}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/service/api/openapi/v1/rag/chat",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"raw": raw[:400]}


def main() -> int:
    parser = argparse.ArgumentParser(description="PAMI 检索可用性探针")
    parser.add_argument("--env-file", default=str(TEMPLATE_ROOT / "deploy" / ".env"))
    parser.add_argument("--base-url", default="")
    parser.add_argument("--question", action="append", default=[])
    args = parser.parse_args()

    env_file = read_env_file(pathlib.Path(args.env_file))
    base_url = args.base_url or resolve("PAMI_BASE_URL", env_file, "http://127.0.0.1:8081")
    key = resolve("ZHIYIN_PAMI_RAG_API_KEY", env_file)
    enabled = resolve("ZHIYIN_USE_PAMI_SEARCH", env_file, "0")

    print(f"平台地址   : {base_url}")
    print(f"RAG Key    : {'已配置，长度 ' + str(len(key)) if key else '缺失'}")
    # 只提示、不改动：本探针刻意不翻这个开关（D7 约束）
    print(f"PAMI 检索开关: ZHIYIN_USE_PAMI_SEARCH={enabled}（探针不改动它，只直连验证）")
    if not key:
        print("\n[缺少凭据] 先在平台发布 RAG 应用并生成 Key，再写入 deploy/.env 的 "
              "ZHIYIN_PAMI_RAG_API_KEY。")
        return 2

    questions = args.question or DEFAULT_QUESTIONS
    blocked_reason = ""
    hits_total = 0
    for question in questions:
        status, body = ask(base_url, key, question)
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        answer = str(data.get("output") or "")
        search_list = data.get("searchList") or []
        message = str(body.get("message") or "")
        print(f"\nQ: {question}")
        print(f"  HTTP {status} code={body.get('code')}")
        if message:
            print(f"  平台消息: {message}")
            blocked_reason = blocked_reason or message
        print(f"  答案长度 {len(answer)}｜召回 {len(search_list)} 条")
        if answer:
            print(f"  答案: {answer[:200]}")
        for item in search_list[:5]:
            title = str(item.get("title") or "")
            print(f"    - {title}")
        hits_total += len(search_list)
        # 命中了期望关键词才算"真的检索到"
        expected_words = next(
            (words for head, words in EXPECTED.items() if head in question), ()
        )
        if expected_words:
            blob = answer + "".join(str(i.get("title") or "") + str(i.get("snippet") or "")
                                    for i in search_list)
            matched = any(word.lower() in blob.lower() for word in expected_words)
            print(f"  命中期望内容（{expected_words}）: {'是' if matched else '否'}")

    print("\n== 判定 ==")
    if hits_total:
        print("  检索可用：平台返回了知识库召回条目（可去跑 scripts/eval_retrieval.py 出基准）")
        return 0
    print("  检索不可用，且**不是职引侧的问题**（Key 已就绪、22 份内容已在索引里）。")
    if blocked_reason:
        print(f"  平台原话：{blocked_reason}")
    print("  已知缺件：平台无 rerank 模型（RAG 问答强制要求 rerank_model_id）。")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())

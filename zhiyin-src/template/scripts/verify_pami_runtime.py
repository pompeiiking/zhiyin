"""验证真实 PAMI LLM、Embedding 与 RAG 应用。

仅使用已发布应用的 API Key；不打印密钥，也不创建持久数据。
"""

from __future__ import annotations

import asyncio
import json
import os

from zhiyin_data_sdk.gateways.ai import LLMMessage
from zhiyin_infrastructure.pami import (
    PamiEmbedGateway,
    PamiKnowledgeGateway,
    PamiLLMGateway,
)


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少真实 PAMI 验证配置：{name}")
    return value


async def main() -> None:
    base_url = required("ZHIYIN_PAMI_BASE_URL")
    model_id = required("ZHIYIN_PAMI_EMBEDDING_MODEL_ID")
    agent_key = required("ZHIYIN_PAMI_AGENT_API_KEY")
    rag_key = required("ZHIYIN_PAMI_RAG_API_KEY")

    embedding = PamiEmbedGateway(base_url, model_id)
    vectors = await embedding.embed(["职引真实嵌入探针"])
    if len(vectors) != 1 or len(vectors[0]) != 1024:
        raise RuntimeError("真实 Embedding 没有返回单个 1024 维向量")

    llm = PamiLLMGateway(base_url, agent_key)
    answer = await llm.chat(
        [LLMMessage(role="user", content="只回复：职引真实模型探针成功")],
        temperature=0.0,
    )
    if not answer.text.strip() or answer.degraded:
        raise RuntimeError("真实 LLM 没有返回有效结果")

    knowledge = PamiKnowledgeGateway(base_url, rag_key)
    hits = await knowledge.search("职引探针知识", top_k=3)

    print(
        json.dumps(
            {
                "embedding": {"model": model_id, "dimension": len(vectors[0])},
                "llm": {"model": answer.model, "characters": len(answer.text)},
                "rag": {"hits": len(hits)},
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())


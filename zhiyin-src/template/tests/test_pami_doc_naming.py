"""平台文档命名约定与 PAMI 来源回填的测试（D7 ③ 的回填口径）。

为什么值得单测：这条约定是**唯一**能让平台命中对回权威表的线索——平台不回文档 id
（响应只有 `kb_name/title/snippet`）。约定一旦漂移，权威回填会**静默失配**、命中被
整条丢弃（表现为检索恒空），所以反解规则必须被钉住。
"""

from __future__ import annotations

import httpx
import pytest

from zhiyin_infrastructure.pami.adapters import PamiSearchGateway
from zhiyin_infrastructure.pami.doc_naming import build_doc_name, parse_doc_name
from zhiyin_kernel.enums import RetrievalNamespace
from zhiyin_kernel.retrieval import RetrievalQuery


def test_parse_plain_document_name() -> None:
    parsed = parse_doc_name("theory_theory-holland-riasec.txt")
    assert parsed is not None
    assert (parsed.namespace, parsed.doc_id, parsed.is_theory_card) == (
        "theory",
        "theory-holland-riasec",
        False,
    )


def test_parse_theory_card_name_keeps_underscores_in_id() -> None:
    """`<ns>_card_<id>`：id 里的下划线必须**完整保留**，不能被二次切分。"""
    parsed = parse_doc_name("theory_card_holland_riasec.txt")
    assert parsed is not None
    assert (parsed.namespace, parsed.doc_id, parsed.is_theory_card) == (
        "theory",
        "holland_riasec",
        True,
    )


def test_parse_occupation_code_with_dashes() -> None:
    parsed = parse_doc_name("occupation_occ-2-02-10-01.txt")
    assert parsed is not None
    assert (parsed.namespace, parsed.doc_id) == ("occupation", "occ-2-02-10-01")


@pytest.mark.parametrize(
    "name",
    [
        "",
        "notes.txt",  # 没有 namespace 前缀
        "theory.txt",  # 只有 namespace
        "unknown_ns_doc.txt",  # namespace 不在已知集合内
        "theory_card_.txt",  # card 标记后没有 id
    ],
)
def test_unparsable_names_return_none_instead_of_guessing(name: str) -> None:
    """反解不了就返回 None —— 调用方回落到内容哈希。

    这里刻意不"猜一个最像的 id"：猜错会让权威回填静默失配，比缺一条溯源更糟。
    """
    assert parse_doc_name(name) is None


def test_build_and_parse_are_inverse() -> None:
    for namespace, doc_id, is_card in (
        ("theory", "clover", False),
        ("theory", "clover", True),
        ("occupation", "occ-2-02-10-01", False),
    ):
        name = build_doc_name(namespace, doc_id, is_theory_card=is_card)
        parsed = parse_doc_name(name)
        assert parsed is not None
        assert (parsed.namespace, parsed.doc_id, parsed.is_theory_card) == (
            namespace,
            doc_id,
            is_card,
        )


def test_build_rejects_unknown_namespace() -> None:
    with pytest.raises(ValueError, match="namespace"):
        build_doc_name("nope", "x")


@pytest.mark.asyncio
async def test_pami_hits_recover_source_id_from_the_doc_name() -> None:
    """平台不回文档 id，但**文件名**能反解出来——这是权威回填与溯源的关键。"""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "output": "answer",
                    "searchList": [
                        {"kb_name": "职引知识库", "title": "theory_card_clover.txt",
                         "snippet": "三叶草模型"},
                        {"kb_name": "职引知识库", "title": "无法反解的名字",
                         "snippet": "未知来源"},
                    ],
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        search = PamiSearchGateway("http://nginx:8081", "api-key", client=client)
        hits = await search.search(
            RetrievalQuery(
                query="三叶草", namespace=RetrievalNamespace.THEORY, mode="keyword"
            )
        )

    assert hits[0].source_id == "clover"
    assert hits[0].evidence_id == "theory:clover", "应与权威表主键同形"
    assert hits[0].metadata["doc_kind"] == "theory_card"
    assert hits[0].metadata["id_parsed"] is True

    # 反解不了的那条：回落哈希、id_parsed=False，但仍然带 namespace 前缀（D11）
    assert hits[1].metadata["id_parsed"] is False
    assert hits[1].evidence_id.startswith("theory:")
    assert hits[1].source_id == ""

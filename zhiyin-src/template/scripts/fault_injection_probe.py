"""D7 ⑤ 真实基础设施故障注入探针（只读，不写业务数据）。

为什么不能只有单测
------------------
单元测试用 `FailingVector` 这类假件抛异常，只能证明"分支写对了"；它证明不了
**真实驱动/网络故障时的行为**，也证明不了故障真的被注入进去了。

本探针在**真实装配好的容器里**制造真实故障（真实连接被拒、真实 DNS 失败），
逐项验证：

1. 关键词通道真故障 → 降级到向量通道，并如实标记 degraded；
2. 向量通道真故障 → 降级到关键词通道，并如实标记 degraded；
3. 两条都真故障 → 显式 `RuntimeError`，而不是返回空列表冒充"没有相关内容"；
4. 无命中 ≠ 故障（无命中必须 `degraded=False`）；
5. Rerank 未接入时检索照常可用。

用法（在容器内跑，因为要用容器自己的装配与配置）：

    docker cp scripts/fault_injection_probe.py <container>:/tmp/probe.py
    docker exec -w /app <container> python /tmp/probe.py

⚠️ 探针必须先证明"正常路径可用"，否则它自己会骗人
--------------------------------------------------
第一版探针用 8 维向量去查要求 1024 维的 `PgVectorGateway`，而该网关在**连接之前**
就抛 `ValidationError`，于是同时产生两个错误结论：把"健康但维度不匹配"当成
"向量库宕机"，又让"死主机"用例根本没走到网络。**一个假故障掩盖了另一个假故障。**
因此本探针先做健康度体检（§1），再做故障注入，并在每个故障用例后单独确认
"这个故障真的存在"。这也是 `degraded_reasons`（区分配置错 / 连不上）的由来。

不打印任何连接串 / 口令 / Key。
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from zhiyin_boot.container import build_container
from zhiyin_boot.container.ports import GATEWAY_PORTS
from zhiyin_infrastructure.local.embedding import LocalHashEmbedder
from zhiyin_infrastructure.local.knowledge import LocalSearchGateway
from zhiyin_infrastructure.pami.adapters import PamiSearchGateway
from zhiyin_infrastructure.pgvector import VECTOR_DIMENSION, PgVectorGateway
from zhiyin_infrastructure.search import RrfHybridSearchGateway
from zhiyin_kernel.enums import RetrievalNamespace
from zhiyin_kernel.retrieval import RetrievalQuery

THEORY = RetrievalNamespace.THEORY
DEAD_KEYWORD_URL = "http://127.0.0.1:1"  # 容器内 1 端口必然被拒
PROBE_TOP_K = 5


class AuditSpy:
    """与生产同形状的审计接收方，只记不写库。

    "降级是否被标记"不能靠返回条数来读（本来就可能零命中），而要走与生产同一条
    `audit.record(degraded=...)` 通路，这样零命中时结论依然成立。
    """

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    async def record(self, **kwargs: Any) -> None:
        self.records.append(kwargs)

    @property
    def last_degraded(self) -> bool | None:
        return self.records[-1]["degraded"] if self.records else None


def _query(text: str = "职业兴趣", top_k: int = PROBE_TOP_K) -> RetrievalQuery:
    return RetrievalQuery(query=text, namespace=THEORY, top_k=top_k)


def _dead_host_dsn(dsn: str) -> str:
    """把真实 DSN 的 host 换成不存在的域名——**真实 DNS 失败**，其余原样保留。"""
    head, _, tail = dsn.partition("@")
    assert head and tail, "DSN 形状与预期不符"
    database = tail.partition("/")[2]
    return f"{head}@pgvector-does-not-exist.invalid:5432/{database}"


async def _probe_channel(name: str, gateway: Any) -> bool:
    """真实通道健康度体检——先确认"正常情况确实能用"，故障结论才有意义。"""
    try:
        hits = await gateway.search(_query())
        print(f"  {name}: 可用，返回 {len(hits)} 条")
        return True
    except Exception as exc:  # noqa: BLE001 - 探针要把任何故障都报出来
        print(f"  {name}: 不可用（{type(exc).__name__}）")
        return False


async def _confirm_fault_is_real(
    name: str, call: Any, failures: list[str], *, expect: str
) -> None:
    """单独确认"这个故障真的存在"，避免用例通过是因为别的原因。

    ⚠️ 这里必须用**各自通道的真实签名**去调用。第一版把统一的 `RetrievalQuery`
    直接丢给 `PgVectorGateway.search(namespace, vector)`，于是确认语句拿到的是
    `TypeError`（pydantic 模型不可哈希）——它证明的只是"我调用错了"，与 DNS 是否
    失败毫无关系，却看起来像"故障已确认"。`expect` 因此要求写清预期异常类名。
    """
    try:
        await call()
    except Exception as exc:  # noqa: BLE001
        actual = type(exc).__name__
        print(f"  {name} 故障真实性确认：{actual}")
        if actual != expect:
            failures.append(f"{name}：故障确认拿到 {actual}，预期 {expect}（不是同一个故障）")
        return
    failures.append(f"{name}：故障没有真正注入（居然调用成功了）")


async def main() -> int:
    container = build_container()
    search = container.search
    failures: list[str] = []

    print("== 0. 真实装配 ==")
    print(f"  search    = {type(search).__name__}")
    print(f"  embedding = {type(container.embedding).__name__}")
    print(f"  vector    = {type(container.vector).__name__}")
    print(f"  Rerank 能力位存在 = {'rerank' in GATEWAY_PORTS}")
    if not isinstance(search, RrfHybridSearchGateway):
        print("  [注意] 装配出来的不是 RRF 混合检索，以下结论不适用")
        return 2

    print("== 1. 真实通道健康度体检（先证明正常可用）==")
    real_keyword = search._keyword  # noqa: SLF001 - 探针需要拿到真实通道实现
    print(f"  关键词通道实现 = {type(real_keyword).__name__}")
    if not await _probe_channel("关键词通道（真实）", real_keyword):
        real_keyword = LocalSearchGateway()
        print("  → 回退为 LocalSearchGateway（真实本地实现）当「可用的关键词通道」")
        await _probe_channel("关键词通道（本地回退）", real_keyword)

    embedder = LocalHashEmbedder(dim=VECTOR_DIMENSION, model_id="probe")
    try:
        vector = (await embedder.embed(["职业兴趣"]))[0]
        rows = await container.vector.search(
            THEORY.value, vector, model="probe", top_k=3
        )
        print(f"  真实 pgvector: 可用，theory 命名空间命中 {len(rows)} 条（空库=0 属正常）")
    except Exception as exc:  # noqa: BLE001
        print(f"  真实 pgvector: 不可用（{type(exc).__name__}）")

    print("== 2. 用例 A：关键词通道真故障（真实连接被拒）==")
    broken_keyword = PamiSearchGateway(DEAD_KEYWORD_URL, "probe", timeout_s=2.0)
    spy = AuditSpy()
    probe = RrfHybridSearchGateway(broken_keyword, embedder, container.vector, audit=spy)
    try:
        hits = await probe.search(_query())
        print(f"  未抛异常，返回 {len(hits)} 条，审计 degraded={spy.last_degraded}")
        if spy.last_degraded is not True:
            failures.append("用例 A：关键词真故障未如实标记 degraded")
        if hits and hits[0].metadata["retrieval"]["degraded_channels"] != ["keyword"]:
            failures.append("用例 A：命中 metadata 的 degraded_channels 不正确")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"用例 A：单通道故障不该整体失败，实际抛 {type(exc).__name__}")
    await _confirm_fault_is_real(
        "用例 A",
        lambda: broken_keyword.search(_query()),
        failures,
        expect="UnavailableError",
    )

    print("== 3. 用例 B：向量通道真故障（真实 DNS 失败）==")
    dead_vector = PgVectorGateway(_dead_host_dsn(container.settings.vector_database_url))
    spy = AuditSpy()
    probe = RrfHybridSearchGateway(real_keyword, embedder, dead_vector, audit=spy)
    try:
        hits = await probe.search(_query())
        print(f"  未抛异常，返回 {len(hits)} 条，审计 degraded={spy.last_degraded}")
        if spy.last_degraded is not True:
            failures.append("用例 B：向量真故障未如实标记 degraded")
        if hits and hits[0].metadata["retrieval"]["degraded_channels"] != ["vector"]:
            failures.append("用例 B：命中 metadata 的 degraded_channels 不正确")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"用例 B：单通道故障不该整体失败，实际抛 {type(exc).__name__}")
    await _confirm_fault_is_real(
        "用例 B",
        lambda: dead_vector.search(
            THEORY.value, [0.0] * VECTOR_DIMENSION, model="probe", top_k=1
        ),
        failures,
        expect="UnavailableError",
    )

    print("== 4. 用例 C：两条通道都真故障 ==")
    probe = RrfHybridSearchGateway(broken_keyword, embedder, dead_vector, audit=AuditSpy())
    try:
        hits = await probe.search(_query())
        failures.append(f"用例 C：全通道故障却返回 {len(hits)} 条，属静默伪成功")
        print(f"  [失败] 未抛异常，返回 {len(hits)} 条")
    except RuntimeError as exc:
        print(f"  如期显式失败：RuntimeError: {exc}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"用例 C：抛的不是 RuntimeError 而是 {type(exc).__name__}")

    print("== 5. 用例 D：无命中不是故障 ==")
    spy = AuditSpy()
    probe = RrfHybridSearchGateway(real_keyword, embedder, container.vector, audit=spy)
    try:
        hits = await probe.search(_query("zzz-不存在的关键词-zzz", top_k=3))
        print(f"  正常返回 {len(hits)} 条，审计 degraded={spy.last_degraded}")
        if spy.last_degraded is not False:
            failures.append("用例 D：无命中却标记了 degraded（会把「没内容」误报成「故障」）")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"用例 D：无命中不该抛异常，实际抛 {type(exc).__name__}")

    print("== 6. 用例 E：Rerank 未接入（平台实测 0 个 rerank 模型）==")
    if "rerank" in GATEWAY_PORTS:
        failures.append("用例 E：容器里出现了 rerank 能力位，与「未接入」的前提不符")
    else:
        hits = await RrfHybridSearchGateway(
            real_keyword, embedder, container.vector
        ).search(_query())
        print(f"  无 Rerank 也能检索：返回 {len(hits)} 条")
        if hits:
            print(f"  命中算法声明 = {hits[0].metadata['retrieval']['algorithm']}")
            if hits[0].metadata["retrieval"]["algorithm"] != "rrf":
                failures.append("用例 E：无 Rerank 时算法声明不是 rrf")

    print("== 结论 ==")
    if failures:
        for item in failures:
            print(f"  [失败] {item}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

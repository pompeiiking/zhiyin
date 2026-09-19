"""本地统一检索实现。

本地模式从 JSON 读取知识卡并提供关键词匹配；生产模式由 Boot 使用
PAMI Embedding、pgvector 与 RRF 组合成统一 Search 实现。

与《业务数据采集与存储来源设计》的对应关系：
- `data/knowledge/{namespace}.json` 是**公共知识库**（专业 / 职业 / 岗位 / 政策），
  只作报告与方案里的 evidence / sources 引用，**不写入 profile_field**；
- 命中结果必须带 `source_url` 与 `fetched_at`（该文档 R-CRAWL-006），
  因此 metadata 透传原始条目字段，不做裁剪。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from zhiyin_data_sdk.gateways.ai import SearchGateway
from zhiyin_kernel.retrieval import RetrievalEvidence, RetrievalQuery

class LocalSearchGateway(SearchGateway):
    """按 namespace 读取本地 JSON；本地环境只提供关键词通道。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(self, data_dir: str = "data/knowledge") -> None:
        self._data_dir = Path(data_dir)
        self._cache: dict[str, list[dict[str, Any]]] = {}
        self._demo_namespaces: set[str] | None = None

    @property
    def demo_namespaces(self) -> set[str]:
        """自述为演示数据的 namespace 集合（按文件判定，不是整个目录一刀切）。

        **按 namespace 判定**是有意的：真实内容会一个域一个域地补进来（例如 theory
        先换成真实卡片、jd 仍是空的），一刀切会在那时把真实内容也标成演示。
        """
        if self._demo_namespaces is None:
            self._demo_namespaces = self._scan_demo_namespaces()
        return self._demo_namespaces

    @property
    def serves_demo_content(self) -> bool:
        """当前语料里是否**有**演示数据（D12）。

        为什么要暴露这个属性：这些卡片会被当作证据进入报告，而此前系统对它是不是
        演示内容一无所知——相位门禁只问"search 能力位装没装上"，于是演示语料照样
        让 phase 3 判绿，`/healthz` 也显示 `ok`。装配报告据此如实上报，不再假装
        "实现装上了"就等于"内容是真的"。

        判定方式：语料文件自带的 `_note` 里出现 `DEMO` / `演示`。刻意**只看语料
        自己的声明**，不靠环境名或文件路径猜——路径猜法会在换目录时静默失效。

        结果缓存：`/healthz` 会被反复探活，不能每次都重扫语料。单个文件读取失败按
        "不是演示内容"处理，避免把一次目录/格式问题升级成启动失败（真正搜索时该
        错误照样会暴露）。
        """
        return bool(self.demo_namespaces)

    def _scan_demo_namespaces(self) -> set[str]:
        found: set[str] = set()
        if not self._data_dir.is_dir():
            return found
        for path in sorted(self._data_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            note = str(payload.get("_note") or "")
            if "DEMO" in note.upper() or "演示" in note:
                found.add(path.stem)
        return found

    async def search(self, request: RetrievalQuery) -> list[RetrievalEvidence]:
        if request.mode == "vector":
            return []
        namespace = request.namespace.value
        namespaces = [namespace]
        terms = _terms(request.query)
        scored: list[tuple[float, RetrievalEvidence]] = []

        for space in namespaces:
            for index, raw in enumerate(self._load(space)):
                if raw.get("status", "enabled") != "enabled":
                    continue
                review_status = raw.get("review_status")
                if review_status is not None and review_status != "approved":
                    continue
                if request.filters and not _match_filters(raw, request.filters):
                    continue
                score = _score(raw, terms)
                if score <= 0:
                    continue
                # 逐条标出"这条是演示内容"（D12）：装配报告只能说明整条通道可疑，
                # 而引用核对要按**单条证据**决定收不收，所以标记必须落到命中上。
                metadata = {
                    **raw,
                    "namespace": space,
                    "demo": space in self.demo_namespaces,
                }
                scored.append(
                    (
                        score,
                        RetrievalEvidence(
                            # `evidence_id` 必须带 namespace（D11）：评测集、权威文档存储
                            # （`RetrievalDocumentStore` 的 `document_id`）与跨通道 RRF 去重
                            # 都按 `namespace:id` 取键；这里若只写裸 id，同一篇文档会因
                            # 通道不同而被当成两篇，且评测期望永远匹配不上。
                            evidence_id=f"{space}:{raw.get('id') or f'{space}-{index}'}",
                            namespace=request.namespace,
                            source_id=str(raw.get("source_id") or raw.get("id") or ""),
                            source_url=str(raw.get("source_url") or ""),
                            title=str(raw.get("title") or raw.get("name") or ""),
                            content=str(raw.get("summary") or raw.get("content") or ""),
                            score=score,
                            version=max(int(raw.get("version") or 1), 1),
                            metadata=metadata,
                        ),
                    )
                )

        scored.sort(key=lambda item: (-item[0], item[1].evidence_id))
        return [hit for _, hit in scored[: request.top_k]]

    def _load(self, namespace: str) -> list[dict[str, Any]]:
        if namespace in self._cache:
            return self._cache[namespace]
        path = self._data_dir / f"{namespace}.json"
        items: list[dict[str, Any]] = []
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            payload = raw.get("items", []) if isinstance(raw, dict) else raw
            items = [item for item in payload if isinstance(item, dict)]
        self._cache[namespace] = items
        return items

    def reload(self) -> None:
        """清缓存，用于演示"改知识库不重启"。"""
        self._cache.clear()


def _terms(query: str) -> list[str]:
    """第一期本地切分：标点分段，并为连续中文补二元词。

    这样“计算机专业”可以命中“计算机类专业”，无需引入分词依赖；英文或编码
    仍使用原始分段，真实分词与向量召回留到 M3。
    """
    normalized = query or ""
    for token in "，。！？、；：（）【】《》,.!?;:()[]\"'\n\t":
        normalized = normalized.replace(token, " ")
    terms: list[str] = []
    for part in normalized.split(" "):
        if len(part) < 2:
            continue
        terms.append(part)
        if len(part) > 2 and all("\u4e00" <= char <= "\u9fff" for char in part):
            terms.extend(part[index : index + 2] for index in range(len(part) - 1))
    return list(dict.fromkeys(terms))


def _score(raw: dict[str, Any], terms: list[str]) -> float:
    if not terms:
        return 0.0
    haystack = " ".join(
        str(raw.get(field, "")) for field in ("title", "name", "summary", "content", "tags")
    )
    score = 0.0
    for term in terms:
        if term in haystack:
            score += 1.0
    if score > 0 and str(raw.get("title") or raw.get("name") or "") and any(
        term in str(raw.get("title") or raw.get("name") or "") for term in terms
    ):
        # 标题命中加权，避免正文偶然包含就把结果排到前面。
        score += 0.5
    return score


def _match_filters(raw: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        actual = raw.get(key)
        if isinstance(expected, (list, tuple, set)):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


__all__ = ["LocalSearchGateway"]

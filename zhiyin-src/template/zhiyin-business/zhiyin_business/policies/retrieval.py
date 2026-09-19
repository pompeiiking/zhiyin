"""五环节检索需求判断与确定性 Query Plan。"""

from __future__ import annotations

import re

from zhiyin_kernel.enums import LoopStage, RetrievalNamespace
from zhiyin_kernel.retrieval import RetrievalPlan, RetrievalQuery


_STAGE_NAMESPACES: dict[LoopStage, tuple[RetrievalNamespace, ...]] = {
    LoopStage.COLLECT: (RetrievalNamespace.RESUME, RetrievalNamespace.MEMORY),
    LoopStage.DIAGNOSE: (
        RetrievalNamespace.OCCUPATION,
        RetrievalNamespace.JD,
        RetrievalNamespace.RESUME,
        RetrievalNamespace.REPORT,
        RetrievalNamespace.THEORY,
    ),
    LoopStage.DECIDE: (
        RetrievalNamespace.OCCUPATION,
        RetrievalNamespace.JD,
        RetrievalNamespace.REPORT,
        RetrievalNamespace.RESUME,
        RetrievalNamespace.THEORY,
    ),
    LoopStage.ACT: (
        RetrievalNamespace.JD,
        RetrievalNamespace.OCCUPATION,
        RetrievalNamespace.REPORT,
    ),
    LoopStage.REVIEW: (
        RetrievalNamespace.MEMORY,
        RetrievalNamespace.REPORT,
        RetrievalNamespace.THEORY,
    ),
}

_COLLECT_HINTS = ("简历", "项目", "经历", "以前", "上次", "历史")
_REVIEW_EXTERNAL_HINTS = ("岗位", "招聘", "政策", "行情", "截止", "变化")


def _query_targets(stage: LoopStage, message: str) -> list[str]:
    """决策比较时拆成对称子查询；不调用模型、不引入 IO。"""
    if stage is not LoopStage.DECIDE or not any(
        token in message for token in ("对比", "比较", "还是", "和")
    ):
        return [message]
    targets = [
        item.strip(" ，。；：")
        for item in re.split(r"(?:还是|对比|比较|、|/|和)", message)
        if item.strip(" ，。；：")
    ]
    return list(dict.fromkeys(targets))[:4] or [message]


class RetrievalPlanningPolicy:
    """只产生检索计划，不执行 IO。"""

    def plan(
        self,
        *,
        stage: LoopStage,
        intent: str,
        message: str,
        user_id: str,
        org_id: str = "",
        trace_id: str = "",
        top_k: int = 5,
    ) -> RetrievalPlan:
        normalized = message.strip()
        required = bool(normalized) and (
            stage in {LoopStage.DIAGNOSE, LoopStage.DECIDE, LoopStage.ACT, LoopStage.REVIEW}
            or any(token in normalized for token in _COLLECT_HINTS)
        )
        namespaces = list(_STAGE_NAMESPACES[stage]) if required else []
        if stage is LoopStage.REVIEW and any(
            token in normalized for token in _REVIEW_EXTERNAL_HINTS
        ):
            namespaces.extend((RetrievalNamespace.JD, RetrievalNamespace.OCCUPATION))

        queries: list[RetrievalQuery] = []
        targets = _query_targets(stage, normalized)
        for namespace in dict.fromkeys(namespaces):
            filters: dict[str, object] = {"status": "enabled"}
            if namespace in {
                RetrievalNamespace.REPORT,
                RetrievalNamespace.MEMORY,
                RetrievalNamespace.RESUME,
            }:
                filters["user_id"] = user_id
                if org_id:
                    filters["org_id"] = org_id
            for target in targets:
                queries.append(
                    RetrievalQuery(
                        query=target,
                        namespace=namespace,
                        mode="hybrid",
                        top_k=top_k,
                        filters=filters,
                        org_id=org_id,
                        user_id=user_id,
                        trace_id=trace_id,
                    )
                )
        return RetrievalPlan(
            stage=stage,
            intent=intent,
            question=normalized,
            required=required,
            queries=queries,
            reason=("本环节需要外部事实或历史证据" if required else "本轮只需黑板事实"),
        )


__all__ = ["RetrievalPlanningPolicy"]

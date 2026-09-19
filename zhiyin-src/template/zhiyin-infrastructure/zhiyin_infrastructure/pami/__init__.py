"""PAMI 平台适配器的稳定导出面。"""

from zhiyin_infrastructure.pami.adapters import (
    PamiAuthGateway,
    PamiEmbedGateway,
    PamiLLMGateway,
    PamiSearchGateway,
)

__all__ = [
    "PamiAuthGateway",
    "PamiEmbedGateway",
    "PamiLLMGateway",
    "PamiSearchGateway",
]

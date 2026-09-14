"""文档对齐守卫。

为什么值得守：本期实测发现 **18 处断链**（引用了已移动或不存在的文档），
以及若干"文档写了、代码没有"的漂移（8 个服务只写在表格里、
`business/workers/base.py` 已删除但文档仍在引用、接口路径与 `/api/v1` 前缀不一致）。
文档漂移的代价是**照错抄**：新人照着文档去改一个不存在的文件。

本文件只守两件机械可判的事：

1. 文档里的**相对链接必须能解析到真实文件**（仓外文档用文字引用、不放链接）；
2. **文档地图**（第一份该读的文件）必须齐全。

它不检查文字表述是否正确——那需要人看。
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

import pytest

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TEMPLATE_ROOT.parents[1]
DOCS_ROOT = REPO_ROOT / "docs"

# 外部协议：不解析成本地文件
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "codex:", "tel:")

# 文档地图：这几份是"第一份该读的"，缺任何一份都说明文档结构被破坏
CANONICAL_DOCS: dict[str, str] = {
    "docs/开发指南.md": "开发入口：架构地图与落位手册",
    "docs/PRD/职引-PRD-v2.0.md": "需求基线",
    "docs/技术架构文档/职引技术架构文档.md": "总体技术架构",
    "docs/技术架构文档/职引-目标架构设计-v1.0.md": "目标架构与落地状态",
    "docs/技术架构文档/第一期工程/第一期技术架构文档/职引技术架构文档-第一期.md": "第一期架构基线",
    "docs/前端设计/职引-前端页面设计-v1.0.md": "页面与交互口径",
    "docs/评审/职引-架构与代码结构评估-v1.0.md": "改造前评估快照",
    "prototype/原型设计说明.md": "高保真原型规格",
    "zhiyin-src/template/README.md": "工程上手说明",
}


def _markdown_files() -> list[Path]:
    files = sorted(DOCS_ROOT.rglob("*.md"))
    files += sorted((REPO_ROOT / "prototype").rglob("*.md"))
    files.append(TEMPLATE_ROOT / "README.md")
    return [path for path in files if path.is_file()]


def _relative_links(path: Path) -> list[str]:
    """取出一条 markdown 文档里的全部相对链接目标（去掉锚点）。"""
    text = path.read_text(encoding="utf-8")
    targets: list[str] = []
    for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
        raw = match.group(1).strip().strip("<>")
        if not raw or raw.startswith(EXTERNAL_PREFIXES) or raw.startswith("#"):
            continue
        target = unquote(raw.split("#")[0].strip())
        if target:
            targets.append(target)
    return targets


@pytest.mark.parametrize("doc", _markdown_files(), ids=lambda p: str(p.name))
def test_relative_links_resolve(doc: Path) -> None:
    """文档里的相对链接必须指向真实存在的文件。

    仓外文档（如原 `recourse/` 下的 BRD / FRD）**不要**写成链接：断链比没有链接
    更容易误导——读者会以为文件在仓库里。
    """
    broken = [
        target
        for target in _relative_links(doc)
        if not (doc.parent / target).resolve().exists()
    ]
    assert not broken, (
        f"{doc.relative_to(REPO_ROOT)} 存在断链：{broken}。"
        "指向仓外文档时请改为文字引用并标注『仓外文档，未纳入本仓』"
    )


@pytest.mark.parametrize("relative_path", sorted(CANONICAL_DOCS))
def test_canonical_doc_exists(relative_path: str) -> None:
    """文档地图必须齐全：这几份是团队上手与对齐的入口。"""
    path = REPO_ROOT / relative_path
    assert path.is_file(), (
        f"文档地图缺件：{relative_path}（{CANONICAL_DOCS[relative_path]}）。"
        "若确实要改位置，请同步更新本测试与 docs/开发指南.md"
    )

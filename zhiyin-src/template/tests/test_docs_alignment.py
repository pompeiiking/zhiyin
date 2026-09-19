"""文档对齐守卫。

为什么值得守：本期实测发现 **18 处断链**（引用了已移动或不存在的文档），
以及若干"文档写了、代码没有"的漂移（8 个服务只写在表格里、
`business/workers/base.py` 已删除但文档仍在引用、接口路径与 `/api/v1` 前缀不一致）。
文档漂移的代价是**照错抄**：新人照着文档去改一个不存在的文件。

本文件只守两件机械可判的事：

1. 文档里的**相对链接必须能解析到真实文件**（仓外文档用文字引用、不放链接）；
2. **文档地图**（第一份该读的文件）必须齐全。

在此基础上补三类"照错抄"风险最高的检查（第三轮补充）：

3. 文档里用代码片段引用的**仓库路径必须存在**（含目录与文件）；
4. 文档里的**能力位数量必须与 `container/ports.py` 一致**；
5. 门禁 JSON 的 `manual` 项里提到的**目录必须存在**（否则验收口径悬空）。

它不检查文字表述是否正确——那需要人看。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TEMPLATE_ROOT.parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
REGISTRY_DIR = TEMPLATE_ROOT / "data" / "registry"

# 外部协议：不解析成本地文件
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "codex:", "tel:")

# 文档地图：这几份是"第一份该读的"，缺任何一份都说明文档结构被破坏
CANONICAL_DOCS: dict[str, str] = {
    "README.md": "仓根入口（五分钟上手 + 五条底线）",
    "docs/README.md": "文档索引（先读哪几份）",
    "docs/开发指南.md": "开发入口：架构地图与落位手册",
    "docs/PRD/职引-PRD-v2.0.md": "需求基线",
    "docs/技术架构文档/职引技术架构文档.md": "总体技术架构",
    "docs/技术架构文档/职引-目标架构设计-v1.0.md": "目标架构与落地状态",
    "docs/评审/职引-架构与结构评估-最终版.md": "架构与结构评估（唯一当前状态）",
    "docs/评审/业务口径决策记录-v1.0.md": "业务口径基线（16 项已定稿）",
    "docs/技术架构文档/第一期工程/第一期技术架构文档/职引技术架构文档-第一期.md": "第一期架构基线",
    "docs/前端设计/职引-前端页面设计-v1.0.md": "页面与交互口径",
    "prototype/原型设计说明.md": "高保真原型规格",
    "zhiyin-src/template/README.md": "工程上手说明",
}

# 需要做"引用路径存在性"检查的文档：都是**当前有效**的文档（不是历史快照）。
# 历史评估（v1.0 / v1.1 / v1.2）已降级为快照，不在检查范围内——
# 它们顶部的"已废弃"横幅已指向最终版，读者不会再被旧路径误导。
CURRENT_DOCS: tuple[str, ...] = (
    "README.md",
    "docs/README.md",
    "docs/开发指南.md",
    "docs/前端设计/职引-前端页面设计-v1.0.md",
    "docs/评审/职引-架构与结构评估-最终版.md",
    "docs/评审/业务口径决策记录-v1.0.md",
    "docs/技术架构文档/职引-目标架构设计-v1.0.md",
    "docs/技术架构文档/第一期工程/第一期技术架构文档/职引技术架构文档-第一期.md",
    "docs/技术架构文档/第一期工程/第一期分层设计文档/职引技术架构-分层详细设计.md",
    "docs/技术架构文档/第一期工程/第一期分层设计文档/第一期分层设计定义/职引技术架构-分层实现与接口设计.md",
    "zhiyin-src/template/README.md",
    "zhiyin-src/template/zhiyin-web/README.md",
)

# 文档里**故意**提到的不存在路径，逐条给出理由。
# 加一条之前先问：能不能把文档改成指向真实文件？能改就改，别往这里加。
DOCUMENTED_MISSING_PATHS: dict[str, str] = {
    # 历史名 / 已删除物：文档在讲"它原来叫什么、为什么拆"，本身就不该存在
    "business/domain/": "改名前的目录名（`domain/` → `ports/`）",
    "domain/": "同上",
    "workers/base.py": "已删除（Worker 基类下放到 zhiyin_kernel/worker.py）",
    "business/workers/base.py": "同上",
    "zhiyin_data_sdk/contracts/": "已迁出（共享内核归位到 zhiyin-kernel）",
    "zhiyin-data-sdk/zhiyin_data_sdk/contracts/": "同上",
    "zhiyin_orchestration/impl.py": "已拆为 impl/（一原语一文件）",
    "facade/mock.py": "已删除（OPEN-4：Mock 门面与 ZHIYIN_MOCK 死配置一并移除）",
    "api/facade/mock.py": "同上",
}


def _markdown_files() -> list[Path]:
    files = sorted(DOCS_ROOT.rglob("*.md"))
    files += sorted((REPO_ROOT / "prototype").rglob("*.md"))
    files.append(REPO_ROOT / "README.md")
    files.append(TEMPLATE_ROOT / "README.md")
    files.append(TEMPLATE_ROOT / "zhiyin-web" / "README.md")
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


# --------------------------------------------------------------------------
# 3. 文档里引用的仓库路径必须存在
# --------------------------------------------------------------------------

_PATH_EXTENSIONS = (".py", ".json", ".toml", ".md", ".ts", ".vue", ".yml", ".yaml", ".cfg")

# 文档写路径时的简写约定 → 真实位置。
# 例：`services/registry.py` 其实是 `zhiyin-business/zhiyin_business/services/registry.py`，
# `api/dto/mappers.py` 是 `zhiyin-api/zhiyin_api/dto/mappers.py`。
_SHORTHAND_ALIASES: dict[str, str] = {
    "api": "zhiyin-api/zhiyin_api",
    "business": "zhiyin-business/zhiyin_business",
    "kernel": "zhiyin-kernel/zhiyin_kernel",
    "data_sdk": "zhiyin-data-sdk/zhiyin_data_sdk",
    "orchestration": "zhiyin-orchestration/zhiyin_orchestration",
    "infrastructure": "zhiyin-infrastructure/zhiyin_infrastructure",
    "boot": "zhiyin-boot/zhiyin_boot",
    "web": "zhiyin-web",
}


def _package_dirs() -> list[Path]:
    return sorted(
        path
        for path in TEMPLATE_ROOT.iterdir()
        if path.is_dir() and path.name.startswith("zhiyin-")
    )


def _resolves(relative: str, doc_dir: Path) -> bool:
    """把文档里的一个路径片段解析到真实文件（按约定依次尝试）。"""
    candidates: list[Path] = [REPO_ROOT / relative, doc_dir / relative, TEMPLATE_ROOT / relative]

    head, _, rest = relative.partition("/")
    if head in _SHORTHAND_ALIASES and rest:
        candidates.append(TEMPLATE_ROOT / _SHORTHAND_ALIASES[head] / rest)
    if head.startswith("zhiyin-") and rest:
        # `zhiyin-boot/container/` → `zhiyin-boot/zhiyin_boot/container/`
        candidates.append(TEMPLATE_ROOT / head / head.replace("-", "_") / rest)

    for package_dir in _package_dirs():
        candidates.append(package_dir / relative)
        for sub in package_dir.iterdir():
            if sub.is_dir():
                candidates.append(sub / relative)

    for extra in ("data", "tests", "zhiyin-web", "zhiyin-web/src"):
        candidates.append(TEMPLATE_ROOT / extra / relative)

    return any(candidate.exists() for candidate in candidates)


def _looks_like_repo_path(span: str) -> bool:
    """判断一个代码片段是不是"仓库路径引用"，而不是接口路径 / 组件名 / 命令。"""
    if "/" not in span or " " in span:
        return False
    if any(token in span for token in ("*", "{", "}", "<", ">", "|", "…", "...", "=", "@", "::")):
        return False
    if span.startswith(("/", "http", "GET", "POST", "PUT", "DELETE", "PATCH")):
        return False
    if not re.fullmatch(r"[A-Za-z0-9_./\-]+", span):
        return False
    # 只认"能定位"的三种形态，避免把组件名（`home/TaskCardGroup`）与接口段
    # （`task/enter`）当成文件路径：
    #   ① 带文件扩展名；② 至少两段的目录（`data/registry/`）；
    #   ③ 带仓库根前缀的路径（`zhiyin-src/...`）。
    # 单个叶子目录（目录树里的 `minio/`、`local/`）无法判断父目录，不算。
    has_inner_slash = "/" in span.rstrip("/")
    if span.endswith(_PATH_EXTENSIONS):
        return True
    if span.endswith("/") and has_inner_slash:
        return True
    return span.startswith(
        ("docs/", "zhiyin-src/", "prototype/", "tests/", "data/", ".github/")
    )


def _path_references(text: str) -> set[str]:
    """取出一段文本里的路径引用：行内代码片段 + 围栏代码块（目录树 / 流程图里也可能写路径）。"""
    spans = {match.group(1).strip() for match in re.finditer(r"`([^`]+)`", text)}
    for block in re.findall(r"```[a-zA-Z]*\n([\s\S]*?)```", text):
        for token in re.findall(r"[A-Za-z0-9_][A-Za-z0-9_./\-]*", block):
            spans.add(token)
    return {span for span in spans if _looks_like_repo_path(span)}


@pytest.mark.parametrize("relative_doc", CURRENT_DOCS)
def test_documented_repo_paths_exist(relative_doc: str) -> None:
    """文档里用代码片段引用的仓库路径必须真实存在。

    这条守的是最贵的漂移：文档说"改这个文件"，而文件不在那儿。
    历史名与"按需新增"的计划目录在 `DOCUMENTED_MISSING_PATHS` 里逐条登记理由，
    其余一律必须存在。
    """
    doc = REPO_ROOT / relative_doc
    assert doc.is_file(), f"待检查的文档不存在：{relative_doc}"
    missing: dict[str, str] = {}
    for span in _path_references(doc.read_text(encoding="utf-8")):
        if span in DOCUMENTED_MISSING_PATHS:
            continue
        if not _resolves(span, doc.parent):
            missing[span] = relative_doc

    assert not missing, (
        "以下文档引用了不存在的仓库路径（照错抄风险）：\n  "
        + "\n  ".join(f"{span}（{doc_name}）" for span, doc_name in sorted(missing.items()))
        + "\n若它是历史名或计划中的目录，请登记到 DOCUMENTED_MISSING_PATHS 并写清理由；"
        "否则请把文档改到真实路径。"
    )


def test_capability_counts_in_docs_match_code() -> None:
    """文档里的能力位数量必须与装配清单一致。

    开发指南用一行写死了"15 Gateway / 7 Repository / 1 事务 / 6 编排原语 / 11 服务 /
    3 Worker"。新增一个能力位却忘了改文档，读文档的人就会以为缺口只剩那些——
    这类数字漂移最容易被忽略，也最容易误导排期。
    """
    from zhiyin_boot.container.ports import (
        GATEWAY_PORTS,
        ORCHESTRATION_PORTS,
        REPOSITORY_PORTS,
        SERVICE_PORTS,
        TRANSACTION_PORTS,
        WORKER_PORTS,
    )

    guide = (DOCS_ROOT / "开发指南.md").read_text(encoding="utf-8")
    match = re.search(
        r"（(\d+) Gateway / (\d+) Repository / (\d+) 事务 / (\d+) 编排原语 / (\d+) 服务 / (\d+) Worker）",
        guide,
    )
    assert match, (
        "docs/开发指南.md 里找不到能力位数量那一行（形如"
        "「15 Gateway / 7 Repository / 1 事务 / 6 编排原语 / 11 服务 / 3 Worker」）。"
        "改文案时请保留这行，它是本守卫的锚点。"
    )

    declared = {
        "Gateway": int(match.group(1)),
        "Repository": int(match.group(2)),
        "事务": int(match.group(3)),
        "编排原语": int(match.group(4)),
        "服务": int(match.group(5)),
        "Worker": int(match.group(6)),
    }
    actual = {
        "Gateway": len(GATEWAY_PORTS),
        "Repository": len(REPOSITORY_PORTS),
        "事务": len(TRANSACTION_PORTS),
        "编排原语": len(ORCHESTRATION_PORTS),
        "服务": len(SERVICE_PORTS),
        "Worker": len(WORKER_PORTS),
    }
    drift = {
        key: f"文档 {declared[key]} / 代码 {actual[key]}"
        for key in actual
        if declared[key] != actual[key]
    }
    assert not drift, f"docs/开发指南.md 的能力位数量与 container/ports.py 不一致：{drift}"


def test_gate_manual_paths_exist() -> None:
    """门禁 JSON 的 manual 项里提到的目录必须存在。

    此前 `--check --phase=2` 的退出条件写着"`tests/e2e/` 主路径通过"，而该目录不存在——
    门禁引用了一个不存在的验收落点。这里把"门禁提到的目录必须真实"钉住。
    """
    gates = json.loads((REGISTRY_DIR / "assembly_gates.json").read_text(encoding="utf-8"))
    referenced: set[str] = set()
    for gate in gates.get("items", []):
        for text in gate.get("manual", []) or []:
            # manual 是自然语言（可能带反引号也可能不带），因此按"像目录的 token"提取：
            # 只认 ASCII 路径字符且以 `/` 结尾的片段，避免把中文短语当成路径。
            for span in re.findall(r"[A-Za-z0-9_][A-Za-z0-9_./\-]*/", str(text)):
                if "/" in span:
                    referenced.add(span)

    assert referenced, "门禁里应当有可解析的目录引用（如 tests/e2e/）"
    missing = sorted(
        span
        for span in referenced
        if span not in DOCUMENTED_MISSING_PATHS and not _resolves(span, TEMPLATE_ROOT)
    )
    assert not missing, f"门禁引用了不存在的目录：{missing}"


# --------------------------------------------------------------------------
# 6. "唯一当前状态"标记（防止版本膨胀后读者/AI 不知道读哪份）
# --------------------------------------------------------------------------

FINAL_ASSESSMENT = "docs/评审/职引-架构与结构评估-最终版.md"
CURRENT_STATE_MARKER = 'CURRENT_STATE = "职引-架构与结构评估-最终版.md"'
DEPRECATED_ASSESSMENTS = (
    "docs/评审/职引-架构与代码结构评估-v1.0.md",
    "docs/评审/职引-架构外壳完整度评估-v1.1.md",
    "docs/评审/职引-架构外壳完整度评估-v1.2.md",
)


def test_exactly_one_current_assessment() -> None:
    """仓库里只能有一份文档自称"当前状态"。

    多份版本化评估最容易造成"AI/新人读错版本"：两份都自称 current，
    读者只能靠日期猜。这里用一条机器可判的标记把"谁是当前"钉死，
    历史文档必须降级为"已废弃"，否则本测试失败。
    """
    final = REPO_ROOT / FINAL_ASSESSMENT
    assert final.is_file(), f"缺少唯一当前评估：{FINAL_ASSESSMENT}"

    carriers = [
        path
        for path in DOCS_ROOT.rglob("*.md")
        if CURRENT_STATE_MARKER in path.read_text(encoding="utf-8")
    ]
    assert carriers == [final], (
        "「当前状态」标记只应出现在最终版一份文档里：\n"
        + "\n".join(str(path.relative_to(REPO_ROOT)) for path in carriers)
    )


@pytest.mark.parametrize("relative", DEPRECATED_ASSESSMENTS)
def test_historical_assessments_are_marked_deprecated(relative: str) -> None:
    """历史评估必须在顶部明确"已废弃"并指向最终版。

    否则读者会把它当成现状，又或者 AI 检索到旧的数字/路径去改代码。
    """
    doc = REPO_ROOT / relative
    assert doc.is_file(), f"历史评估缺失：{relative}"
    text = doc.read_text(encoding="utf-8")
    assert "已废弃" in text, f"{relative} 顶部缺少「已废弃」声明"
    assert Path(FINAL_ASSESSMENT).name in text, (
        f"{relative} 未指向最终版 {FINAL_ASSESSMENT}"
    )

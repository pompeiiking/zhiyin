"""接口契约快照守卫：`contracts/openapi.json` 必须等于代码现状。

为什么值得守
------------
前端类型（`zhiyin-web/src/api/types.ts`）由这份快照生成。一旦快照与代码漂移，
前端就会拿到**看起来正确、实际过期**的类型——比没有类型更贵，因为它会让人
相信"字段就是这样"。所以这里把三段链路的第一段钉住：

    代码 == 快照（本文件）   →   快照 == 前端类型（CI: npm run check:api）

第二段跨语言（Node），无法在 pytest 里跑，因此放在 CI 的前端作业里；
两段合起来才覆盖完整的"字段口径对齐"。
"""

from __future__ import annotations

import json
from pathlib import Path

from zhiyin_api.contract import (
    build_openapi_schema,
    contract_is_stale,
    read_contract,
    render_openapi,
    write_contract,
)

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = TEMPLATE_ROOT / "contracts" / "openapi.json"


def test_contract_snapshot_exists() -> None:
    assert CONTRACT_PATH.is_file(), (
        "缺少接口契约快照 contracts/openapi.json（前端类型由它生成）。"
        "请运行：python scripts/export_openapi.py"
    )


def test_contract_snapshot_matches_the_code() -> None:
    """按代码重新构造 OpenAPI，必须与入库快照一致。"""
    committed = read_contract(CONTRACT_PATH)
    live = build_openapi_schema()
    assert committed == live, (
        "接口契约快照与代码不一致。请运行：python scripts/export_openapi.py\n"
        "（若只是改了注释/文档，也请重新生成——快照必须与代码逐字节对应）"
    )


def test_contract_snapshot_is_canonically_formatted() -> None:
    """快照文本必须是规范格式，`--check` 与 CI 的 diff 才有意义。"""
    live = build_openapi_schema()
    assert CONTRACT_PATH.read_text(encoding="utf-8") == render_openapi(live), (
        "快照不是由脚本生成的规范格式（键顺序 / 缩进 / 编码不符）。"
        "请运行：python scripts/export_openapi.py"
    )


def test_snapshot_covers_every_frontend_facing_route() -> None:
    """快照里必须包含前端接口清单引用的全部路由。

    这条与 `tests/test_frontend_alignment.py` 的分工：那里守"前端清单里的 url
    必须能在后端找到"，这里守"快照本身没有漏掉这些路由"——两段都过，
    前端才不会 404 而 OpenAPI 里看着"有这条路由"。
    """
    paths = set(read_contract(CONTRACT_PATH)["paths"])
    for expected in (
        "/api/v1/app/bootstrap",
        "/api/v1/app/sessions",
        "/api/v1/app/task/enter",
        "/api/v1/app/conversation/message",
        "/api/v1/app/workspace",
        "/api/v1/app/report/full-text",
        "/api/v1/app/assets/export",
        "/healthz",
    ):
        assert expected in paths, f"接口契约快照缺少 {expected}"


def test_check_mode_detects_a_modified_snapshot(tmp_path: Path) -> None:
    """`python scripts/export_openapi.py --check` 的判定必须真的会报错。

    守卫自己也要被测：一条"永远返回一致"的 --check 比没有 --check 更糟——
    它会让 CI 显示绿，而漂移照样合入。这里手工篡改一份快照副本，确认能被识别，
    并覆盖三类漂移（多一条接口 / 少一条接口 / DTO 变更）。
    """
    live = build_openapi_schema()

    added = json.loads(json.dumps(live))
    added["paths"]["/api/v1/ghost"] = {"get": {"summary": "不该存在的接口"}}
    target = tmp_path / "added.json"
    target.write_text(render_openapi(added), encoding="utf-8")
    assert any("ghost" in item for item in contract_is_stale(target))

    removed = json.loads(json.dumps(live))
    removed["paths"].pop("/api/v1/app/bootstrap")
    target = tmp_path / "removed.json"
    target.write_text(render_openapi(removed), encoding="utf-8")
    assert any("bootstrap" in item for item in contract_is_stale(target))

    changed = json.loads(json.dumps(live))
    schema = changed["components"]["schemas"]["BootstrapView"]
    schema["properties"]["ghost_field"] = {"title": "Ghost", "type": "string"}
    target = tmp_path / "changed.json"
    target.write_text(render_openapi(changed), encoding="utf-8")
    assert contract_is_stale(target)

    # 反向：由脚本重新生成的快照必须被判为一致（否则 --check 会在 CI 里假红）
    fresh = write_contract(tmp_path / "fresh.json")
    assert contract_is_stale(fresh) == []

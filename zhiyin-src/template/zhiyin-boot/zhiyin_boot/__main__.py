"""启动入口（CLI）。

用法：

    python -m zhiyin_boot                        # 启动本地服务（默认 127.0.0.1:8000）
    python -m zhiyin_boot --port 8080 --reload

    python -m zhiyin_boot --check                # 打印装配报告，不启动服务
    python -m zhiyin_boot --check --strict       # 全绿才算通过（发布门禁）
    python -m zhiyin_boot --check --phase=1      # 只校验里程碑 1 的退出条件
    python -m zhiyin_boot --check --phase=2      # 里程碑 2：业务主干端到端

    python -m zhiyin_boot worker impact --once   # 手动跑一轮某个 Worker
    python -m zhiyin_boot worker active_event    # 独立部署某个 Worker（常驻）

    python -m zhiyin_boot rerank-bridge          # 平台 rerank 协议转换桥（见模块说明）

第一期定位是"本地可启动、可演示、可调试"（§1.1）：读配置 → build_container →
交给 uvicorn。任何装配缺失都在启动时暴露，不做静默降级。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from zhiyin_boot.container import build_container, wire_application
from zhiyin_boot.report import describe_assembly, evaluate_gate, load_gates
from zhiyin_boot.workers import run_forever


def _ensure_utf8_stdout() -> None:
    """Windows 控制台默认可能是 GBK，打印中文装配报告会乱码或抛 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):  # pragma: no cover - 流的类型不支持时忽略
                pass


def _run_check(container, *, phase: int | None, strict: bool) -> int:
    """装配检查。返回进程退出码：0 通过 / 1 未通过。"""
    report = describe_assembly(container)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))

    if phase is not None:
        gates = load_gates(container.settings.local_registry_dir)
        gate = next((item for item in gates if item.phase == phase), None)
        if gate is None:
            print(
                f"未找到里程碑 {phase} 的门禁定义，请检查 "
                "data/registry/assembly_gates.json",
                file=sys.stderr,
            )
            return 2
        result = evaluate_gate(report, gate)
        print(json.dumps({"gate": result.to_dict()}, ensure_ascii=False, indent=2))
        return 0 if result.passed else 1

    # 不带 --phase 时：默认是信息输出（第一期业务尚未实现属预期），
    # 需要 CI 门禁时显式加 --strict（全绿）。
    return 0 if (report.healthy or not strict) else 1


def _run_worker(argv: list[str]) -> int:
    """独立运行一个 Worker：与同进程部署复用同一个 container。"""
    parser = argparse.ArgumentParser(prog="zhiyin worker", description="职引 · Worker")
    parser.add_argument("name", help="Worker 名称（见装配报告 workers 分组）")
    parser.add_argument(
        "--once", action="store_true", help="只跑一轮后退出（可配合外部 cron）"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        help="轮询间隔秒数，默认取 Settings.worker_interval_s",
    )
    args = parser.parse_args(argv)

    container = build_container()
    registry = {getattr(worker, "name", ""): worker for worker in container.workers}
    worker = registry.get(args.name)
    if worker is None:
        available = sorted(name for name in registry if name) or ["（当前未注册任何 Worker）"]
        print(
            f"未找到 Worker：{args.name}；已注册：{', '.join(available)}",
            file=sys.stderr,
        )
        return 2

    if args.once:
        processed = asyncio.run(worker.run_once())
        print(f"{args.name}：本轮处理 {processed} 条")
        return 0

    interval = args.interval or container.settings.worker_interval_s
    asyncio.run(run_forever(worker, interval))
    return 0


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and argv[0] == "worker":
        return _run_worker(argv[1:])

    if argv and argv[0] == "rerank-bridge":
        from zhiyin_boot.rerank_bridge import main as run_bridge

        return run_bridge()

    parser = argparse.ArgumentParser(prog="zhiyin", description="职引 · 第一期服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（默认仅本机）")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="开发热重载")
    parser.add_argument(
        "--check",
        action="store_true",
        help="只做装配检查并打印报告，不启动服务",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="配合 --check：有部件未装配时以非 0 退出（用于 CI 门禁）",
    )
    parser.add_argument(
        "--phase",
        type=int,
        default=None,
        help="配合 --check：只校验某个里程碑的退出条件（见 assembly_gates.json）",
    )
    args = parser.parse_args(argv)

    container = build_container()

    if args.check:
        return _run_check(container, phase=args.phase, strict=args.strict)

    app = wire_application(container)
    try:
        import uvicorn
    except ModuleNotFoundError:  # pragma: no cover - 依赖缺失时给出明确指引
        print(
            "缺少 uvicorn，请先安装运行依赖：pip install -e .[dev]",
            file=sys.stderr,
        )
        return 2

    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

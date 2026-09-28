import argparse
import json
import os
from pathlib import Path
import platform
import secrets
import sys
from typing import Any
from . import __version__
from .commands import Registry
from .context import Manifest
from .engine import Engine
from .errors import EngineError
from .jsonutil import strict_loads
from .store import Access, ReferenceStore
from .telemetry import Telemetry, Scope
from .tokens import available, prepare


def output(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ace", description="Local-first deterministic agent context tools")
    p.add_argument("--state", type=Path, default=Path(".ace-local"), help="Local metric/config directory")
    p.add_argument("--workspace", default="default", help="Trusted host-selected workspace ID")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("diagnostics")
    sub.add_parser("tokenizer-prepare", help="Explicitly download public cl100k vocabulary")
    opt = sub.add_parser("optimize")
    opt.add_argument("file", type=Path)
    opt.add_argument("--format", choices=["auto", "json", "logs", "pytest", "shell", "sql", "code", "stream"], default="auto")
    opt.add_argument("--persist-originals", action="store_true")
    opt.add_argument("--signed", action="store_true")
    opt.add_argument("--exit-status", type=int)
    opt.add_argument("--exact-dataset", action="store_true")
    for name in ["expand", "registry"]:
        cmd = sub.add_parser(name)
        cmd.add_argument("--root", type=Path, default=Path.cwd())
        cmd.add_argument("--suites", type=Path, required=True, help="Trusted local name-to-path JSON map")
        if name == "expand":
            cmd.add_argument("request", type=Path)
    retrieve = sub.add_parser("retrieve")
    retrieve.add_argument("reference")
    context = sub.add_parser("prepare")
    context.add_argument("manifest", type=Path)
    context.add_argument("--task", required=True)
    context.add_argument("--requirements", nargs="+", required=True)
    context.add_argument("--output-contract", required=True)
    bench = sub.add_parser("benchmark")
    bench.add_argument("--repeats", type=int, default=5)
    bench.add_argument("--output", type=Path, default=Path("reports/offline-benchmark.json"))
    demo = sub.add_parser("seed-demo")
    report = sub.add_parser("report")
    report.add_argument("--mode", choices=["real", "demo"], default="real")
    report.add_argument("--benchmark")
    report.add_argument("--output", type=Path)
    dash = sub.add_parser("dashboard")
    dash.add_argument("--port", type=int, default=8765)
    sub.add_parser("cleanup")
    mcp = sub.add_parser("mcp")
    mcp.add_argument("--root", type=Path)
    mcp.add_argument("--suites", type=Path)
    sub.add_parser("offline-agent")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    access = Access("local-cli", frozenset({args.workspace}))
    cache = args.state / "tokenizer"
    try:
        if args.command == "diagnostics":
            tok = available(cache)
            output({"engine_version": __version__, "python": sys.version, "os": platform.platform(), "architecture": platform.machine(), "tokenizer": tok.identity if tok else "Unavailable", "state_path": str(args.state.resolve()), "network_required_for_core": False, "raw_storage_default": "memory_only", "tested_platforms": "See docs/TEST-RESULTS.md; this command reports this environment only"})
        elif args.command == "tokenizer-prepare":
            prepare(cache)
            output({"prepared": "cl100k_base", "path": str(cache), "requires_optional_package": "pip install .[tokens]"})
        elif args.command in {"registry", "expand"}:
            registry = Registry(args.root, strict_loads(args.suites.read_text()))
            output(registry.description() if args.command == "registry" else registry.dry_run(strict_loads(args.request.read_text())))
        elif args.command == "prepare":
            manifest = Manifest.create(strict_loads(args.manifest.read_text()))
            output(manifest.prepare(args.task, args.requirements, args.output_contract))
        elif args.command == "retrieve":
            store = ReferenceStore(args.state/"originals.sqlite3")
            output(store.get(args.workspace, args.reference, access))
            store.close()
        elif args.command == "optimize":
            # CLI is short-lived; reference-dependent views require explicit persistent retention.
            store = ReferenceStore(args.state/"originals.sqlite3" if args.persist_originals else None)
            if args.format == "pytest" and not args.persist_originals:
                from .engine import Optimization
                output(Optimization("passthrough", args.file.read_text(), exit_status=args.exit_status, bypass_reason="CLI retrieval requires --persist-originals; original unchanged").metadata())
            else:
                engine = Engine(args.workspace, access, tokenizer=available(cache), store=store)
                output(engine.optimize(args.file.read_text(), args.format, signed=args.signed, exact_dataset=args.exact_dataset, exit_status=args.exit_status).metadata())
            store.close()
        else:
            db = Telemetry(args.state/"metrics.sqlite3")
            try:
                if args.command == "benchmark":
                    from .benchmark import offline
                    from .reports import report_html
                    report = offline(db, args.workspace, access, available(cache), repeats=args.repeats)
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(json.dumps(report, indent=2))
                    args.output.with_suffix(".html").write_text(report_html(report))
                    output({"report": str(args.output), "html": str(args.output.with_suffix('.html')), "all_fidelity_passed": report["all_fidelity_passed"], "rows": report["rows"]})
                    return 0 if report["all_fidelity_passed"] else 1
                elif args.command == "seed-demo":
                    from .benchmark import seed_demo
                    seed_demo(db, args.workspace, access)
                    output({"seeded": "demo mode only", "real_data_modified": False})
                elif args.command == "report":
                    from .metrics import summarize
                    from .reports import report_html, export_csv
                    scope = Scope(args.workspace, args.mode, filters={"benchmark": args.benchmark} if args.benchmark else {})
                    report = summarize(db.events(scope, access), scope, db.settings(args.workspace, access))
                    if args.output:
                        value = report_html(report) if args.output.suffix == ".html" else export_csv(report) if args.output.suffix == ".csv" else json.dumps(report, indent=2)
                        args.output.parent.mkdir(parents=True, exist_ok=True)
                        args.output.write_text(value)
                    else:
                        output(report)
                elif args.command == "dashboard":
                    from .dashboard import DashboardServer
                    secret = os.environ.get("ACE_DASHBOARD_SECRET") or secrets.token_urlsafe(24)
                    server = DashboardServer(args.port, db, access, args.workspace, secret)
                    print(f"Local dashboard: http://127.0.0.1:{server.server_port}\nLogin secret: {secret}\nDo not put this secret in a URL.", flush=True)
                    try:
                        server.serve_forever(poll_interval=.3)
                    except KeyboardInterrupt:
                        pass
                    finally:
                        server.server_close()
                elif args.command == "cleanup":
                    originals_removed = 0
                    if (args.state/"originals.sqlite3").exists():
                        originals = ReferenceStore(args.state/"originals.sqlite3")
                        originals_removed = originals.cleanup()
                        originals.close()
                    output({"metric_events_removed": db.cleanup(), "expired_originals_removed": originals_removed})
                elif args.command == "mcp":
                    from .mcp import serve
                    if bool(args.root) != bool(args.suites):
                        raise ValueError("MCP root and suites must be supplied together by the host")
                    mcp_registry = Registry(args.root, strict_loads(args.suites.read_text())) if args.root else None
                    serve(Engine(args.workspace, access, tokenizer=available(cache)), db, registry=mcp_registry)
                elif args.command == "offline-agent":
                    from .adapters import offline_agent
                    output(offline_agent(db, args.workspace, access, available(cache)))
            finally:
                db.close()
    except (EngineError, ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    return 0

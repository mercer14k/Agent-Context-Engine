"""Offline replay measures deterministic fidelity and payload counts, not model quality."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import sys
import time
from uuid import uuid4
from typing import Any
from . import __version__
from .engine import Engine, Optimization
from .fixtures import story_manifest, inventory, inventory_result, test_log
from .jsonutil import compact_json, dumps, strict_loads
from .store import Access
from .telemetry import Telemetry, Scope
from .tokens import Tokenizer
from .transforms import restore_logs
from .metrics import summarize


def offline(db: Telemetry, workspace: str, access: Access, tokenizer: Tokenizer | None, *, repeats: int = 5) -> dict[str, Any]:
    if not 1 <= repeats <= 100:
        raise ValueError("repeats must be 1–100")
    batch = uuid4().hex[:12]
    manifest = story_manifest()
    handoff = manifest.prepare("Validate narrative structure", ["heroes", "nodes"], "Return separate hero/chapter/node assertions")
    cases = [("coding-agent", test_log(), "logs"), ("inventory-reconciliation", inventory(), "json"),
             ("agent-handoff", json.dumps(handoff, indent=2, ensure_ascii=False), "json"), ("already-compact", '{"ok":true}', "json")]
    records: list[dict[str, Any]] = []
    order = [(case, arm, repeat) for case in cases for arm in ("off", "native", "engine") for repeat in range(repeats)]
    random.Random(217).shuffle(order)
    for (name, text, fmt), arm, repeat in order:
        run_id = uuid4().hex
        sink = db.sink(workspace, "real", run_id, access)
        start = time.time()
        tick = time.perf_counter()
        engine = Engine(workspace, access, tokenizer=tokenizer, emit=sink)
        original = Optimization("passthrough", text).message()
        if arm == "engine":
            result = engine.optimize(text, fmt, exact_dataset=name == "inventory-reconciliation")
            candidate = result.content
            envelope = result.message()
            method = result.method
            bypass = result.bypass_reason
        else:
            candidate = compact_json(text) if arm == "native" and fmt == "json" else text
            envelope = Optimization("native_json_minify" if candidate != text else "passthrough", candidate).message()
            method = "native_json_minify" if candidate != text else "passthrough"
            bypass = None
            sink("optimization", {"method": method, "original_tokens": tokenizer.count(original) if tokenizer else None,
                "optimized_tokens": tokenizer.count(envelope) if tokenizer else None, "tokenizer": tokenizer.identity if tokenizer else "Unavailable",
                "duration_ms": (time.perf_counter()-tick)*1000, "bypass_reason": bypass,
                "evidence": "Tokenizer-counted payload" if tokenizer else "Unavailable"})
        if fmt == "logs":
            faithful = (restore_logs(candidate) if method == "adjacent_log_runs" else candidate) == text
        elif name == "inventory-reconciliation":
            expected = {"items": 40, "closing_total": 4200, "valuation": "518.518513851851851384200", "mismatches": []}
            faithful = inventory_result(candidate) == expected
        else:
            faithful = strict_loads(candidate, decimals=True) == strict_loads(text, decimals=True)
            if name == "agent-handoff":
                req = {r["id"]: r for r in strict_loads(candidate)["requirements"]}
                faithful = faithful and all(k in req for k in ("heroes", "chapters", "nodes", "safety")) and req["nodes"]["depends_on"] == ["chapters"]
        end = time.time()
        sink("run", {"task": name, "benchmark": name, "arm": arm, "pair_id": f"{batch}-{name}-{repeat}", "agent": "offline-replay", "provider": "none", "model": "none",
            "tokenizer": tokenizer.identity if tokenizer else "Unavailable", "config": "offline-v1-no-model-no-cache", "engine_version": __version__, "method": method,
            "start": start, "end": end, "success": None, "expected_requests": 0, "evidence": "Tokenizer-counted payload"})
        sink("check", {"validator": "exact-fixture-v1", "category": "transform_fidelity", "valid": faithful, "failure_code": None if faithful else "fixture_mismatch", "evidence": "Deterministic assertion"})
        records.append({"run_id": run_id, "fixture": name, "arm": arm, "repeat": repeat, "method": method,
            "original_tokens": tokenizer.count(original) if tokenizer else None, "visible_tokens": tokenizer.count(envelope) if tokenizer else None,
            "fidelity": faithful, "duration_ms": (end-start)*1000, "bypass": bypass,
            "fixture_sha256": hashlib.sha256(text.encode()).hexdigest()})
        engine.store.close()
    rows = []
    for name, _, _ in cases:
        for arm in ("off", "native", "engine"):
            group = [r for r in records if r["fixture"] == name and r["arm"] == arm]
            rows.append({"fixture": name, "arm": arm, "n": len(group), "visible_tokens": group[0]["visible_tokens"],
                "fidelity_passed": sum(r["fidelity"] for r in group), "median_ms": statistics.median(r["duration_ms"] for r in group),
                "min_ms": min(r["duration_ms"] for r in group), "max_ms": max(r["duration_ms"] for r in group)})
    return {"schema": "ace.benchmark.v1", "mode": "offline-replay", "batch": batch, "engine_version": __version__, "python": sys.version,
        "os": platform.platform(), "architecture": platform.machine(), "tokenizer": tokenizer.identity if tokenizer else "Unavailable",
        "scope": "Model-visible tool-result envelope including role/trust/reference wrapper; no provider calls", "repeats": repeats, "seed": 217,
        "cache_conditions": "No provider cache, models, compression calls, or live task attempts. Native JSON is already minified.",
        "limitations": ["Offline fidelity is not live task success", "Model input/output savings, provider usage, and cost per successful agent task are unavailable", "Fixture token counts exclude full conversation; workflow fields remain unavailable", "No competitor configuration exercised", "No confidence interval for model quality: no live sample"],
        "rows": rows, "records": records, "all_fidelity_passed": all(r["fidelity"] for r in records)}


def seed_demo(db: Telemetry, workspace: str, access: Access) -> None:
    """Idempotent separate mode; every request is permanently labeled Simulated."""
    scenarios = ["arithmetic-25-percent", "negative-savings", "lost-cache-benefit", "failed-quality", "missing-usage", "retrieval-overhead", "no-op"]
    base_time = time.time()-6*3600
    for index, scenario in enumerate(scenarios):
        for arm in ("off", "native", "engine"):
            rid = f"demo-{scenario}-{arm}"
            sink = db.sink(workspace, "demo", rid, access)
            start = base_time + index * 1800
            i, o, overhead, cached = 10000, 2000, 0, 0
            if arm == "engine":
                i = 6000
                overhead = 1000 if scenario in {"arithmetic-25-percent", "retrieval-overhead"} else 0
                if scenario == "negative-savings":
                    i, overhead = 10000, 2000
                if scenario == "no-op":
                    i = 10000
            if scenario == "lost-cache-benefit" and arm != "engine":
                cached = 9500
            expected = 2 if overhead else 1
            sink("run", {"task": scenario, "agent": "synthetic-agent", "provider": "simulated", "model": "fixture-model", "tokenizer": "fixture-counts-v1", "benchmark": scenario, "arm": arm, "pair_id": scenario,
                "config": "synthetic-v1", "engine_version": __version__, "method": "json_whitespace" if arm == "engine" else "passthrough", "start": start, "end": start+8+index+(2 if arm == "engine" else 0),
                "success": False if scenario == "failed-quality" and arm == "engine" else None if scenario == "missing-usage" else True,
                "validator": "synthetic-exact-outcome-v1", "expected_requests": expected, "evidence": "Simulated", "price_version": "demo-v1"}, event_id=rid+"-run", timestamp=start)
            usage = {"provider": "simulated", "model": "fixture-model", "input_tokens": None if scenario == "missing-usage" else i, "output_tokens": o, "cached_input_tokens": cached, "cache_write_tokens": 0,
                "reasoning_tokens": 500, "tool_cost": 0, "final": True, "purpose": "operation", "evidence": "Simulated", "price_version": "demo-v1", "provider_wait_ms": 7000}
            # Cumulative SDK snapshots and duplicate terminal deliveries count once.
            sink("usage", {**usage, "input_tokens": 100, "output_tokens": 0, "final": False, "cached_input_tokens": 0}, event_id=rid+"-partial", timestamp=start+.1, request_id=rid+"-req", revision=0)
            sink("usage", usage, event_id=rid+"-usage", timestamp=start+1, request_id=rid+"-req", revision=1)
            sink("usage", usage, event_id=rid+"-duplicate", timestamp=start+2, request_id=rid+"-req", revision=1)
            if overhead:
                # 1000 separate retrieval-context INPUT tokens; never included in the 6000 main input.
                sink("usage", {**usage, "input_tokens": overhead, "output_tokens": 0, "reasoning_tokens": 0, "cached_input_tokens": 0}, event_id=rid+"-overhead", timestamp=start+3, request_id=rid+"-overhead-req", revision=1)
                sink("retrieval", {"valid": True, "duration_ms": 1}, event_id=rid+"-retrieval", timestamp=start+2)
            if scenario == "failed-quality":
                sink("check", {"validator": "synthetic-exact-outcome-v1", "category": "end_task", "valid": arm != "engine", "failure_code": "inventory_mismatch" if arm == "engine" else None, "evidence": "Simulated"}, event_id=rid+"-check")
            if scenario == "negative-savings" and arm == "engine":
                sink("retry", {"reason_code": "synthetic_provider_retry"}, event_id=rid+"-retry")
            sink("optimization", {"method": "json_whitespace" if arm == "engine" else "passthrough", "original_tokens": 10000, "optimized_tokens": i, "tokenizer": "fixture-counts-v1", "duration_ms": .3+index/10, "bypass_reason": "Already compact" if scenario == "no-op" else None, "evidence": "Simulated"}, event_id=rid+"-optimization")
            sink("command", {"operation": "run_tests", "schema_version": "1", "registry_version": "synthetic-v1", "valid": True, "executed": False, "exit_code": None, "arguments": "suite=auth", "invocation": "python -m pytest", "compact_tokens": 50, "native_tokens": 34, "duration_ms": .1}, event_id=rid+"-command")

"""Single source of truth for SDK, CLI, dashboard, and exports."""
from collections import defaultdict
from dataclasses import asdict
from decimal import Decimal
import math
import statistics
import time
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .errors import ValidationError
from .telemetry import Scope

DEFINITIONS = {
    "payload_reduction": "100 × (sum original envelope tokens − sum optimized envelope tokens) / sum original envelope tokens; tokenizer strata kept separate. Not API usage.",
    "workflow_reduction": "100 × (matched baseline total tokens − matched engine total tokens) / matched baseline total tokens. Every model request counted once, including retrieval and retry calls.",
    "success_rate": "Verified successful tasks / evaluated tasks. Unknown outcomes excluded from denominator and disclosed.",
    "cost_per_success": "All attributable cohort cost including failures and retries / verified successes. Incomplete outcomes make this provisional; incomplete prices make it unavailable.",
    "cost_improvement": "100 × (baseline cost per success − engine cost per success) / baseline cost per success for matched cohorts only.",
    "duration": "Task end − task start. Concurrent spans are not summed. Percentiles computed from individual durations by linear interpolation.",
    "cost": "Calculated usage cost, not an invoice. Input counts include cache reads/writes as disjoint subsets; reasoning is already included in output. Price rules explicitly versioned per provider/model. Judge cost is separate.",
}


def fraction(n: float, d: float) -> float | None:
    return n / d if d else None


def reduction(before: float, after: float) -> float | None:
    return 100 * (before - after) / before if before > 0 else None


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    location = (len(values) - 1) * q
    low, high = math.floor(location), math.ceil(location)
    return values[low] + (values[high] - values[low]) * (location - low)


def validate_settings(value: dict[str, Any]) -> None:
    if set(value) != {"retention_days", "timezone", "prices", "alerts"}:
        raise ValidationError("Invalid settings fields")
    if type(value["retention_days"]) is not int or not 1 <= value["retention_days"] <= 3650:
        raise ValidationError("Retention must be 1–3650 days")
    try:
        if value["timezone"] != "UTC":
            ZoneInfo(value["timezone"])
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ValidationError("Unknown display timezone") from exc
    if not isinstance(value["prices"], list):
        raise ValidationError("Prices must be a list")
    price_keys = {"provider", "model", "version", "currency", "source", "effective_date", "input", "cached_input", "cache_write", "output", "discount", "rule"}
    seen = set()
    for p in value["prices"]:
        if set(p) != price_keys or p["rule"] != "inclusive-input-disjoint-cache-v1":
            raise ValidationError("Unknown price schema/rule")
        for k in ("input", "cached_input", "cache_write", "output", "discount"):
            try:
                n = Decimal(str(p[k]))
            except Exception as exc:
                raise ValidationError("Invalid price") from exc
            if not n.is_finite() or n < 0 or (k == "discount" and n > 1):
                raise ValidationError("Invalid price")
        key = (p["provider"], p["model"], p["version"])
        if key in seen:
            raise ValidationError("Duplicate price version")
        seen.add(key)
    required_alerts = {"min_samples", "success_rate_below", "retry_rate_above", "latency_ms_above", "cost_per_success_above", "retrieval_failure_rate_above", "validation_failure_rate_above", "coverage_below"}
    if not isinstance(value["alerts"], dict) or set(value["alerts"]) != required_alerts:
        raise ValidationError("Invalid alert thresholds")
    for key, number in value["alerts"].items():
        if type(number) not in {int, float} or not math.isfinite(number) or number < 0:
            raise ValidationError("Invalid threshold")
        if key == "min_samples" and (type(number) is not int or number < 1):
            raise ValidationError("min_samples must be a positive integer")


def usage_cost(u: dict[str, Any], prices: list[dict[str, Any]]) -> dict[str, Any]:
    price = next((p for p in prices if (p["provider"], p["model"], p["version"]) == (u.get("provider"), u.get("model"), u.get("price_version"))), None)
    if not price:
        return {"total": None, "reason": "Pricing unavailable", "input": None, "output": None, "currency": None}
    i, o, read, write = (u.get(k) for k in ("input_tokens", "output_tokens", "cached_input_tokens", "cache_write_tokens"))
    scale = Decimal(1_000_000)
    discount = Decimal(1) - Decimal(str(price["discount"]))
    input_known = i is not None and read is not None and write is not None and read + write <= i
    input_cost = ((Decimal(i-read-write)*Decimal(str(price["input"])) + Decimal(read)*Decimal(str(price["cached_input"])) + Decimal(write)*Decimal(str(price["cache_write"]))) / scale * discount) if i is not None and read is not None and write is not None and input_known else None
    output_cost = Decimal(o)*Decimal(str(price["output"])) / scale * discount if o is not None else None
    tool = u.get("tool_cost")
    complete = input_cost is not None and output_cost is not None and tool is not None
    partial = sum((v for v in (input_cost, output_cost, Decimal(str(tool)) if tool is not None else None) if v is not None), Decimal(0))
    return {"input": float(input_cost) if input_cost is not None else None, "output": float(output_cost) if output_cost is not None else None,
            "total": float(partial) if complete else None, "known_partial": float(partial), "currency": price["currency"], "version": price["version"],
            "reason": None if complete else "Usage, cache categories, or tool-service cost incomplete"}



def summarize(events: list[dict[str, Any]], scope: Scope, settings: dict[str, Any]) -> dict[str, Any]:
    if scope.mode == "demo":
        from .fixtures import DEMO_PRICE
        settings = {**settings, "prices": [DEMO_PRICE.copy()]}
    run_events: dict[str, dict[str, Any]] = {}
    for e in sorted(events, key=lambda x: (x["revision"], x["timestamp"])):
        if e["kind"] == "run":
            run_events[e["run_id"]] = e
    # Cumulative updates replace older revisions; equal conflicting revisions invalidate usage.
    requests: dict[tuple[str, str], dict[str, Any]] = {}
    conflicts: set[tuple[str, str]] = set()
    for e in events:
        if e["kind"] != "usage":
            continue
        key = (e["data"].get("provider", ""), e["request_id"])
        previous = requests.get(key)
        if previous and (previous["run_id"] != e["run_id"] or (previous["revision"] == e["revision"] and previous["data"] != e["data"])):
            conflicts.add(key)
        if previous is None or e["revision"] > previous["revision"]:
            requests[key] = e
    runs = []
    for run_id, event in run_events.items():
        data = event["data"]
        own = [e for e in events if e["run_id"] == run_id]
        calls = [e for e in requests.values() if e["run_id"] == run_id]
        costs = [usage_cost(e["data"], settings["prices"]) for e in calls]
        currencies = {c["currency"] for c in costs if c.get("currency")}
        complete = bool(calls) and data.get("expected_requests") == len(calls) and all(e["data"].get("final") is True and e["data"].get("input_tokens") is not None and e["data"].get("output_tokens") is not None and (e["data"].get("provider", ""), e["request_id"]) not in conflicts for e in calls)
        cost_complete = complete and len(currencies) == 1 and all(c["total"] is not None for c in costs)
        input_known = sum(e["data"].get("input_tokens") or 0 for e in calls)
        output_known = sum(e["data"].get("output_tokens") or 0 for e in calls)
        duration = (data["end"]-data["start"])*1000 if data.get("end") is not None and data.get("start") is not None and data["end"] >= data["start"] else None
        eval_valid = data.get("success") is not None and bool(data.get("validator"))
        op_cost = sum(c.get("total") or c.get("known_partial", 0) for e, c in zip(calls, costs) if e["data"].get("purpose") != "evaluation") if len(currencies) == 1 else None
        judge_cost = sum(c.get("total") or c.get("known_partial", 0) for e, c in zip(calls, costs) if e["data"].get("purpose") == "evaluation") if len(currencies) == 1 else None
        runs.append({"run_id": run_id, **data, "success": data.get("success") if eval_valid else None,
            "input_tokens": input_known if complete else None, "output_tokens": output_known if complete else None,
            "known_partial_tokens": input_known+output_known, "total_tokens": input_known+output_known if complete else None,
            "usage_complete": complete, "requests": len(calls), "cost": op_cost+judge_cost if cost_complete and op_cost is not None and judge_cost is not None else None,
            "known_partial_cost": op_cost+judge_cost if op_cost is not None and judge_cost is not None else None,
            "operational_cost": op_cost if cost_complete else None, "evaluation_cost": judge_cost if cost_complete else None,
            "currency": next(iter(currencies)) if len(currencies) == 1 else None,
            "input_cost": sum(c["input"] for c in costs) if cost_complete else None,
            "output_cost": sum(c["output"] for c in costs) if cost_complete else None,
            "duration_ms": duration, "engine_ms": sum(e["data"].get("duration_ms", 0) for e in own if e["kind"] == "optimization"),
            "retries": sum(e["kind"] == "retry" for e in own), "retrievals": sum(e["kind"] == "retrieval" for e in own),
            "bypasses": sum(bool(e["data"].get("bypass_reason")) for e in own if e["kind"] == "optimization"),
            "measurement_sources": sorted({e["data"].get("evidence", "Unavailable") for e in calls})})
    currencies = {r["currency"] for r in runs if r["currency"]}
    compatible_money = len(currencies) == 1
    successes = sum(r["success"] is True for r in runs)
    evaluated = sum(r["success"] is not None for r in runs)
    cost_complete = bool(runs) and compatible_money and all(r["cost"] is not None for r in runs)
    durations = [r["duration_ms"] for r in runs if r["duration_ms"] is not None]
    payload: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in events:
        if e["kind"] == "optimization":
            payload[e["data"].get("tokenizer", "Unavailable")].append(e["data"])
    payload_stats = []
    for tokenizer, items in payload.items():
        known = [i for i in items if i.get("original_tokens") is not None and i.get("optimized_tokens") is not None]
        before = sum(i["original_tokens"] for i in known)
        after = sum(i["optimized_tokens"] for i in known)
        payload_stats.append({"tokenizer": tokenizer, "sample_size": len(items), "measured": len(known), "original": before if known else None, "optimized": after if known else None, "reduction_pct": reduction(before, after) if len(known) == len(items) else None, "evidence": "Simulated" if scope.mode == "demo" else "Tokenizer-counted payload"})
    # Compare only uniquely paired arms within workload/model/tokenizer/config/evidence strata.
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for r in runs:
        if r.get("pair_id"):
            group_key = tuple(r.get(k) for k in ("benchmark", "provider", "model", "tokenizer", "config", "pair_id")) + (tuple(r["measurement_sources"]), r.get("price_version"))
            groups[group_key].append(r)
    pairs = []
    for group_key, group in groups.items():
        for baseline in ("off", "native"):
            base = [r for r in group if r.get("arm") == baseline]
            engine = [r for r in group if r.get("arm") == "engine"]
            if len(base) != 1 or len(engine) != 1:
                continue
            b, o = base[0], engine[0]
            before, after = b["total_tokens"], o["total_tokens"]
            pairs.append({"pair_id": group_key[5], "benchmark": group_key[0], "stratum": list(group_key[:5]), "baseline_arm": baseline,
                          "baseline_run": b["run_id"], "engine_run": o["run_id"], "baseline_tokens": before, "engine_tokens": after,
                          "reduction_pct": reduction(before, after) if before is not None and after is not None else None,
                          "evidence": "Simulated" if scope.mode == "demo" else "Paired benchmark", "measurement_sources": b["measurement_sources"],
                          "reason": None if before is not None and after is not None else "Complete workflow usage unavailable",
                          "baseline_success": b["success"], "engine_success": o["success"], "baseline_cost": b["cost"], "engine_cost": o["cost"]})
    comparisons = []
    strata: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in pairs:
        strata[str(p["stratum"])+p["baseline_arm"]+str(p["measurement_sources"])].append(p)
    for group in strata.values():
        complete = all(p["baseline_tokens"] is not None and p["engine_tokens"] is not None for p in group)
        before = sum(p["baseline_tokens"] for p in group) if complete else None
        after = sum(p["engine_tokens"] for p in group) if complete else None
        money = all(p["baseline_cost"] is not None and p["engine_cost"] is not None for p in group) and compatible_money
        bs = sum(p["baseline_success"] is True for p in group)
        os = sum(p["engine_success"] is True for p in group)
        bcps = fraction(sum(p["baseline_cost"] for p in group), bs) if money else None
        ocps = fraction(sum(p["engine_cost"] for p in group), os) if money else None
        comparisons.append({"stratum": group[0]["stratum"], "baseline_arm": group[0]["baseline_arm"], "sample_size": len(group), "baseline_tokens": before, "engine_tokens": after,
            "reduction_pct": reduction(before, after) if before is not None and after is not None else None, "cost_improvement_pct": reduction(bcps, ocps) if bcps is not None and ocps is not None else None,
            "provisional": any(p["baseline_success"] is None or p["engine_success"] is None for p in group), "evidence": group[0]["evidence"], "measurement_sources": group[0]["measurement_sources"]})
    # Never combine token totals across model/tokenizer/evidence families.
    token_strata = {(r.get("provider"), r.get("model"), r.get("tokenizer"), tuple(r["measurement_sources"])) for r in runs}
    usage_complete = bool(runs) and len(token_strata) == 1 and all(r["usage_complete"] for r in runs)
    cost_total = sum(r["cost"] for r in runs) if cost_complete else None
    result = {"scope": asdict(scope), "mode_label": "SYNTHETIC DEMONSTRATION — not performance evidence" if scope.mode == "demo" else "Real local telemetry",
        "sample_size": len(runs), "evaluated": evaluated, "unevaluated": len(runs)-evaluated, "successes": successes,
        "outcome_sources": sorted({r.get("evidence", "Unavailable") for r in runs if r["success"] is not None}),
        "success_rate": fraction(successes, evaluated), "provisional": evaluated < len(runs), "usage_coverage": fraction(sum(r["usage_complete"] for r in runs), len(runs)),
        "input_tokens": sum(r["input_tokens"] for r in runs) if usage_complete else None, "output_tokens": sum(r["output_tokens"] for r in runs) if usage_complete else None,
        "usage_reason": None if usage_complete else "No complete compatible workflow cohort; inspect runs/strata",
        "cost": cost_total, "cost_reason": None if cost_complete else "Pricing, usage, currency, or cohort incomplete",
        "known_partial_cost": sum(r["known_partial_cost"] or 0 for r in runs) if compatible_money and any(r["known_partial_cost"] is not None for r in runs) else None,
        "currency": next(iter(currencies)) if compatible_money else None, "cost_per_success": fraction(cost_total, successes) if cost_total is not None else None,
        "operational_cost": sum(r["operational_cost"] for r in runs) if cost_complete else None,
        "evaluation_cost": sum(r["evaluation_cost"] for r in runs) if cost_complete else None,
        "input_cost": sum(r["input_cost"] for r in runs) if cost_complete else None,
        "output_cost": sum(r["output_cost"] for r in runs) if cost_complete else None,
        "duration_median_ms": statistics.median(durations) if durations else None, "duration_p95_ms": percentile(durations, .95), "duration_samples": len(durations),
        "engine_ms": sum(r["engine_ms"] for r in runs), "failures": evaluated-successes,
        "retries": sum(r["retries"] for r in runs), "retrievals": sum(r["retrievals"] for r in runs), "bypasses": sum(r["bypasses"] for r in runs),
        "conflicting_requests": len(conflicts), "last_update": max((e["received"] for e in events), default=None),
        "runs": sorted(runs, key=lambda r: r.get("start", 0), reverse=True), "payload": payload_stats, "pairs": pairs, "comparisons": comparisons,
        "commands": [e for e in events if e["kind"] == "command"], "checks": [e for e in events if e["kind"] == "check"], "definitions": DEFINITIONS,
        "prices": settings["prices"], "timezone": settings["timezone"], "generated_at": time.time()}
    result["alerts"] = alerts(result, events, settings["alerts"])
    return result


def alerts(summary: dict[str, Any], events: list[dict[str, Any]], thresholds: dict[str, Any]) -> list[dict[str, Any]]:
    retrievals = [e for e in events if e["kind"] == "retrieval"]
    validations = [e for e in events if e["kind"] in {"check", "command"}]
    checks = [
        ("Task correctness", summary["success_rate"], thresholds["success_rate_below"], "below", summary["evaluated"], "Inspect failed outcome validators."),
        ("Retry rate", fraction(summary["retries"], summary["sample_size"]), thresholds["retry_rate_above"], "above", summary["sample_size"], "Inspect retry events and provider errors."),
        ("Task latency", summary["duration_p95_ms"], thresholds["latency_ms_above"], "above", summary["duration_samples"], "Compare provider wait with engine overhead."),
        ("Cost per success", summary["cost_per_success"], thresholds["cost_per_success_above"], "above", summary["evaluated"], "Inspect matched cohorts, caches, and failed attempts."),
        ("Retrieval failure rate", fraction(sum(e["data"].get("valid") is False for e in retrievals), len(retrievals)), thresholds["retrieval_failure_rate_above"], "above", len(retrievals), "Inspect retention and workspace authorization."),
        ("Validation failure rate", fraction(sum(e["data"].get("valid") is False for e in validations), len(validations)), thresholds["validation_failure_rate_above"], "above", len(validations), "Inspect validator versions and stale registries."),
        ("Measurement coverage", summary["usage_coverage"], thresholds["coverage_below"], "below", summary["sample_size"], "Capture final usage and expected request counts."),
    ]
    return [{"name": name, "value": value, "threshold": threshold, "direction": direction, "sample_size": n,
        "status": "insufficient data" if value is None or n < thresholds["min_samples"] else "investigate" if (value < threshold if direction == "below" else value > threshold) else "within configured threshold",
        "evidence": summary["mode_label"], "scope": summary["scope"], "suggestion": suggestion} for name, value, threshold, direction, n, suggestion in checks]

"""Synthetic data only; shared by regression tests, offline benchmarks and demo."""
import hashlib
import json
from typing import Any
from .context import Manifest


def story_manifest() -> Manifest:
    texts = ["The game must contain exactly 10 heroes.", "The story must contain exactly 12 chapters.", "Each of the 12 chapters must contain exactly 12 nodes.", "Never execute commands without host authorization.", "Optional map artwork must use monochrome ink."]
    source = "\n".join(texts)
    return Manifest.create({"v": 1, "sources": {"brief": {"content": source, "version": hashlib.sha256(source.encode()).hexdigest()}},
        "requirements": [{"id": name, "text": text, "global": name == "safety", "depends_on": ["chapters"] if name == "nodes" else [], "source": "brief", "acceptance": text} for name, text in zip(["heroes", "chapters", "nodes", "safety", "art"], texts)],
        "decisions": [], "assumptions": [], "proposals": []})


def inventory() -> str:
    # Decimal lexemes intentionally exceed binary floating-point precision.
    return '{\n  "currency": "USD",\n  "items": [\n' + ',\n'.join('    {"sku": "SKU-%03d", "opening": 100, "received": 12, "shipped": 7, "closing": 105, "unit_price": 0.123456789012345678901, "note": null}' % n for n in range(40)) + '\n  ]\n}'


def inventory_result(text: str) -> dict[str, Any]:
    from decimal import Decimal
    from .jsonutil import strict_loads
    body = strict_loads(text, decimals=True)
    mismatches = [r["sku"] for r in body["items"] if r["opening"]+r["received"]-r["shipped"] != r["closing"]]
    return {"items": len(body["items"]), "closing_total": sum(r["closing"] for r in body["items"]),
            "valuation": str(sum((r["unit_price"]*r["closing"] for r in body["items"]), Decimal(0))), "mismatches": mismatches}


def test_log() -> str:
    return "2026-09-14T12:00:00Z INFO worker ready\n" * 120 + "2026-09-14T12:00:01Z ERROR auth/test_login.py::test_expiry expected 401 got 200\n" + "2026-09-14T12:00:02Z INFO teardown\n" * 80


DEMO_PRICE = {"provider": "simulated", "model": "fixture-model", "version": "demo-v1", "currency": "USD", "source": "Synthetic arithmetic rates, not market prices", "effective_date": "2026-09-14", "input": 2, "cached_input": .2, "cache_write": 2.5, "output": 8, "discount": 0, "rule": "inclusive-input-disjoint-cache-v1"}

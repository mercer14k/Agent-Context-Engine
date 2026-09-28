"""Task scoping over explicit atomic requirements, not semantic summarization."""
from dataclasses import dataclass
import hashlib
from typing import Any
from .jsonutil import dumps, fields
from .errors import ValidationError
from .store import ReferenceStore, Access


@dataclass(frozen=True)
class Manifest:
    body: str
    version: str

    @classmethod
    def create(cls, data: dict[str, Any]) -> "Manifest":
        fields(data, {"v", "requirements", "sources", "decisions", "assumptions", "proposals"})
        if data["v"] != 1 or type(data["v"]) is not int:
            raise ValidationError("Unknown manifest version")
        if not isinstance(data["requirements"], list) or not isinstance(data["sources"], dict):
            raise ValidationError("Invalid manifest collections")
        for key in ("decisions", "assumptions", "proposals"):
            if not isinstance(data[key], list) or any(not isinstance(x, str) for x in data[key]):
                raise ValidationError("Decisions, assumptions, proposals must be string lists")
        for source in data["sources"].values():
            fields(source, {"version", "content"})
            if not isinstance(source["content"], str) or source["version"] != hashlib.sha256(source["content"].encode()).hexdigest():
                raise ValidationError("Source version does not match exact content")
        ids: set[str] = set()
        for item in data["requirements"]:
            fields(item, {"id", "text", "global", "depends_on", "source", "acceptance"})
            if any(not isinstance(item[k], str) or not item[k] for k in ("id", "text", "source", "acceptance")):
                raise ValidationError("Requirements need nonempty exact text and identifiers")
            if item["id"] in ids or type(item["global"]) is not bool or not isinstance(item["depends_on"], list) or any(not isinstance(x, str) for x in item["depends_on"]):
                raise ValidationError("Invalid or duplicate atomic requirement")
            if item["source"] not in data["sources"]:
                raise ValidationError("Missing requirement source")
            ids.add(item["id"])
        if any(set(item["depends_on"]) - ids for item in data["requirements"]):
            raise ValidationError("Missing dependency")
        body = dumps(data)
        return cls(body, hashlib.sha256(body.encode()).hexdigest())

    def prepare(self, task: str, required_ids: list[str], output_contract: str, *,
                inputs: list[dict[str, str]] | None = None, store: ReferenceStore | None = None,
                workspace: str = "default", access: Access | None = None,
                expected_version: str | None = None) -> dict[str, Any]:
        from .jsonutil import strict_loads
        if expected_version is not None and expected_version != self.version:
            raise ValidationError("Stale manifest")
        if not task or not output_contract:
            raise ValidationError("Task and output contract are required")
        data = strict_loads(self.body)
        by_id = {r["id"]: r for r in data["requirements"]}
        selected = set(required_ids) | {r["id"] for r in data["requirements"] if r["global"]}
        if selected - by_id.keys():
            raise ValidationError("Unknown requirement")
        previous: set[str] = set()
        while previous != selected:
            previous = selected.copy()
            for key in previous:
                selected.update(by_id[key]["depends_on"])
        # Stable prefix: constraints first, then task-specific inputs. Exact text retained.
        reqs = [r for r in data["requirements"] if r["id"] in selected]
        resolved = []
        for item in inputs or []:
            fields(item, {"reference"})
            if store is None or access is None:
                raise ValidationError("Reference access is unavailable")
            resolved.append(store.get(workspace, item["reference"], access))
        return {"v": 1, "manifest_version": self.version, "requirements": reqs,
                "decisions": data["decisions"], "assumptions": data["assumptions"], "proposals": data["proposals"],
                "source_versions": {r["source"]: data["sources"][r["source"]]["version"] for r in reqs},
                "task": task, "inputs": resolved, "output_contract": output_contract,
                "method": "explicit_scope_exact_text", "warning": "Caller selects task-critical IDs; semantic completeness is not inferred"}

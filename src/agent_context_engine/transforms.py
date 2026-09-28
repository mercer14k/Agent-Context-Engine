import re
from typing import Any
from .jsonutil import compact_json, dumps, strict_loads
from .errors import ValidationError


def log_runs(text: str) -> str:
    """Reversible adjacent-run encoding with exact lines, including timestamps/newlines."""
    runs: list[dict[str, Any]] = []
    for position, line in enumerate(text.splitlines(keepends=True), 1):
        if runs and runs[-1]["line"] == line:
            runs[-1]["count"] += 1
            runs[-1]["end"] = position
        else:
            runs.append({"start": position, "end": position, "count": 1, "line": line})
    return dumps({"format": "ace.log-runs.v1", "runs": runs})


def restore_logs(encoded: str, *, max_bytes: int = 16_000_000) -> str:
    data = strict_loads(encoded)
    if not isinstance(data, dict) or data.get("format") != "ace.log-runs.v1" or not isinstance(data.get("runs"), list):
        raise ValidationError("Unknown log encoding")
    out = []
    position = 1
    size = 0
    for run in data["runs"]:
        count, line = run.get("count"), run.get("line")
        if type(count) is not int or count < 1 or not isinstance(line, str) or run.get("start") != position or run.get("end") != position + count - 1:
            raise ValidationError("Invalid log range")
        size += len(line.encode()) * count
        if size > max_bytes:
            raise ValidationError("Decoded log exceeds size bound")
        out.append(line * count)
        position += count
    return "".join(out)


def pytest_view(text: str) -> str:
    lines = text.splitlines(keepends=True)
    # Conservative pytest terminal grammar. Retain all error sections verbatim.
    summary = re.compile(r"^=+ (?:\d+ (?:passed|failed|skipped|error|errors|xfailed|xpassed|deselected|warnings?)(?:, )?)+ in [0-9.]+s(?: \([^\n]*\))? =+\s*$")
    if not lines or not summary.fullmatch(lines[-1]):
        raise ValidationError("Unrecognized test output")
    progress = re.compile(r"^[.FsxXE]+\s+\[\s*\d+%\]\s*$")
    retained = [line for line in lines if not progress.fullmatch(line)]
    if len(retained) == len(lines):
        return text
    return "[pytest view: routine progress rows omitted; error details and terminal counts retained]\n" + "".join(retained)


def transform(text: str, format: str) -> tuple[str, str, bool]:
    if format == "json":
        return compact_json(text), "json_whitespace", False
    if format == "logs":
        return log_runs(text), "adjacent_log_runs", False
    if format == "pytest":
        return pytest_view(text), "pytest_progress_view", True
    if format == "auto" and text.lstrip().startswith(("{", "[")):
        return compact_json(text), "json_whitespace", False
    return text, "passthrough", False

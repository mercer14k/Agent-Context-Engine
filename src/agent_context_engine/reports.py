import csv
import html
import io
import json
from typing import Any


def csv_safe(value: Any) -> str:
    text = "" if value is None else str(value)
    return "'" + text if (text.startswith(("\t", "\r", "\n")) or text.lstrip().startswith(("=", "+", "-", "@"))) else text


def export_csv(summary: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    cols = ["run_id", "task", "arm", "provider", "model", "success", "input_tokens", "output_tokens", "cost", "duration_ms", "usage_complete"]
    writer.writerow(["data_mode", "workspace", *cols])
    for run in summary["runs"]:
        writer.writerow([csv_safe(summary["mode_label"]), csv_safe(summary["scope"]["workspace"]), *[csv_safe(run.get(k)) for k in cols]])
    return output.getvalue()


def report_html(data: dict[str, Any], title: str = "Agent Context Engine · Evidence report") -> str:
    # Script-free, portable, escaped. Raw prompts are never included.
    rows = data.get("rows", data.get("runs", []))
    columns = list(rows[0]) if rows else []
    table = "<table><thead><tr>"+"".join(f"<th>{html.escape(c)}</th>" for c in columns)+"</tr></thead><tbody>"
    for row in rows:
        table += "<tr>"+"".join(f"<td>{html.escape(str(row.get(c, 'Unavailable')))}</td>" for c in columns)+"</tr>"
    table += "</tbody></table>"
    metadata = {k: v for k, v in data.items() if k not in {"rows", "runs", "records", "commands", "checks"}}
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{html.escape(title)}</title><style>body{{background:#111419;color:#e5e9ed;font:15px/1.6 system-ui;margin:5vw}}h1{{font-weight:550}}table{{border-collapse:collapse;display:block;overflow:auto}}td,th{{padding:10px;border:1px solid #39404b;text-align:left}}pre{{white-space:pre-wrap;background:#1c2129;padding:24px;border-radius:12px}}.tag{{color:#b9ef90}}</style><h1>{html.escape(title)}</h1><p class="tag">{html.escape(data.get('mode_label', data.get('mode', 'Unavailable')))}</p><p>Local report · No live quality or billing claim is implied by offline or synthetic evidence.</p>{table}<h2>Scope, definitions, configuration, and limitations</h2><pre>{html.escape(json.dumps(metadata, indent=2, ensure_ascii=False))}</pre></html>'''

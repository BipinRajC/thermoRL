from __future__ import annotations

import json
import shutil
from pathlib import Path

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>ThermoRL · Scenario: RAMP</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; }
    code { background: #f2f2f2; padding: 0.1rem 0.3rem; }
  </style>
</head>
<body>
  <h1>ThermoRL replay bundle</h1>
  <p>Static artifact. The Three.js player lands in M7. Frames and ledgers are already here.</p>
  <ul>
    <li><code>frames_rr.jsonl</code></li>
    <li><code>frames_thermorl.jsonl</code></li>
    <li><code>ledger_rr.jsonl</code></li>
    <li><code>ledger_thermorl.jsonl</code></li>
    <li><code>metrics.json</code></li>
    <li><code>manifest.json</code></li>
  </ul>
</body>
</html>
"""


def bundle(
    *,
    frames_rr: Path,
    frames_thermorl: Path,
    ledger_rr: Path,
    ledger_thermorl: Path,
    metrics_rr: Path,
    metrics_thermorl: Path,
    out_dir: Path,
    bundle_id: str,
    seed: int,
    target_offered_load_ratio: float,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(frames_rr, out_dir / "frames_rr.jsonl")
    shutil.copyfile(frames_thermorl, out_dir / "frames_thermorl.jsonl")
    shutil.copyfile(ledger_rr, out_dir / "ledger_rr.jsonl")
    shutil.copyfile(ledger_thermorl, out_dir / "ledger_thermorl.jsonl")

    left = json.loads(metrics_rr.read_text())
    right = json.loads(metrics_thermorl.read_text())
    merged = {
        "thi_p10": min(float(left["thi_p10"]), float(right["thi_p10"])),
        "thi_p90": max(float(left["thi_p90"]), float(right["thi_p90"])),
        "round_robin": left,
        "thermorl": right,
    }
    (out_dir / "metrics.json").write_text(json.dumps(merged, indent=2) + "\n")
    viz_dist = Path(__file__).resolve().parents[2] / "viz" / "dist"
    if (viz_dist / "index.html").exists():
        for item in viz_dist.iterdir():
            dest = out_dir / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
    else:
        (out_dir / "index.html").write_text(INDEX_HTML)
    (out_dir / "manifest.json").write_text(
        json.dumps(
            {
                "bundle_id": bundle_id,
                "scenario_id": "ramp",
                "policies": ["round_robin", "thi_lookahead"],
                "seed": seed,
                "backend": "python",
                "target_offered_load_ratio": target_offered_load_ratio,
            },
            indent=2,
        )
        + "\n"
    )
    _write_inline_data(out_dir)
    return out_dir


def _read_jsonl(path: Path) -> list[object]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _write_inline_data(out_dir: Path) -> None:
    payload = {
        "frames_rr": _read_jsonl(out_dir / "frames_rr.jsonl"),
        "frames_thermorl": _read_jsonl(out_dir / "frames_thermorl.jsonl"),
        "ledger_thermorl": _read_jsonl(out_dir / "ledger_thermorl.jsonl"),
        "metrics": json.loads((out_dir / "metrics.json").read_text()),
    }
    (out_dir / "bundle-data.js").write_text("window.THERMORL_DATA = " + json.dumps(payload) + ";\n")
    html = out_dir / "index.html"
    if html.exists():
        text = html.read_text()
        if "bundle-data.js" not in text:
            html.write_text(
                text.replace(
                    '<script type="module"',
                    '<script src="./bundle-data.js"></script>\n    <script type="module"',
                    1,
                )
            )

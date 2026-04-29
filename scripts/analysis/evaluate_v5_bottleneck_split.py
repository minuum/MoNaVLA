#!/usr/bin/env python3
"""
Build a unified bottleneck split summary for current V5 artifacts.

This script intentionally supports partially-complete truth evaluation:
  - if bbox truth is pending, it still emits current model-side summaries
  - once truth is completed, the same script can incorporate it
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SHORTTERM_PATH = ROOT / "docs" / "v5" / "shortterm_eval" / "summary.json"
DEGRADATION_PATH = ROOT / "docs" / "v5" / "rollout_degradation" / "degradation_summary.json"
BBOX_TRUTH_EVAL_PATH = ROOT / "docs" / "v5" / "bbox_truth_eval" / "summary.json"
STEP1_SUMMARY_PATH = ROOT / "docs" / "v5" / "bbox_nav_step1" / "summary.json"
OUT_DIR = ROOT / "docs" / "v5" / "bottleneck_split"
DEFAULT_PM_LOG = ROOT / "logs" / "v5_eval_queue_20260422.log"

MODELS = ["exp24", "exp21", "exp18", "exp17", "exp11"]


def load_json(path: Path):
    return json.loads(path.read_text())


def load_pm_map(log_path: Path) -> dict:
    text = log_path.read_text(errors="ignore") if log_path.exists() else ""
    vals = [float(x) for x in re.findall(r"PM \(Perfect Match\) : ([0-9.]+)%", text)]
    tail = vals[-len(MODELS):] if len(vals) >= len(MODELS) else vals
    return dict(zip(MODELS, tail))


def provisional_bottleneck(item: dict) -> str:
    closed_loop = item["closed_loop_success"]
    prefix = item["non_straight_prefix_success"]
    macro = item["macro_per_path_frame_acc"]
    pm = item.get("pm_percent")

    if closed_loop > 0:
        if macro < 0.08:
            return "closed_loop_best_but_offline_alignment_weak"
        return "closed_loop_candidate"
    if prefix >= 0.45:
        return "late_drift_or_action_collapse"
    if pm is not None and pm >= 50.0:
        return "teacher_forced_ok_but_rollout_breakdown"
    return "perception_or_policy_commitment_failure"


def build_html(payload: dict) -> str:
    rows = []
    for item in payload["models"]:
        rows.append(
            f"""
            <tr>
              <td>{item['model']}</td>
              <td>{item['closed_loop_success']*100:.1f}%</td>
              <td>{item['non_straight_prefix_success']*100:.1f}%</td>
              <td>{item['macro_per_path_frame_acc']*100:.1f}%</td>
              <td>{item['full_fpe']:.3f}</td>
              <td>{item['full_tld']:.3f}</td>
              <td>{item['pm_percent']:.2f}%</td>
              <td>{item['provisional_bottleneck']}</td>
            </tr>
            """
        )
    bbox_status = payload["bbox_truth_eval"]["status"] if payload.get("bbox_truth_eval") else "missing"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>V5 Bottleneck Split</title>
  <style>
    :root {{
      --bg: #f4f1e8;
      --card: #fffdf7;
      --line: #d7d1c3;
      --fg: #1c2217;
      --muted: #5b6354;
      --accent: #2f5d50;
    }}
    body {{
      margin: 0;
      padding: 28px;
      background: linear-gradient(180deg, #f7f5ee, #ece8dc);
      color: var(--fg);
      font-family: Georgia, "Times New Roman", serif;
    }}
    h1 {{ margin: 0 0 8px 0; }}
    .sub {{ color: var(--muted); margin-bottom: 18px; max-width: 900px; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 8px 28px rgba(30, 40, 20, 0.05);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 8px;
      text-align: left;
    }}
    th {{ color: var(--accent); }}
    .meta {{ margin-bottom: 12px; color: var(--muted); }}
  </style>
</head>
<body>
  <h1>V5 Bottleneck Split</h1>
  <div class="sub">
    Current summary merges short-term rollout, degradation, PM, and bbox-truth status.
    BBox truth status: <strong>{bbox_status}</strong>.
  </div>
  <div class="card">
    <div class="meta">Pseudo bbox baseline PM: {payload['bbox_step1_baseline']['overall_pm_mlp']*100:.1f}%</div>
    <table>
      <thead>
        <tr>
          <th>Model</th>
          <th>Closed-loop</th>
          <th>Prefix@5</th>
          <th>Macro Frame</th>
          <th>FPE</th>
          <th>TLD</th>
          <th>PM</th>
          <th>Provisional Bottleneck</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pm_log", default=str(DEFAULT_PM_LOG))
    args = parser.parse_args()

    shortterm = load_json(SHORTTERM_PATH)
    degradation = load_json(DEGRADATION_PATH)["models"]
    step1 = load_json(STEP1_SUMMARY_PATH)
    bbox_truth = load_json(BBOX_TRUTH_EVAL_PATH) if BBOX_TRUTH_EVAL_PATH.exists() else None
    pm_map = load_pm_map(Path(args.pm_log))

    rows = []
    for item in shortterm["models"]:
        model = item["model"]
        deg = degradation[model]["summary"]
        row = {
            "model": model,
            "closed_loop_success": item["closed_loop_success"],
            "non_straight_prefix_success": item["non_straight_prefix_success"],
            "macro_per_path_frame_acc": item["macro_per_path_frame_acc"],
            "full_fpe": item["closed_loop_mean_fpe"],
            "full_tld": item["closed_loop_mean_tld"],
            "pm_percent": pm_map.get(model),
            "k5_success": deg["prefix"]["k=5"]["success_rate"],
            "k10_success": deg["prefix"]["k=10"]["success_rate"],
            "provisional_bottleneck": "",
        }
        row["provisional_bottleneck"] = provisional_bottleneck(row)
        rows.append(row)

    payload = {
        "dataset_note": shortterm.get("dataset_note"),
        "bbox_truth_eval": bbox_truth,
        "bbox_step1_baseline": step1,
        "models": rows,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUT_DIR / "summary.json"
    out_html = OUT_DIR / "index.html"
    out_json.write_text(json.dumps(payload, indent=2))
    out_html.write_text(build_html(payload))
    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_html}")


if __name__ == "__main__":
    main()

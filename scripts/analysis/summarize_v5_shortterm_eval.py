#!/usr/bin/env python3
"""
Summarize short-term V5 evaluation metrics for the current collection state.

Primary goal:
  Report the three metrics that best fit the current V5 core-only dataset:
  1. closed-loop success rate
  2. non-straight prefix@5 success rate
  3. macro per-path frame accuracy

This wraps the shared-split degradation evaluation so we can use one script for
fast model selection.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.analysis.evaluate_rollout_degradation_v5 import (
    OUT_DIR as DEG_OUT_DIR,
    evaluate_model,
    get_test_episode_paths,
)

OUT_DIR = ROOT / "docs" / "v5" / "shortterm_eval"
OUT_DIR.mkdir(parents=True, exist_ok=True)

NON_STRAIGHT_PATHS = {
    "center_left",
    "center_right",
    "left_left",
    "left_right",
    "right_left",
    "right_right",
}


def summarize_shortterm(result: dict, prefix_horizon: int) -> dict:
    summary = result["summary"]
    episodes = result["episodes"]

    non_straight_eps = [ep for ep in episodes if ep["path_type"] in NON_STRAIGHT_PATHS]
    non_straight_prefix = [
        ep["prefix"][f"k={prefix_horizon}"]["success"] for ep in non_straight_eps
    ]

    by_path = summary.get("by_path_full", {})
    macro_frame_acc = (
        sum(v["frame_acc"] for v in by_path.values()) / max(len(by_path), 1)
    )
    macro_closed_loop = (
        sum(v["success_rate"] for v in by_path.values()) / max(len(by_path), 1)
    )

    return {
        "model": result["model"],
        "label": result["label"],
        "n_episodes": summary["n_episodes"],
        "closed_loop_success": summary["full"]["success_rate"],
        "closed_loop_mean_fpe": summary["full"]["mean_fpe"],
        "closed_loop_mean_tld": summary["full"]["mean_tld"],
        "prefix_horizon": prefix_horizon,
        "non_straight_prefix_success": (
            sum(non_straight_prefix) / max(len(non_straight_prefix), 1)
        ),
        "macro_per_path_frame_acc": macro_frame_acc,
        "macro_per_path_closed_loop": macro_closed_loop,
        "by_path_frame_acc": {
            path: stats["frame_acc"] for path, stats in sorted(by_path.items())
        },
        "by_path_closed_loop": {
            path: stats["success_rate"] for path, stats in sorted(by_path.items())
        },
    }


def build_html(payload: dict) -> str:
    cards = []
    for item in payload["models"]:
        cards.append(
            f"""
            <section class="card">
              <div class="eyebrow">{item['model']}</div>
              <h2>{item['label']}</h2>
              <div class="metric-grid">
                <div>
                  <div class="metric">{item['closed_loop_success']*100:.1f}%</div>
                  <div class="caption">Closed-loop success</div>
                </div>
                <div>
                  <div class="metric">{item['non_straight_prefix_success']*100:.1f}%</div>
                  <div class="caption">Non-straight prefix@{item['prefix_horizon']} success</div>
                </div>
                <div>
                  <div class="metric">{item['macro_per_path_frame_acc']*100:.1f}%</div>
                  <div class="caption">Macro per-path frame acc</div>
                </div>
              </div>
              <div class="sub">
                FPE {item['closed_loop_mean_fpe']:.3f}m ·
                TLD {item['closed_loop_mean_tld']:.3f} ·
                Macro per-path closed-loop {item['macro_per_path_closed_loop']*100:.1f}%
              </div>
            </section>
            """
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>V5 Short-Term Eval</title>
  <style>
    :root {{
      --bg: #f6f7f2;
      --fg: #142013;
      --muted: #5c6657;
      --card: #fffdf6;
      --line: #d8ddd0;
      --accent: #205c3b;
    }}
    body {{
      margin: 0;
      padding: 28px;
      background: radial-gradient(circle at top left, #fcfbf5, #eef2e7 70%);
      color: var(--fg);
      font-family: Georgia, "Times New Roman", serif;
    }}
    h1 {{ margin: 0 0 8px 0; font-size: 2rem; }}
    .subhead {{ color: var(--muted); max-width: 900px; line-height: 1.5; margin-bottom: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 8px 30px rgba(30, 50, 20, 0.05);
    }}
    .eyebrow {{ color: var(--accent); text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.78rem; }}
    h2 {{ margin: 8px 0 16px 0; font-size: 1.4rem; }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }}
    .metric {{ font-size: 2rem; font-weight: 700; }}
    .caption {{ color: var(--muted); font-size: 0.85rem; line-height: 1.25; }}
    .sub {{ margin-top: 14px; color: var(--muted); font-size: 0.92rem; }}
  </style>
</head>
<body>
  <h1>V5 Short-Term Evaluation</h1>
  <div class="subhead">
    Current V5 collection is a core-only route dataset. These three metrics are the recommended
    short-term selection signals: closed-loop success, non-straight prefix commitment, and macro
    per-path frame accuracy.
  </div>
  <div class="grid">
    {''.join(cards)}
  </div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--models",
        default="exp11,exp17,exp18,exp21,exp24,exp25,exp26,exp27,exp28",
        help="Comma-separated model keys supported by evaluate_rollout_degradation_v5.py",
    )
    parser.add_argument("--prefix_horizon", type=int, default=5)
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument("--success_fpe", type=float, default=0.5)
    args = parser.parse_args()

    model_keys = [m.strip() for m in args.models.split(",") if m.strip()]
    episode_paths = get_test_episode_paths(seed=42)

    results = []
    for key in model_keys:
        result = evaluate_model(
            key,
            episode_paths=episode_paths,
            horizons=[args.prefix_horizon, 10, 15],
            dt=args.dt,
            success_fpe=args.success_fpe,
        )
        short = summarize_shortterm(result, prefix_horizon=args.prefix_horizon)
        results.append(short)
        print(
            f"{short['model']:>6s} | closed_loop={short['closed_loop_success']*100:5.1f}% | "
            f"prefix@{args.prefix_horizon} non-straight={short['non_straight_prefix_success']*100:5.1f}% | "
            f"macro_frame_acc={short['macro_per_path_frame_acc']*100:5.1f}%"
        )

    payload = {
        "dataset_note": "V5 core-only route dataset",
        "source": str(DEG_OUT_DIR / "degradation_summary.json"),
        "models": results,
    }

    out_json = OUT_DIR / "summary.json"
    out_html = OUT_DIR / "index.html"
    out_json.write_text(json.dumps(payload, indent=2))
    out_html.write_text(build_html(payload))
    print(f"\nWrote: {out_json}")
    print(f"Wrote: {out_html}")


if __name__ == "__main__":
    main()

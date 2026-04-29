#!/usr/bin/env python3
"""
Exp14 Step 0-C: Rule-based 경계값 튜닝

Step 0-B의 (cx, area, GT_class) 데이터로 grid search해서
best rule thresholds 찾기. 재추론 불필요.

Usage:
  python3 scripts/tune_bbox_nav_rule.py
"""

import json
from pathlib import Path
from collections import defaultdict
from itertools import product

ROOT = Path(__file__).resolve().parent.parent
STEP0B = ROOT / "docs" / "v5" / "bbox_nav_step0b"
OUT_DIR = ROOT / "docs" / "v5" / "bbox_nav_step0c"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CLASS_NAMES = ["STOP", "FORWARD", "LEFT", "RIGHT", "FWD+L", "FWD+R", "ROT_L", "ROT_R"]
PATH_TYPES = [
    "center_straight", "center_left", "center_right",
    "left_straight",   "left_left",   "left_right",
    "right_straight",  "right_left",  "right_right",
]


def apply_rule(cx, area, th):
    if cx is None or area is None:
        return 1
    if area > th["stop_area"]:
        return 0
    if cx < th["hard_left"]:
        return 2
    if cx < th["soft_left"]:
        return 4
    if cx > th["hard_right"]:
        return 3
    if cx > th["soft_right"]:
        return 5
    return 1


def eval_rule(results, th):
    correct = 0
    total = 0
    per_path = defaultdict(lambda: {"c": 0, "t": 0})
    for r in results:
        gt = r["gt_class"]
        bb = r.get("bbox")
        if bb is None:
            pred = 1
        else:
            pred = apply_rule(bb["cx"], bb["area"], th)
        per_path[r["path_type"]]["t"] += 1
        if pred == gt:
            correct += 1
            per_path[r["path_type"]]["c"] += 1
        total += 1
    return correct / total, per_path


def main():
    results = json.loads((STEP0B / "results.json").read_text())
    print(f"Loaded {len(results)} samples")

    # Analyze GT class distribution vs cx/area
    by_gt = defaultdict(list)
    for r in results:
        bb = r.get("bbox")
        if bb:
            by_gt[r["gt_name"]].append((bb["cx"], bb["area"]))

    print("\n=== cx distribution by GT class ===")
    for cls in CLASS_NAMES:
        pairs = by_gt.get(cls, [])
        if not pairs:
            continue
        cxs = sorted(x for x, _ in pairs)
        n = len(cxs)
        print(f"  {cls:8s} n={n:3d}  cx min/p25/med/p75/max = "
              f"{cxs[0]:.2f} / {cxs[n//4]:.2f} / {cxs[n//2]:.2f} / "
              f"{cxs[3*n//4]:.2f} / {cxs[-1]:.2f}")

    # Baseline eval
    baseline_th = {
        "hard_left": 0.15, "soft_left": 0.30,
        "soft_right": 0.70, "hard_right": 0.85,
        "stop_area": 0.35,
    }
    base_pm, base_per = eval_rule(results, baseline_th)
    print(f"\nBaseline rule PM: {base_pm:.2%}")

    # Grid search
    best_pm = base_pm
    best_th = baseline_th
    grid_hard_left  = [0.10, 0.15, 0.20, 0.25]
    grid_soft_left  = [0.30, 0.35, 0.40, 0.45, 0.50]
    grid_soft_right = [0.50, 0.55, 0.60, 0.65, 0.70]
    grid_hard_right = [0.75, 0.80, 0.85, 0.90]
    grid_stop_area  = [0.25, 0.35, 0.50, 0.99]  # 0.99 = effectively disable STOP

    count = 0
    for hl, sl, sr, hr, sa in product(
        grid_hard_left, grid_soft_left, grid_soft_right,
        grid_hard_right, grid_stop_area
    ):
        if hl >= sl or sl >= sr or sr >= hr:
            continue
        th = {"hard_left": hl, "soft_left": sl,
              "soft_right": sr, "hard_right": hr,
              "stop_area": sa}
        pm, _ = eval_rule(results, th)
        count += 1
        if pm > best_pm:
            best_pm = pm
            best_th = th

    print(f"\nGrid search: {count} combinations tried")
    print(f"Best PM: {best_pm:.2%}  (baseline {base_pm:.2%})")
    print(f"Best thresholds: {best_th}")

    # Eval best
    best_pm_final, best_per = eval_rule(results, best_th)
    print(f"\n=== Per-path with best rule ===")
    for pt in PATH_TYPES:
        v = best_per.get(pt, {"c": 0, "t": 0})
        print(f"  {pt:20s}: {v['c']}/{v['t']} = {v['c']/max(v['t'],1):.1%}")

    # Write rule-tuned results + HTML
    tuned_results = []
    for r in results:
        bb = r.get("bbox")
        pred = apply_rule(bb["cx"], bb["area"], best_th) if bb else 1
        rr = dict(r)
        rr["pred_class"] = pred
        rr["pred_name"] = CLASS_NAMES[pred]
        # rewrite image path (reuse step0b images)
        rr["image"] = f"../bbox_nav_step0b/{r['image']}"
        tuned_results.append(rr)

    summary = {
        "overall_pm": best_pm_final,
        "total": sum(v["t"] for v in best_per.values()),
        "correct": sum(v["c"] for v in best_per.values()),
        "pm_by_path": {k: {"correct": v["c"], "total": v["t"]} for k, v in best_per.items()},
        "baseline_pm": base_pm,
        "best_thresholds": best_th,
        "baseline_thresholds": baseline_th,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    (OUT_DIR / "results.json").write_text(
        json.dumps(tuned_results, indent=2, ensure_ascii=False)
    )

    build_html(tuned_results, summary)
    print(f"\nHTML: {OUT_DIR / 'index.html'}")


def build_html(results, summary):
    by_path = defaultdict(list)
    for r in results:
        by_path[r["path_type"]].append(r)

    pm_rows = []
    for pt in PATH_TYPES:
        v = summary["pm_by_path"].get(pt, {"correct": 0, "total": 0})
        pm = v["correct"] / max(v["total"], 1)
        pm_rows.append(
            f"<tr><td>{pt}</td><td>{v['correct']}/{v['total']}</td>"
            f"<td><strong>{pm:.1%}</strong></td></tr>"
        )

    th = summary["best_thresholds"]
    th_html = (f"STOP_area≥{th['stop_area']:.2f} | "
               f"LEFT cx&lt;{th['hard_left']:.2f} | "
               f"FWD+L cx&lt;{th['soft_left']:.2f} | "
               f"FWD cx≤{th['soft_right']:.2f} | "
               f"FWD+R cx≤{th['hard_right']:.2f} | RIGHT else")

    sections = []
    for pt in PATH_TYPES:
        rows = by_path.get(pt, [])
        if not rows:
            continue
        correct = sum(1 for r in rows if r["pred_class"] == r["gt_class"])
        total = len(rows)
        cells = []
        for r in rows:
            ok = "ok" if r["pred_class"] == r["gt_class"] else "bad"
            bb = r.get("bbox")
            bbox_info = f"cx={bb['cx']:.2f} area={bb['area']:.2f}" if bb else "no bbox"
            cells.append(f"""
              <div class="sample {ok}">
                <img src="{r['image']}" alt="">
                <div class="meta">
                  <div><strong>{r['pred_name']}</strong> vs GT <strong>{r['gt_name']}</strong></div>
                  <div class="cap">{bbox_info}</div>
                </div>
              </div>""")
        sections.append(f"""
          <div class="path-section">
            <h2>{pt} <span class="pm">{correct}/{total} = {correct/total:.1%}</span></h2>
            <div class="grid">{''.join(cells)}</div>
          </div>""")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Exp14 Step 0-C: Tuned Rule</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 24px; background: #0f172a; color: #e2e8f0; }}
  h1 {{ font-size: 2rem; margin-bottom: 8px; }}
  .sub {{ color: #94a3b8; margin-bottom: 24px; max-width: 900px; line-height: 1.6; }}
  .back {{ display: inline-block; margin-bottom: 16px; color: #60a5fa; text-decoration: none; }}
  .overall {{ display: inline-block; padding: 12px 24px; background: #1e293b; border-radius: 8px; margin-bottom: 20px; font-size: 1.3rem; }}
  .overall strong {{ color: #22c55e; }}
  .rule {{ background: #1e293b; padding: 10px 14px; border-radius: 6px; font-family: monospace; font-size: 0.85rem; margin-bottom: 20px; color: #fbbf24; }}
  table {{ border-collapse: collapse; margin-bottom: 28px; background: #1e293b; border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 8px 16px; text-align: left; border-bottom: 1px solid #334155; }}
  th {{ background: #0b1220; }}
  .path-section {{ margin-bottom: 36px; }}
  .path-section h2 {{ font-size: 1.3rem; padding: 8px 12px; background: #1e293b; border-radius: 6px; }}
  .path-section h2 .pm {{ color: #facc15; font-size: 0.9rem; margin-left: 8px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; margin-top: 10px; }}
  .sample {{ background: #1e293b; border-radius: 8px; overflow: hidden; border: 2px solid transparent; }}
  .sample.ok {{ border-color: #22c55e; }}
  .sample.bad {{ border-color: #ef4444; }}
  .sample img {{ width: 100%; display: block; }}
  .meta {{ padding: 8px 10px; font-size: 0.85rem; }}
  .cap {{ color: #facc15; margin-top: 4px; font-size: 0.75rem; font-family: monospace; }}
</style>
</head>
<body>
  <a class="back" href="../../index.html">← Back to main</a>
  <h1>Exp14 Step 0-C: Tuned Rule (grid search)</h1>
  <p class="sub">
    Step 0-B와 동일한 Exp10 grounding 결과에 rule threshold만 grid search로 튜닝.
    Baseline PM {summary['baseline_pm']:.1%} → Tuned PM {summary['overall_pm']:.1%}
  </p>
  <div class="overall">Overall PM: <strong>{summary['overall_pm']:.1%}</strong>
    ({summary['correct']}/{summary['total']}) · baseline {summary['baseline_pm']:.1%}</div>
  <div class="rule">Best rule: {th_html}</div>
  <h2>PM per Path Type</h2>
  <table><tr><th>Path Type</th><th>Correct/Total</th><th>PM</th></tr>{''.join(pm_rows)}</table>
  {''.join(sections)}
</body>
</html>"""
    (OUT_DIR / "index.html").write_text(html)


if __name__ == "__main__":
    main()

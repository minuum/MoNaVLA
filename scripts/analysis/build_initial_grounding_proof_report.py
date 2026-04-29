#!/usr/bin/env python3
"""
Build the TODO-1 object-recognition proof report for the April 24 professor
feedback.

The report deliberately separates:
  - model grounding output from ROS_action/v5_data_bak/v5_grounding.json
  - scaffold seed boxes from docs/v5/bbox_truth_initial18.json
  - human-reviewed GT fields, if they have been filled

If no human-reviewed rows exist, it emits a pending report instead of
fabricating perception metrics.
"""

from __future__ import annotations

import argparse
import html
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent.parent
TRUTH_PATH = ROOT / "docs" / "v5" / "bbox_truth_initial18.json"
GROUNDING_PATH = ROOT / "ROS_action" / "v5_data_bak" / "v5_grounding.json"
OUT_DIR = ROOT / "docs" / "v5" / "initial_grounding_proof"
OVERLAY_DIR = OUT_DIR / "overlays"

DONE_STATUSES = {"done", "complete", "completed", "verified", "reviewed"}
KEYWORDS = ("basket", "gray box", "box", "container", "gray")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def normalize_box(box: Any) -> Optional[list[float]]:
    if not box:
        return None
    if isinstance(box, dict):
        vals = [box[k] for k in ("x1", "y1", "x2", "y2")]
    else:
        vals = list(box)
    x1, y1, x2, y2 = [float(v) for v in vals]
    if max(x1, y1, x2, y2) > 1.5:
        x1, y1, x2, y2 = x1 / 1000.0, y1 / 1000.0, x2 / 1000.0, y2 / 1000.0
    x1, x2 = sorted((max(0.0, min(1.0, x1)), max(0.0, min(1.0, x2))))
    y1, y2 = sorted((max(0.0, min(1.0, y1)), max(0.0, min(1.0, y2))))
    return [x1, y1, x2, y2]


def bbox_center(box: Optional[list[float]]) -> tuple[Optional[float], Optional[float]]:
    if box is None:
        return None, None
    return (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0


def bbox_area(box: Optional[list[float]]) -> Optional[float]:
    if box is None:
        return None
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def coarse_from_box(box: Optional[list[float]]) -> str:
    cx, _cy = bbox_center(box)
    if cx is None:
        return "not_visible"
    if cx < 1.0 / 3.0:
        return "left"
    if cx > 2.0 / 3.0:
        return "right"
    return "center"


def iou_xyxy(a: Optional[list[float]], b: Optional[list[float]]) -> Optional[float]:
    if a is None or b is None:
        return None
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = bbox_area(a) + bbox_area(b) - inter
    return inter / union if union > 0 else 0.0


def center_l1(a: Optional[list[float]], b: Optional[list[float]]) -> Optional[float]:
    acx, acy = bbox_center(a)
    bcx, bcy = bbox_center(b)
    if acx is None or acy is None or bcx is None or bcy is None:
        return None
    return abs(acx - bcx) + abs(acy - bcy)


def select_grounding_bbox(frame_data: dict[str, Any]) -> tuple[Optional[dict[str, Any]], str, bool]:
    valid = frame_data.get("valid_bboxes", []) or []
    all_boxes = frame_data.get("bboxes", []) or []
    fullscreen_only = bool(all_boxes) and not valid

    for box in valid:
        entity = str(box.get("entity", "")).lower()
        if any(k in entity for k in KEYWORDS):
            return box, "keyword_match", fullscreen_only
    if valid:
        return valid[0], "first_valid_fallback", fullscreen_only
    return None, "none", fullscreen_only


def is_reviewed(ann: dict[str, Any]) -> bool:
    if str(ann.get("review_status", "")).lower() in DONE_STATUSES:
        return True
    return ann.get("target_visible") is not None


def draw_box(draw: ImageDraw.ImageDraw, box: Optional[list[float]], size: tuple[int, int], color: str, width: int) -> None:
    if box is None:
        return
    w, h = size
    draw.rectangle(
        [box[0] * w, box[1] * h, box[2] * w, box[3] * h],
        outline=color,
        width=width,
    )


def render_overlay(row: dict[str, Any], out_path: Path) -> None:
    img = Image.open(row["frame_path"]).convert("RGB").resize((640, 360))
    draw = ImageDraw.Draw(img)
    draw_box(draw, row["seed_bbox"], img.size, "#3399ff", 3)
    draw_box(draw, row["model_bbox"], img.size, "#ff3333", 4)
    draw_box(draw, row["gt_bbox"], img.size, "#00ff66", 4)
    draw.rectangle([0, 0, img.size[0], 48], fill=(15, 23, 42))
    title = f'{row["path_type"]} / f{row["frame_idx"]:04d} / reviewed={row["reviewed"]}'
    draw.text((8, 6), title, fill=(255, 255, 255))
    draw.text((8, 26), "blue=seed  red=model  green=human-GT", fill=(255, 255, 255))
    img.save(out_path)


def mean(values: list[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def ratio(num: int, den: int) -> Optional[float]:
    return num / den if den else None


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    reviewed = [r for r in rows if r["reviewed"]]
    visible = [r for r in reviewed if r["target_visible"]]
    invisible = [r for r in reviewed if r["target_visible"] is False]
    visible_pred = [r for r in visible if r["model_bbox"] is not None]
    invisible_pred = [r for r in invisible if r["model_bbox"] is not None]
    side_cases = [r for r in visible if r["gt_coarse"] in {"left", "right"}]
    side_errors = [r for r in side_cases if r["model_coarse"] != r["gt_coarse"]]

    model_boxes = [r for r in rows if r["model_bbox"] is not None]
    source_counts = Counter(r["model_source"] for r in rows)
    entity_counts = Counter(r["model_entity"] or "none" for r in rows)

    return {
        "n_total": len(rows),
        "n_reviewed": len(reviewed),
        "n_pending": len(rows) - len(reviewed),
        "n_model_bbox": len(model_boxes),
        "model_bbox_rate": ratio(len(model_boxes), len(rows)),
        "model_source_counts": dict(source_counts),
        "model_entity_top10": dict(entity_counts.most_common(10)),
        "status": "pending_human_review" if not reviewed else "ok",
        "metrics": None
        if not reviewed
        else {
            "n_visible": len(visible),
            "n_invisible": len(invisible),
            "detection_recall": ratio(len(visible_pred), len(visible)),
            "false_positive_rate": ratio(len(invisible_pred), len(invisible)),
            "mean_iou": mean([r["model_iou"] for r in visible_pred if r["model_iou"] is not None]),
            "mean_center_l1": mean([r["model_center_l1"] for r in visible_pred if r["model_center_l1"] is not None]),
            "wrong_side_rate": ratio(len(side_errors), len(side_cases)),
        },
    }


def build_rows(truth_path: Path, grounding_path: Path, out_dir: Path) -> list[dict[str, Any]]:
    truth_payload = load_json(truth_path)
    annotations = truth_payload["annotations"] if isinstance(truth_payload, dict) else truth_payload
    grounding = load_json(grounding_path)
    overlay_dir = out_dir / "overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for ann in annotations:
        episode = ann["episode"]
        frame_idx = int(ann["frame_idx"])
        frame_data = grounding.get(episode, {}).get(str(frame_idx), {})
        model_box_raw, source, fullscreen_only = select_grounding_bbox(frame_data)
        model_box = normalize_box(model_box_raw)
        seed_box = normalize_box(ann.get("seed_bbox_xyxy_norm"))
        gt_box = normalize_box(ann.get("bbox_xyxy_norm"))
        reviewed = is_reviewed(ann)
        target_visible = ann.get("target_visible") if reviewed else None
        gt_coarse = ann.get("coarse_position") or ("not_visible" if target_visible is False else None)
        row = {
            "episode": episode,
            "path_type": ann["path_type"],
            "frame_idx": frame_idx,
            "frame_path": ann["frame_path"],
            "reviewed": reviewed,
            "review_status": ann.get("review_status"),
            "target_visible": target_visible,
            "gt_bbox": gt_box,
            "gt_coarse": gt_coarse,
            "seed_bbox": seed_box,
            "seed_entity": ann.get("seed_entity"),
            "seed_caption": ann.get("seed_caption"),
            "model_bbox": model_box,
            "model_entity": model_box_raw.get("entity") if model_box_raw else None,
            "model_source": source,
            "model_fullscreen_only": fullscreen_only,
            "model_caption": frame_data.get("caption"),
            "model_raw": frame_data.get("raw"),
            "model_coarse": coarse_from_box(model_box),
            "model_iou": iou_xyxy(gt_box, model_box),
            "model_center_l1": center_l1(gt_box, model_box),
        }
        overlay_path = overlay_dir / f'{episode}_f{frame_idx:04d}.png'
        render_overlay(row, overlay_path)
        row["overlay_rel"] = str(overlay_path.relative_to(out_dir))
        rows.append(row)
    return rows


def build_html(summary: dict[str, Any], rows: list[dict[str, Any]], out_path: Path) -> None:
    cards = []
    for row in rows:
        cards.append(
            f"""
            <article class="card {'pending' if not row['reviewed'] else 'reviewed'}">
              <img src="{html.escape(row['overlay_rel'])}" alt="{html.escape(row['episode'])} frame {row['frame_idx']}">
              <div class="meta">
                <div><strong>{html.escape(row['path_type'])}</strong> / frame {row['frame_idx']} / reviewed={str(row['reviewed']).lower()}</div>
                <div>model: entity=<code>{html.escape(str(row['model_entity']))}</code>, coarse=<code>{html.escape(row['model_coarse'])}</code>, source=<code>{html.escape(row['model_source'])}</code></div>
                <div>GT: visible=<code>{html.escape(str(row['target_visible']))}</code>, coarse=<code>{html.escape(str(row['gt_coarse']))}</code>, IoU=<code>{html.escape(str(None if row['model_iou'] is None else round(row['model_iou'], 4)))}</code></div>
                <div>seed: entity=<code>{html.escape(str(row['seed_entity']))}</code></div>
                <p>{html.escape(str(row['model_caption'])[:260])}</p>
              </div>
            </article>
            """
        )

    metrics = summary["metrics"]
    metrics_html = "<p>No human-reviewed rows yet; quantitative perception metrics are intentionally withheld.</p>"
    if metrics is not None:
        metrics_html = "<pre>" + html.escape(json.dumps(metrics, indent=2)) + "</pre>"

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Initial Grounding Proof</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; background: #f8fafc; color: #111827; }}
    h1 {{ margin-bottom: 4px; }}
    .summary, .card {{ background: white; border: 1px solid #d1d5db; border-radius: 6px; }}
    .summary {{ padding: 16px; margin: 16px 0 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; }}
    .card.pending {{ border-left: 5px solid #f59e0b; }}
    .card.reviewed {{ border-left: 5px solid #10b981; }}
    img {{ width: 100%; display: block; border-bottom: 1px solid #e5e7eb; }}
    .meta {{ padding: 12px; font-size: 14px; line-height: 1.45; }}
    code {{ background: #eef2ff; padding: 1px 5px; border-radius: 4px; }}
    pre {{ white-space: pre-wrap; background: #0f172a; color: #e5e7eb; padding: 12px; border-radius: 6px; }}
  </style>
</head>
<body>
  <h1>Initial Grounding Proof</h1>
  <div>Purpose: TODO 1 object-recognition proof from April 24 meeting.</div>
  <section class="summary">
    <div>status: <code>{html.escape(summary['status'])}</code></div>
    <div>reviewed: <code>{summary['n_reviewed']} / {summary['n_total']}</code></div>
    <div>model bbox-like outputs: <code>{summary['n_model_bbox']} / {summary['n_total']}</code></div>
    <h2>Model Output Before Human Review</h2>
    <pre>{html.escape(json.dumps({k: summary[k] for k in ['model_source_counts', 'model_entity_top10']}, indent=2))}</pre>
    <h2>Metrics</h2>
    {metrics_html}
  </section>
  <section class="grid">
    {''.join(cards)}
  </section>
</body>
</html>
"""
    out_path.write_text(html_text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth", default=str(TRUTH_PATH))
    parser.add_argument("--grounding", default=str(GROUNDING_PATH))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args()

    truth_path = Path(args.truth)
    grounding_path = Path(args.grounding)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = build_rows(truth_path, grounding_path, out_dir)
    summary = summarize(rows)
    payload = {
        "truth_path": str(truth_path),
        "grounding_path": str(grounding_path),
        "summary": summary,
        "rows": rows,
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2))
    build_html(summary, rows, out_dir / "index.html")
    print(f"Wrote: {out_dir / 'summary.json'}")
    print(f"Wrote: {out_dir / 'index.html'}")
    print(f"Status: {summary['status']} ({summary['n_reviewed']} / {summary['n_total']} reviewed)")


if __name__ == "__main__":
    main()

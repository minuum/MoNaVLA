#!/usr/bin/env python3
"""
Evaluate V5 pseudo/perception signals against a human-reviewed bbox truth file.

If the truth file still has pending rows, the script emits a pending summary
instead of fabricated metrics.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent.parent
TRUTH_PATH = ROOT / "docs" / "v5" / "bbox_truth_mini.json"
STEP1_PATH = ROOT / "docs" / "v5" / "bbox_nav_step1" / "bbox_dataset.json"
GROUNDING_PATH = ROOT / "ROS_action" / "v5_data_bak" / "v5_grounding.json"
OUT_DIR = ROOT / "docs" / "v5" / "bbox_truth_eval"

COARSE_LEFT_MAX = 1.0 / 3.0
COARSE_RIGHT_MIN = 2.0 / 3.0


def load_json(path: Path):
    return json.loads(path.read_text())


def select_grounding_bbox(frame_data: dict) -> Tuple[Optional[dict], bool]:
    valid = frame_data.get("valid_bboxes", []) or []
    all_boxes = frame_data.get("bboxes", []) or []
    keywords = ("basket", "gray box", "box", "container", "gray")

    fullscreen_only = bool(all_boxes) and not valid
    for box in valid:
        entity = str(box.get("entity", "")).lower()
        if any(k in entity for k in keywords):
            return box, fullscreen_only
    if valid:
        return valid[0], fullscreen_only
    return None, fullscreen_only


def bbox_to_center_area(box: Optional[dict]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if not box:
        return None, None, None
    x1, y1, x2, y2 = [float(box[k]) for k in ("x1", "y1", "x2", "y2")]
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0, max(0.0, (x2 - x1) * (y2 - y1)))


def coarse_from_cx(cx: Optional[float]) -> str:
    if cx is None:
        return "not_visible"
    if cx < COARSE_LEFT_MAX:
        return "left"
    if cx > COARSE_RIGHT_MIN:
        return "right"
    return "center"


def goal_near_from_proxy(has_bbox: bool, cx: Optional[float], area: Optional[float]) -> bool:
    if not has_bbox or cx is None or area is None:
        return False
    return bool(area >= 0.27 and abs(cx - 0.5) <= 0.03125)


def iou_xyxy(box_a: List[float], box_b: List[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def mean(values: List[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def ratio(num: int, den: int) -> Optional[float]:
    return num / den if den else None


def build_step1_index(dataset: List[dict]) -> Dict[Tuple[str, int], dict]:
    idx = {}
    for ep in dataset:
        for frame in ep["frames"]:
            idx[(ep["episode"], int(frame["frame_idx"]))] = frame
    return idx


def summarize_rows(rows: List[dict]) -> dict:
    visible_rows = [r for r in rows if r["target_visible"]]
    invisible_rows = [r for r in rows if not r["target_visible"]]
    visible_with_pred = [r for r in visible_rows if r["grounding_has_bbox"]]
    invisible_with_pred = [r for r in invisible_rows if r["grounding_has_bbox"]]

    wrong_side_cases = [
        r for r in visible_rows
        if r["coarse_position"] in {"left", "right"}
    ]
    wrong_side_errors = [
        r for r in wrong_side_cases
        if r["grounding_coarse_position"] != r["coarse_position"]
    ]

    proxy_rows = [r for r in rows if r["step1_has_bbox"] is not None]

    return {
        "n_completed": len(rows),
        "n_visible": len(visible_rows),
        "n_invisible": len(invisible_rows),
        "grounding": {
            "detection_recall": ratio(len(visible_with_pred), len(visible_rows)),
            "false_positive_rate": ratio(len(invisible_with_pred), len(invisible_rows)),
            "mean_iou": mean([r["grounding_iou"] for r in visible_with_pred if r["grounding_iou"] is not None]),
            "mean_center_l1": mean([r["grounding_center_l1"] for r in visible_with_pred if r["grounding_center_l1"] is not None]),
            "mean_center_l2": mean([r["grounding_center_l2"] for r in visible_with_pred if r["grounding_center_l2"] is not None]),
            "mean_area_abs_error": mean([r["grounding_area_abs_error"] for r in visible_with_pred if r["grounding_area_abs_error"] is not None]),
            "wrong_side_rate": ratio(len(wrong_side_errors), len(wrong_side_cases)),
            "fullscreen_hallucination_rate": ratio(
                sum(1 for r in rows if r["grounding_fullscreen_only"]),
                len(rows),
            ),
        },
        "step1_proxy": {
            "has_bbox_agreement": ratio(
                sum(1 for r in proxy_rows if bool(r["step1_has_bbox"]) == bool(r["target_visible"])),
                len(proxy_rows),
            ),
            "mean_center_l1": mean([r["step1_center_l1"] for r in proxy_rows if r["step1_center_l1"] is not None]),
            "mean_area_abs_error": mean([r["step1_area_abs_error"] for r in proxy_rows if r["step1_area_abs_error"] is not None]),
            "coarse_position_agreement": ratio(
                sum(1 for r in proxy_rows if r["step1_coarse_position"] == r["coarse_position"]),
                len(proxy_rows),
            ),
            "goal_near_agreement": ratio(
                sum(1 for r in proxy_rows if r["step1_goal_near"] == r["goal_near"]),
                len(proxy_rows),
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth", default=str(TRUTH_PATH))
    args = parser.parse_args()

    truth_payload = load_json(Path(args.truth))
    annotations = truth_payload["annotations"] if isinstance(truth_payload, dict) else truth_payload
    step1_index = build_step1_index(load_json(STEP1_PATH))
    grounding = load_json(GROUNDING_PATH)

    completed = []
    pending = 0

    for ann in annotations:
        if ann.get("review_status") not in {"complete", "verified"}:
            pending += 1
            continue

        episode = ann["episode"]
        frame_idx = int(ann["frame_idx"])
        gt_box = ann.get("bbox_xyxy_norm")
        target_visible = bool(ann["target_visible"])
        coarse_position = ann.get("coarse_position") or ("not_visible" if not target_visible else None)
        goal_near = ann.get("goal_near")

        grounding_frame = grounding.get(episode, {}).get(str(frame_idx), {})
        grounding_box, fullscreen_only = select_grounding_bbox(grounding_frame)
        g_cx, g_cy, g_area = bbox_to_center_area(grounding_box)

        gt_cx = gt_cy = gt_area = None
        if gt_box:
            gt_cx = (float(gt_box[0]) + float(gt_box[2])) / 2.0
            gt_cy = (float(gt_box[1]) + float(gt_box[3])) / 2.0
            gt_area = max(0.0, (float(gt_box[2]) - float(gt_box[0])) * (float(gt_box[3]) - float(gt_box[1])))

        step1 = step1_index.get((episode, frame_idx))
        s_has = None if step1 is None else bool(step1["has_bbox"])
        s_cx = None if step1 is None else float(step1["cx"])
        s_cy = None if step1 is None else float(step1["cy"])
        s_area = None if step1 is None else float(step1["area"])

        completed.append(
            {
                "episode": episode,
                "path_type": ann["path_type"],
                "frame_idx": frame_idx,
                "anchor_tag": ann.get("anchor_tag"),
                "target_visible": target_visible,
                "coarse_position": coarse_position,
                "goal_near": goal_near,
                "grounding_has_bbox": grounding_box is not None,
                "grounding_fullscreen_only": fullscreen_only,
                "grounding_coarse_position": coarse_from_cx(g_cx),
                "grounding_iou": (
                    iou_xyxy(gt_box, [grounding_box["x1"], grounding_box["y1"], grounding_box["x2"], grounding_box["y2"]])
                    if gt_box and grounding_box
                    else None
                ),
                "grounding_center_l1": (
                    abs(g_cx - gt_cx) + abs(g_cy - gt_cy)
                    if gt_cx is not None and g_cx is not None and gt_cy is not None and g_cy is not None
                    else None
                ),
                "grounding_center_l2": (
                    math.sqrt((g_cx - gt_cx) ** 2 + (g_cy - gt_cy) ** 2)
                    if gt_cx is not None and g_cx is not None and gt_cy is not None and g_cy is not None
                    else None
                ),
                "grounding_area_abs_error": (
                    abs(g_area - gt_area)
                    if gt_area is not None and g_area is not None
                    else None
                ),
                "step1_has_bbox": s_has,
                "step1_cx": s_cx,
                "step1_cy": s_cy,
                "step1_area": s_area,
                "step1_center_l1": (
                    abs(s_cx - gt_cx) + abs(s_cy - gt_cy)
                    if s_cx is not None and gt_cx is not None and s_cy is not None and gt_cy is not None
                    else None
                ),
                "step1_area_abs_error": (
                    abs(s_area - gt_area)
                    if s_area is not None and gt_area is not None
                    else None
                ),
                "step1_coarse_position": coarse_from_cx(s_cx),
                "step1_goal_near": goal_near_from_proxy(bool(s_has), s_cx, s_area) if s_has is not None else None,
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_path = defaultdict(list)
    for row in completed:
        by_path[row["path_type"]].append(row)

    payload = {
        "truth_path": str(Path(args.truth)),
        "n_annotations_total": len(annotations),
        "n_annotations_completed": len(completed),
        "n_annotations_pending": pending,
        "status": "pending_human_review" if not completed else "ok",
        "overall": summarize_rows(completed) if completed else None,
        "by_path": {path: summarize_rows(rows) for path, rows in sorted(by_path.items())},
        "rows": completed,
    }

    out_json = OUT_DIR / "summary.json"
    out_json.write_text(json.dumps(payload, indent=2))
    print(f"Wrote: {out_json}")
    print(f"Completed annotations: {len(completed)} / {len(annotations)}")


if __name__ == "__main__":
    main()

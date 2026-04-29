#!/usr/bin/env python3
"""
Analyze proxy-signal candidates for V5 without collecting new data.

Outputs:
- docs/v5/v5_proxy_signal_stats.json

Important:
- Raw action/path statistics are computed on the full 150-episode V5 dataset.
- Geometry/proxy statistics are computed on the currently grounded bbox cache
  (docs/v5/bbox_nav_step1/bbox_dataset.json), which covers 45 episodes.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

import h5py


ROOT = Path(__file__).resolve().parents[2]
V5_DIR = ROOT / "ROS_action" / "mobile_vla_dataset_v5"
BBOX_DATASET = ROOT / "docs" / "v5" / "bbox_nav_step1" / "bbox_dataset.json"
OUT_FILE = ROOT / "docs" / "v5" / "v5_proxy_signal_stats.json"


def percentile(values, q):
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return float(xs[lo])
    frac = pos - lo
    return float(xs[lo] * (1 - frac) + xs[hi] * frac)


def summarize(values):
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "mean": round(float(mean(values)), 6),
        "median": round(float(median(values)), 6),
        "min": round(float(min(values)), 6),
        "max": round(float(max(values)), 6),
        "p25": round(percentile(values, 0.25), 6),
        "p75": round(percentile(values, 0.75), 6),
        "p90": round(percentile(values, 0.90), 6),
    }


def path_type_from_stem(stem: str) -> str:
    for pt in (
        "center_straight",
        "center_left",
        "center_right",
        "left_straight",
        "left_left",
        "left_right",
        "right_straight",
        "right_left",
        "right_right",
    ):
        if pt in stem:
            return pt
    return "unknown"


def discretize_action(a):
    x = float(a[0])
    y = float(a[1])
    az = float(a[2]) if len(a) > 2 else 0.0
    is_x = abs(x) > 0.3
    is_y = abs(y) > 0.3

    if not is_x and not is_y:
        if az > 0.1:
            return 6
        if az < -0.1:
            return 7
        return 0
    if x > 0.3:
        if y > 0.3:
            return 4
        if y < -0.3:
            return 5
        return 1
    if abs(x) < 0.3:
        if y > 0.3:
            return 2
        if y < -0.3:
            return 3
        return 0
    return 0


def analyze_raw_v5():
    files = sorted(V5_DIR.glob("episode_*.h5"))
    path_counts = Counter()
    class_counts = Counter()
    frame_counts = []
    per_path_class = defaultdict(Counter)

    for fp in files:
        pt = path_type_from_stem(fp.stem)
        path_counts[pt] += 1
        with h5py.File(fp, "r") as hf:
            actions = hf["actions"][:]
            frame_counts.append(len(actions))
            for a in actions:
                cls = discretize_action(a)
                class_counts[cls] += 1
                per_path_class[pt][cls] += 1

    return {
        "episode_count": len(files),
        "total_frames": sum(frame_counts),
        "frame_count_summary": summarize(frame_counts),
        "path_type_episode_counts": dict(sorted(path_counts.items())),
        "global_action_class_counts": dict(sorted(class_counts.items())),
        "per_path_action_class_counts": {
            pt: dict(sorted(cnt.items()))
            for pt, cnt in sorted(per_path_class.items())
        },
    }


def episode_proxy_rows(ep):
    frames = ep["frames"]
    rows = []
    prev = None
    for i, fr in enumerate(frames):
        cx = float(fr["cx"])
        cy = float(fr["cy"])
        area = float(fr["area"])
        has_bbox = bool(fr["has_bbox"])
        row = {
            "frame_idx": int(fr["frame_idx"]),
            "norm_t": i / max(len(frames) - 1, 1),
            "cx": cx,
            "cy": cy,
            "area": area,
            "has_bbox": has_bbox,
            "center_error_x": abs(cx - 0.5),
            "center_error_y_to_075": abs(cy - 0.75),
            "delta_area": None if prev is None else area - prev["area"],
            "delta_cx": None if prev is None else cx - prev["cx"],
            "delta_cy": None if prev is None else cy - prev["cy"],
        }
        rows.append(row)
        prev = row
    return rows


def stable_bbox_consistency(rows, last_k=5, cx_tol=0.08, area_tol=0.08):
    tail = rows[-last_k:]
    if not tail:
        return None
    valid = [r for r in tail if r["has_bbox"]]
    if not valid:
        return 0.0
    if len(valid) == 1:
        return 1.0

    stable_pairs = 0
    total_pairs = 0
    for a, b in zip(valid[:-1], valid[1:]):
        total_pairs += 1
        if abs(b["cx"] - a["cx"]) <= cx_tol and abs(b["area"] - a["area"]) <= area_tol:
            stable_pairs += 1
    if total_pairs == 0:
        return 1.0
    return stable_pairs / total_pairs


def analyze_bbox_proxy():
    data = json.loads(BBOX_DATASET.read_text())

    global_buckets = defaultdict(list)
    by_path = defaultdict(lambda: defaultdict(list))
    episode_summaries = []

    for ep in data:
        pt = ep["path_type"]
        rows = episode_proxy_rows(ep)
        n = len(rows)
        early = rows[: max(1, n // 3)]
        mid = rows[max(1, n // 3): max(2, (2 * n) // 3)]
        late3 = rows[-3:]
        late5 = rows[-5:]

        def add_rows(bucket_name, bucket_rows):
            for r in bucket_rows:
                global_buckets[f"{bucket_name}.area"].append(r["area"])
                global_buckets[f"{bucket_name}.center_error_x"].append(r["center_error_x"])
                global_buckets[f"{bucket_name}.center_error_y_to_075"].append(r["center_error_y_to_075"])
                by_path[pt][f"{bucket_name}.area"].append(r["area"])
                by_path[pt][f"{bucket_name}.center_error_x"].append(r["center_error_x"])
                by_path[pt][f"{bucket_name}.center_error_y_to_075"].append(r["center_error_y_to_075"])
                if r["delta_area"] is not None:
                    global_buckets[f"{bucket_name}.abs_delta_area"].append(abs(r["delta_area"]))
                    global_buckets[f"{bucket_name}.abs_delta_cx"].append(abs(r["delta_cx"]))
                    global_buckets[f"{bucket_name}.abs_delta_cy"].append(abs(r["delta_cy"]))
                    by_path[pt][f"{bucket_name}.abs_delta_area"].append(abs(r["delta_area"]))
                    by_path[pt][f"{bucket_name}.abs_delta_cx"].append(abs(r["delta_cx"]))
                    by_path[pt][f"{bucket_name}.abs_delta_cy"].append(abs(r["delta_cy"]))

        add_rows("early", early)
        add_rows("mid", mid)
        add_rows("late3", late3)
        add_rows("late5", late5)

        consistency = stable_bbox_consistency(rows, last_k=5)
        global_buckets["late5.consistency"].append(consistency)
        by_path[pt]["late5.consistency"].append(consistency)

        episode_summaries.append(
            {
                "episode": ep["episode"],
                "path_type": pt,
                "n_frames": n,
                "last_area": rows[-1]["area"],
                "last_center_error_x": rows[-1]["center_error_x"],
                "last_center_error_y_to_075": rows[-1]["center_error_y_to_075"],
                "late5_consistency": consistency,
            }
        )

    threshold_candidates = {
        "goal_near_area_min__late3_p25": round(percentile(global_buckets["late3.area"], 0.25), 6),
        "goal_near_area_min__late5_p25": round(percentile(global_buckets["late5.area"], 0.25), 6),
        "goal_near_center_error_x_max__late3_p75": round(percentile(global_buckets["late3.center_error_x"], 0.75), 6),
        "goal_near_center_error_x_max__late5_p75": round(percentile(global_buckets["late5.center_error_x"], 0.75), 6),
        "goal_near_center_error_y_to_075_max__late3_p75": round(percentile(global_buckets["late3.center_error_y_to_075"], 0.75), 6),
        "goal_near_center_error_y_to_075_max__late5_p75": round(percentile(global_buckets["late5.center_error_y_to_075"], 0.75), 6),
        "plateau_abs_delta_area_max__late3_p75": round(percentile(global_buckets["late3.abs_delta_area"], 0.75), 6),
        "plateau_abs_delta_area_max__late5_p75": round(percentile(global_buckets["late5.abs_delta_area"], 0.75), 6),
        "stability_abs_delta_cx_max__late3_p75": round(percentile(global_buckets["late3.abs_delta_cx"], 0.75), 6),
        "stability_abs_delta_cx_max__late5_p75": round(percentile(global_buckets["late5.abs_delta_cx"], 0.75), 6),
        "recent_bbox_consistency_min__late5_p25": round(percentile(global_buckets["late5.consistency"], 0.25), 6),
    }

    return {
        "grounded_episode_count": len(data),
        "grounded_total_frames": sum(len(ep["frames"]) for ep in data),
        "global_proxy_stats": {
            key: summarize(vals) for key, vals in sorted(global_buckets.items())
        },
        "per_path_proxy_stats": {
            pt: {key: summarize(vals) for key, vals in sorted(stats.items())}
            for pt, stats in sorted(by_path.items())
        },
        "threshold_candidates_v0": threshold_candidates,
        "episode_summary_preview": episode_summaries[:10],
    }


def main():
    raw = analyze_raw_v5()
    bbox = analyze_bbox_proxy()

    payload = {
        "notes": {
            "raw_scope": "Full 150-episode ROS_action/mobile_vla_dataset_v5",
            "geometry_scope": "Grounded bbox cache docs/v5/bbox_nav_step1/bbox_dataset.json (45 episodes)",
            "warning": "Proxy thresholds below are derived from the grounded 45-episode subset, not from all 150 episodes.",
        },
        "raw_v5": raw,
        "bbox_proxy": bbox,
    }

    OUT_FILE.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {OUT_FILE}")
    print("Threshold candidates v0:")
    for k, v in bbox["threshold_candidates_v0"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

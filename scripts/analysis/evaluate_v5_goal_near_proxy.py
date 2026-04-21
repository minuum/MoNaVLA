#!/usr/bin/env python3
"""
Evaluate goal-near proxy rules on the current grounded V5 bbox cache.

Outputs:
- docs/v5/v5_goal_near_eval.json

Current scope:
- docs/v5/bbox_nav_step1/bbox_dataset.json (45 grounded episodes)
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BBOX_DATASET = ROOT / "docs" / "v5" / "bbox_nav_step1" / "bbox_dataset.json"
OUT_FILE = ROOT / "docs" / "v5" / "v5_goal_near_eval.json"


def goal_near_v0(fr: dict) -> bool:
    return (
        bool(fr["has_bbox"])
        and float(fr["area"]) >= 0.27
        and abs(float(fr["cx"]) - 0.5) <= 0.03125
    )


def goal_near_v0_strict(fr: dict) -> bool:
    prev_cx = fr.get("_prev_cx")
    abs_delta_cx = 0.0 if prev_cx is None else abs(float(fr["cx"]) - float(prev_cx))
    return (
        bool(fr["has_bbox"])
        and float(fr["area"]) >= 0.31
        and abs(float(fr["cx"]) - 0.5) <= 0.039062
        and abs_delta_cx <= 0.0625
    )


def add_prev_fields(frames: list[dict]) -> list[dict]:
    out = []
    prev_cx = None
    for fr in frames:
        row = dict(fr)
        row["_prev_cx"] = prev_cx
        out.append(row)
        prev_cx = float(fr["cx"])
    return out


def summarize_counts(episodes, rule_fn):
    by_path = defaultdict(
        lambda: {
            "episodes": 0,
            "early_total": 0,
            "early_positive": 0,
            "late5_total": 0,
            "late5_positive": 0,
            "late5_episode_any": 0,
            "late5_episode_all": 0,
        }
    )

    for ep in episodes:
        path_type = ep["path_type"]
        frames = add_prev_fields(ep["frames"])
        n = len(frames)
        early = frames[: max(1, n // 3)]
        late5 = frames[-5:]

        early_hits = sum(1 for fr in early if rule_fn(fr))
        late_hits = sum(1 for fr in late5 if rule_fn(fr))

        stats = by_path[path_type]
        stats["episodes"] += 1
        stats["early_total"] += len(early)
        stats["early_positive"] += early_hits
        stats["late5_total"] += len(late5)
        stats["late5_positive"] += late_hits
        if late_hits > 0:
            stats["late5_episode_any"] += 1
        if late_hits == len(late5):
            stats["late5_episode_all"] += 1

    global_stats = {
        "episodes": sum(v["episodes"] for v in by_path.values()),
        "early_total": sum(v["early_total"] for v in by_path.values()),
        "early_positive": sum(v["early_positive"] for v in by_path.values()),
        "late5_total": sum(v["late5_total"] for v in by_path.values()),
        "late5_positive": sum(v["late5_positive"] for v in by_path.values()),
        "late5_episode_any": sum(v["late5_episode_any"] for v in by_path.values()),
        "late5_episode_all": sum(v["late5_episode_all"] for v in by_path.values()),
    }

    def enrich(stats):
        stats = dict(stats)
        stats["early_positive_rate"] = round(stats["early_positive"] / max(stats["early_total"], 1), 6)
        stats["late5_frame_hit_rate"] = round(stats["late5_positive"] / max(stats["late5_total"], 1), 6)
        stats["late5_episode_any_rate"] = round(stats["late5_episode_any"] / max(stats["episodes"], 1), 6)
        stats["late5_episode_all_rate"] = round(stats["late5_episode_all"] / max(stats["episodes"], 1), 6)
        return stats

    return {
        "global": enrich(global_stats),
        "by_path": {pt: enrich(stats) for pt, stats in sorted(by_path.items())},
    }


def main():
    episodes = json.loads(BBOX_DATASET.read_text())
    out = {
        "dataset_scope": "docs/v5/bbox_nav_step1/bbox_dataset.json (45 grounded episodes)",
        "rules": {
            "goal_near_v0": {
                "definition": {
                    "has_bbox": True,
                    "area_min": 0.27,
                    "center_error_x_max": 0.03125,
                },
                "metrics": summarize_counts(episodes, goal_near_v0),
            },
            "goal_near_v0_strict": {
                "definition": {
                    "has_bbox": True,
                    "area_min": 0.31,
                    "center_error_x_max": 0.039062,
                    "abs_delta_cx_max": 0.0625,
                },
                "metrics": summarize_counts(episodes, goal_near_v0_strict),
            },
        },
    }
    OUT_FILE.write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Analyze goal-near proxy timing on the current grounded V5 bbox cache.

Outputs:
- docs/v5/v5_goal_near_timing.json
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BBOX_DATASET = ROOT / "docs" / "v5" / "bbox_nav_step1" / "bbox_dataset.json"
OUT_FILE = ROOT / "docs" / "v5" / "v5_goal_near_timing.json"


def goal_near_v0(fr: dict) -> bool:
    return (
        bool(fr["has_bbox"])
        and float(fr["area"]) >= 0.27
        and abs(float(fr["cx"]) - 0.5) <= 0.03125
    )


def onset_stats(flags: list[bool], n: int) -> dict:
    first_idx = next((i for i, x in enumerate(flags) if x), None)
    late5 = flags[-5:]
    early = flags[: max(1, n // 3)]

    trailing_run = 0
    for x in reversed(flags):
        if x:
            trailing_run += 1
        else:
            break

    return {
        "first_positive_idx": first_idx,
        "first_positive_norm": None if first_idx is None else round(first_idx / max(n - 1, 1), 6),
        "positive_frames": sum(flags),
        "positive_rate": round(sum(flags) / max(n, 1), 6),
        "early_positive_frames": sum(early),
        "late5_positive_frames": sum(late5),
        "late5_run_at_end": trailing_run,
        "fires_in_early_third": bool(sum(early) > 0),
        "fires_in_late5": bool(sum(late5) > 0),
        "fires_all_late5": bool(sum(late5) == len(late5)),
    }


def main():
    episodes = json.loads(BBOX_DATASET.read_text())
    per_episode = []
    by_path = defaultdict(list)

    for ep in episodes:
        frames = ep["frames"]
        n = len(frames)
        flags = [goal_near_v0(fr) for fr in frames]
        stats = onset_stats(flags, n)
        row = {
            "episode": ep["episode"],
            "path_type": ep["path_type"],
            "n_frames": n,
            **stats,
        }
        per_episode.append(row)
        by_path[ep["path_type"]].append(row)

    path_summary = {}
    for pt, rows in sorted(by_path.items()):
        with_onset = [r["first_positive_norm"] for r in rows if r["first_positive_norm"] is not None]
        late5_hits = [r["late5_positive_frames"] for r in rows]
        early_fires = sum(1 for r in rows if r["fires_in_early_third"])
        all_late5 = sum(1 for r in rows if r["fires_all_late5"])
        trailing = [r["late5_run_at_end"] for r in rows]
        path_summary[pt] = {
            "episodes": len(rows),
            "episodes_with_any_positive": sum(1 for r in rows if r["first_positive_idx"] is not None),
            "episodes_firing_in_early_third": early_fires,
            "episodes_firing_all_late5": all_late5,
            "mean_first_positive_norm": None if not with_onset else round(sum(with_onset) / len(with_onset), 6),
            "mean_late5_positive_frames": round(sum(late5_hits) / len(late5_hits), 6),
            "mean_late5_run_at_end": round(sum(trailing) / len(trailing), 6),
            "episodes_detail": rows,
        }

    out = {
        "rule": {
            "name": "goal_near_v0",
            "definition": {
                "has_bbox": True,
                "area_min": 0.27,
                "center_error_x_max": 0.03125,
            },
        },
        "dataset_scope": "docs/v5/bbox_nav_step1/bbox_dataset.json (45 grounded episodes)",
        "path_summary": path_summary,
        "top_early_trigger_episodes": sorted(
            [r for r in per_episode if r["first_positive_norm"] is not None],
            key=lambda r: r["first_positive_norm"],
        )[:15],
        "weak_late5_hold_episodes": sorted(
            per_episode,
            key=lambda r: (r["late5_positive_frames"], r["late5_run_at_end"]),
        )[:15],
    }

    OUT_FILE.write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()

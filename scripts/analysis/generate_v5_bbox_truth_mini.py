#!/usr/bin/env python3
"""
Generate a review scaffold for a mini human-verified V5 bbox truth set.

This script does not claim to create ground truth. It creates a deterministic
review queue with:
  - 2 episodes per path type
  - 4 anchor frames per episode
  - seed bbox suggestions from existing Pure-HF Kosmos grounding cache
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_PATH = ROOT / "docs" / "v5" / "bbox_truth_mini.json"
DATASET_PATH = ROOT / "docs" / "v5" / "bbox_nav_step1" / "bbox_dataset.json"
GROUNDING_PATH = ROOT / "ROS_action" / "v5_data_bak" / "v5_grounding.json"
IMAGE_ROOT = ROOT / "ROS_action" / "mobile_vla_dataset_v5(Image)"

PATH_TYPES = [
    "center_straight",
    "center_left",
    "center_right",
    "left_straight",
    "left_left",
    "left_right",
    "right_straight",
    "right_left",
    "right_right",
]
ANCHORS = [
    ("early", 0.15),
    ("mid", 0.40),
    ("late", 0.70),
    ("final", 0.90),
]
TURN_CLASSES = {2, 3, 4, 5, 6, 7}


def load_json(path: Path):
    return json.loads(path.read_text())


def choose_two_episodes(eps: List[dict]) -> List[dict]:
    eps = sorted(eps, key=lambda x: x["episode"])
    if len(eps) <= 2:
        return eps
    return [eps[0], eps[-1]]


def choose_anchor_frames(frames: List[dict], path_type: str) -> List[dict]:
    chosen = []
    used = set()
    n = len(frames)
    is_curve = not path_type.endswith("straight")

    for anchor_name, anchor_p in ANCHORS:
        target_idx = int(round((n - 1) * anchor_p))
        candidates = []
        for i, fr in enumerate(frames):
            score = abs(i - target_idx)
            if is_curve and anchor_name == "mid":
                if fr["gt_class"] in TURN_CLASSES:
                    score -= 0.35
            candidates.append((score, i, fr))
        candidates.sort(key=lambda x: (x[0], x[1]))
        picked = None
        for _, i, fr in candidates:
            if i not in used:
                picked = (i, fr)
                break
        if picked is None:
            picked = (candidates[0][1], candidates[0][2])
        used.add(picked[0])
        chosen.append(
            {
                "anchor_tag": anchor_name,
                "normalized_progress": round(picked[0] / max(n - 1, 1), 4),
                "frame": picked[1],
            }
        )
    return chosen


def select_seed_bbox(frame_data: dict) -> Optional[dict]:
    valid = frame_data.get("valid_bboxes", []) or []
    all_boxes = frame_data.get("bboxes", []) or []
    keywords = ("basket", "gray box", "box", "container", "gray")

    for box in valid:
        entity = str(box.get("entity", "")).lower()
        if any(k in entity for k in keywords):
            return box
    if valid:
        return valid[0]
    for box in all_boxes:
        if not box.get("is_fullscreen", False):
            return box
    return None


def coarse_from_bbox(box: Optional[dict]) -> str:
    if not box:
        return "not_visible"
    cx = (float(box["x1"]) + float(box["x2"])) / 2.0
    if cx < 1.0 / 3.0:
        return "left"
    if cx > 2.0 / 3.0:
        return "right"
    return "center"


def goal_near_seed(box: Optional[dict]) -> Optional[bool]:
    if not box:
        return None
    cx = (float(box["x1"]) + float(box["x2"])) / 2.0
    area = float(box.get("area", 0.0))
    return bool(area >= 0.27 and abs(cx - 0.5) <= 0.03125)


def build_annotations() -> Dict:
    dataset = load_json(DATASET_PATH)
    grounding = load_json(GROUNDING_PATH) if GROUNDING_PATH.exists() else {}
    by_path = defaultdict(list)
    for ep in dataset:
        by_path[ep["path_type"]].append(ep)

    annotations = []
    for path_type in PATH_TYPES:
        for ep in choose_two_episodes(by_path[path_type]):
            for item in choose_anchor_frames(ep["frames"], path_type):
                frame_idx = int(item["frame"]["frame_idx"])
                g_frame = grounding.get(ep["episode"], {}).get(str(frame_idx), {})
                seed_box = select_seed_bbox(g_frame)
                image_path = (
                    IMAGE_ROOT / ep["episode"] / f"frame_{frame_idx:04d}.png"
                )
                annotations.append(
                    {
                        "review_status": "pending",
                        "episode": ep["episode"],
                        "path_type": path_type,
                        "frame_idx": frame_idx,
                        "frame_path": str(image_path),
                        "anchor_tag": item["anchor_tag"],
                        "normalized_progress": item["normalized_progress"],
                        "gt_action_class": int(item["frame"]["gt_class"]),
                        "seed_source": "v5_grounding",
                        "seed_entity": seed_box.get("entity") if seed_box else None,
                        "seed_bbox_xyxy_norm": (
                            [
                                round(float(seed_box["x1"]), 4),
                                round(float(seed_box["y1"]), 4),
                                round(float(seed_box["x2"]), 4),
                                round(float(seed_box["y2"]), 4),
                            ]
                            if seed_box
                            else None
                        ),
                        "seed_has_bbox": seed_box is not None,
                        "seed_coarse_position": coarse_from_bbox(seed_box),
                        "seed_goal_near": goal_near_seed(seed_box),
                        "seed_caption": g_frame.get("caption"),
                        "target_visible": None,
                        "bbox_xyxy_norm": None,
                        "coarse_position": None,
                        "goal_near": None,
                        "notes": "",
                    }
                )

    return {
        "version": 1,
        "dataset_scope": {
            "raw_v5": "ROS_action/mobile_vla_dataset_v5 (150 episodes / 2626 frames)",
            "grounded_subset": "docs/v5/bbox_nav_step1/bbox_dataset.json (45 episodes / 794 frames)",
        },
        "sampling_rule": {
            "episodes_per_path": 2,
            "frames_per_episode": 4,
            "anchors": [dict(anchor_tag=a, normalized_progress=p) for a, p in ANCHORS],
            "curve_mid_bias": "prefer a turning class near the mid anchor on non-straight paths",
        },
        "annotations": annotations,
    }


def main() -> None:
    payload = build_annotations()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Wrote: {OUT_PATH}")
    print(f"Annotations: {len(payload['annotations'])}")


if __name__ == "__main__":
    main()

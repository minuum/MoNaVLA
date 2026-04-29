#!/usr/bin/env python3
"""
Generate a deterministic initial-frame review scaffold for the 2026-04-27
grounding proof:
  - 1 episode per path family
  - 2 early frames per episode (default: frame 0 and frame 2, nearest available)
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_PATH = ROOT / "docs" / "v5" / "bbox_truth_initial18.json"
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
TARGET_FRAMES = [0, 2]


def load_json(path: Path):
    return json.loads(path.read_text())


def choose_episode(eps: List[dict]) -> dict:
    return sorted(eps, key=lambda x: x["episode"])[0]


def choose_initial_frames(frames: List[dict]) -> List[dict]:
    picked = []
    used = set()
    for target_idx in TARGET_FRAMES:
        candidates = sorted(
            frames,
            key=lambda fr: (
                abs(int(fr["frame_idx"]) - target_idx),
                int(fr["frame_idx"]),
            ),
        )
        chosen = None
        for frame in candidates:
            frame_idx = int(frame["frame_idx"])
            if frame_idx not in used:
                chosen = frame
                break
        if chosen is None:
            chosen = candidates[0]
        used.add(int(chosen["frame_idx"]))
        picked.append(chosen)
    return picked


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
        ep = choose_episode(by_path[path_type])
        for frame in choose_initial_frames(ep["frames"]):
            frame_idx = int(frame["frame_idx"])
            g_frame = grounding.get(ep["episode"], {}).get(str(frame_idx), {})
            seed_box = select_seed_bbox(g_frame)
            image_path = IMAGE_ROOT / ep["episode"] / f"frame_{frame_idx:04d}.png"
            annotations.append(
                {
                    "review_status": "pending",
                    "episode": ep["episode"],
                    "path_type": path_type,
                    "frame_idx": frame_idx,
                    "frame_path": str(image_path),
                    "anchor_tag": "initial",
                    "normalized_progress": 0.0,
                    "gt_action_class": int(frame["gt_class"]),
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
            "grounded_subset": "docs/v5/bbox_nav_step1/bbox_dataset.json",
            "review_goal": "9 path families x 2 initial frames = 18-frame Monday grounding proof set",
        },
        "sampling_rule": {
            "episodes_per_path": 1,
            "frames_per_episode": 2,
            "target_frames": TARGET_FRAMES,
            "frame_selection": "pick nearest available frame to each target without duplicates",
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

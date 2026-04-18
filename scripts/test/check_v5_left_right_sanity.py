#!/usr/bin/env python3
"""
V5 LEFT/RIGHT sanity benchmark

목적:
- GT가 LEFT/RIGHT인 샘플만 모아 검증
- 모델 예측과 바스켓 좌우 위치를 같이 확인
- 사람이 바로 볼 수 있도록 검사용 이미지를 저장

기본 대상:
- Exp11 latest checkpoint / config
"""

import os
import sys
import gc
import json
import argparse
import io
import contextlib
from pathlib import Path

import cv2
import torch
import numpy as np
import yaml

# MPI hang 방지
import lightning.fabric.plugins.environments.mpi as _mpi_env_mod
_mpi_env_mod._MPI4PY_AVAILABLE = False

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "third_party" / "RoboVLMs"))

import robovlms.model.backbone as backbone_mod
import robovlms.model.policy_head as policy_head_mod
import robovlms.train.base_trainer as base_trainer_mod
import robovlms.train as train_mod

from robovlms.model.backbone.robokosmos import RoboKosMos
from robovlm_nav.models.policy_head.nav_policy_impl import (
    MobileVLAClassificationDecoder,
    MobileVLALSTMDecoder,
)
from robovlm_nav.models.policy_head.hybrid_action_head import HybridActionHead
from robovlm_nav.trainer.nav_trainer import NavTrainer

setattr(backbone_mod, "RoboKosMos", RoboKosMos)
setattr(backbone_mod, "RoboVLM-Nav", RoboKosMos)
setattr(policy_head_mod, "MobileVLAClassificationDecoder", MobileVLAClassificationDecoder)
setattr(policy_head_mod, "MobileVLALSTMDecoder", MobileVLALSTMDecoder)
setattr(policy_head_mod, "NavPolicy", MobileVLAClassificationDecoder)
setattr(policy_head_mod, "NavPolicyRegression", MobileVLALSTMDecoder)
setattr(policy_head_mod, "HybridActionHead", HybridActionHead)
base_trainer_mod.BaseTrainer = NavTrainer
setattr(train_mod, "NavTrainer", NavTrainer)
setattr(train_mod, "BaseTrainer", NavTrainer)

import main as main_mod
main_mod.BaseTrainer = NavTrainer

from main import load_config
from robovlms.train.mobile_vla_trainer import MobileVLATrainer
from robovlm_nav.datasets.nav_dataset import NavDataset


CLASS_NAMES_8 = {
    0: "STOP",
    1: "FORWARD",
    2: "LEFT",
    3: "RIGHT",
    4: "FWD+L",
    5: "FWD+R",
    6: "TURN_L",
    7: "TURN_R",
}


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config",
        default=str(ROOT / "configs" / "mobile_vla_v5_exp11_google_robot_8cls.json"),
    )
    ap.add_argument(
        "--ckpt",
        default=str(
            ROOT
            / "runs"
            / "v5_nav"
            / "kosmos"
            / "mobile_vla_v5_exp11"
            / "2026-04-16"
            / "v5-exp11-google-robot-8cls"
            / "epoch_epoch=epoch=14-val_loss=val_loss=1.010.ckpt"
        ),
    )
    ap.add_argument(
        "--data",
        default=str(ROOT / "ROS_action" / "mobile_vla_dataset_v5"),
    )
    ap.add_argument("--train_split", type=float, default=0.8)
    ap.add_argument("--limit_per_class", type=int, default=10)
    ap.add_argument("--limit_per_subset", type=int, default=0)
    ap.add_argument(
        "--wanted_ids",
        default="2,3",
        help="Comma-separated class ids to include in sanity selection. Example: 2,3,4,5",
    )
    ap.add_argument(
        "--subset_patterns",
        default="center_left,left_left,center_right,right_right",
        help="Comma-separated episode stem patterns to stratify sanity samples.",
    )
    ap.add_argument(
        "--split_file",
        default="",
        help="Optional YAML split file with fixed dataset indices to use before dynamic discovery.",
    )
    ap.add_argument("--output_dir", default=str(ROOT / "runs" / "sanity_checks" / "left_right"))
    return ap.parse_args()


def fix_paths(configs):
    vlm_path = str(ROOT / ".vlms" / "kosmos-2-patch14-224")

    def _fix(obj):
        for k, v in obj.items():
            if isinstance(v, str) and "kosmos-2-patch14-224" in v:
                obj[k] = vlm_path
            elif isinstance(v, dict):
                _fix(v)

    _fix(configs)
    if isinstance(configs.get("vlm"), dict):
        configs["vlm"]["pretrained_model_name_or_path"] = vlm_path
    if isinstance(configs.get("tokenizer"), dict):
        configs["tokenizer"]["pretrained_model_name_or_path"] = vlm_path


def load_model(config_path, ckpt_path):
    configs = load_config(config_path)
    fix_paths(configs)
    with contextlib.redirect_stdout(io.StringIO()):
        wrapper = MobileVLATrainer(configs)

    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    full_sd = ckpt.get("model_state_dict", ckpt.get("state_dict", {}))
    filtered = {}
    for k, v in full_sd.items():
        if any(x in k for x in ["image_to_text_projection", "act_head", "policy_head", "resampler", "action_token", "lora"]):
            new_k = k.replace("model.", "", 1) if k.startswith("model.") and not hasattr(wrapper, "model") else k
            filtered[new_k] = v
    wrapper.load_state_dict(filtered, strict=False)
    del full_sd, ckpt
    gc.collect()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    wrapper.to(device).eval()
    if device == "cuda":
        wrapper.half()
    return wrapper, device, configs


def parse_gt(batch):
    if "action_chunck" in batch:
        ac = batch["action_chunck"].detach().cpu().numpy()
        return int(ac[0, 0, 0])
    return None


def parse_logits(outputs, t=0, batch_idx=0):
    if isinstance(outputs, (tuple, list)):
        outputs = outputs[0]
    if outputs is None or not isinstance(outputs, torch.Tensor):
        return None
    arr = outputs.detach().cpu().float().numpy()
    if arr.ndim == 4:
        logits = arr[batch_idx, t, 0, :]
    elif arr.ndim == 3:
        logits = arr[batch_idx, t, :]
    elif arr.ndim == 2:
        logits = arr[batch_idx, :]
    else:
        logits = arr
    return int(np.argmax(logits)), logits


def tensor_to_image(rgb_tensor):
    img = rgb_tensor.detach().cpu().float().permute(1, 2, 0).numpy()
    img = np.nan_to_num(img)
    # robust min-max for inspection only
    lo, hi = np.percentile(img, 1), np.percentile(img, 99)
    if hi - lo > 1e-6:
        img = (img - lo) / (hi - lo)
    img = np.clip(img, 0, 1)
    return (img * 255).astype(np.uint8)


def detect_basket_side(img_rgb):
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    _, s, v = cv2.split(hsv)
    mask = ((s < 65) & (v > 35) & (v < 240)).astype(np.uint8) * 255
    mask = cv2.medianBlur(mask, 5)
    num, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
    h, w = img_rgb.shape[:2]
    best = None
    for idx in range(1, num):
        x, y, bw, bh, area = stats[idx]
        if area < 120 or area > h * w * 0.35:
            continue
        cx, cy = centroids[idx]
        score = area - abs(cx - w / 2) * 2.0 - abs(cy - h * 0.65) * 1.2
        if best is None or score > best[0]:
            best = (score, cx, cy, (x, y, bw, bh))
    if best is None:
        return None, None, None
    _, cx, cy, box = best
    side = "left" if cx < w / 2 else "right"
    return side, (float(cx) / w, float(cy) / h), box


def draw_overlay(img_rgb, gt_name, pred_name, side, center, box, sample_idx):
    out = cv2.cvtColor(img_rgb.copy(), cv2.COLOR_RGB2BGR)
    if box is not None:
        x, y, w, h = box
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 255, 0), 2)
    if center is not None:
        cx = int(center[0] * img_rgb.shape[1])
        cy = int(center[1] * img_rgb.shape[0])
        cv2.drawMarker(out, (cx, cy), (255, 0, 0), cv2.MARKER_CROSS, 24, 2)
    lines = [
        f"idx={sample_idx}",
        f"GT={gt_name}",
        f"PRED={pred_name}",
        f"det_side={side or 'none'}",
    ]
    y0 = 22
    for line in lines:
        cv2.putText(out, line, (10, y0), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)
        y0 += 22
    return out


def build_dataset(args):
    raise RuntimeError("build_dataset now requires config-aware parameters")


def build_dataset_from_config(args, configs):
    ds_cfg = dict(configs.get("val_dataset") or {})
    data_dir = ds_cfg.get("data_dir", args.data)
    return NavDataset(
        data_dir=data_dir,
        episode_pattern=ds_cfg.get("episode_pattern", "episode_*.h5"),
        model_name=configs.get("model", "kosmos"),
        window_size=ds_cfg.get("window_size", configs.get("window_size", 8)),
        fwd_pred_next_n=ds_cfg.get("fwd_pred_next_n", configs.get("fwd_pred_next_n", 3)),
        discrete_action=ds_cfg.get("discrete_action", configs.get("discrete_action", True)),
        num_classes=ds_cfg.get("num_classes", configs.get("num_classes", 8)),
        instruction_preset=ds_cfg.get("instruction_preset", "default"),
        grounding_prefix=ds_cfg.get("grounding_prefix", True),
        instruction_override=ds_cfg.get("instruction_override"),
        is_validation=True,
        train_split=ds_cfg.get("train_split", args.train_split),
        stratified_split=ds_cfg.get("stratified_split", True),
        exclude_path_types=ds_cfg.get("exclude_path_types"),
        min_episode_frames=ds_cfg.get("min_episode_frames", 8),
        tokenizer=None,
    )


def get_episode_meta(ds, dataset_idx):
    ep_idx, start_f = ds.frame_indices[dataset_idx]
    ep_path = ds.episode_files[ep_idx]
    return ep_path.stem, ep_idx, start_f


def load_split_spec(split_file):
    if not split_file:
        return {}
    path = Path(split_file)
    if not path.is_absolute():
        path = ROOT / split_file
    if not path.exists():
        raise FileNotFoundError(f"split file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_fixed_targets(split_spec, wanted, subset_patterns):
    targets = []
    subsets = split_spec.get("subsets") or []
    wanted_ids = set(wanted.keys())
    allowed_patterns = set(subset_patterns)
    for subset in subsets:
        expected = subset.get("expected_gt") or {}
        gt_id = expected.get("class_id")
        pattern = subset.get("expected_path_pattern")
        if gt_id not in wanted_ids:
            continue
        if allowed_patterns and pattern not in allowed_patterns:
            continue
        for example in subset.get("candidate_examples") or []:
            dataset_idx = example.get("dataset_idx")
            if dataset_idx is None:
                continue
            targets.append({
                "dataset_idx": int(dataset_idx),
                "gt_id": gt_id,
                "subset": pattern,
                "expected_episode_stem": example.get("episode_stem"),
            })
    return targets


def main():
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    subset_patterns = [p.strip() for p in args.subset_patterns.split(",") if p.strip()]
    use_subset_limits = bool(subset_patterns) and args.limit_per_subset > 0
    split_spec = load_split_spec(args.split_file)

    print("Loading model...")
    wrapper, device, configs = load_model(args.config, args.ckpt)
    model = wrapper.model
    print(f"  device: {device}")
    print(f"  ckpt: {Path(args.ckpt).name}")

    print("Loading validation dataset...")
    ds = build_dataset_from_config(args, configs)
    print(f"  dataset sequences: {len(ds)}")

    wanted_ids = [int(x.strip()) for x in args.wanted_ids.split(",") if x.strip()]
    wanted = {class_id: CLASS_NAMES_8[class_id] for class_id in wanted_ids}
    selected = []
    counts = {class_id: 0 for class_id in wanted}
    subset_counts = {}
    if use_subset_limits:
        subset_counts = {
            wanted_id: {pattern: 0 for pattern in subset_patterns}
            for wanted_id in wanted
        }

    chosen_rows = []
    fixed_targets = build_fixed_targets(split_spec, wanted, subset_patterns)
    if fixed_targets:
        print(f"  fixed split targets: {len(fixed_targets)}")
        for target in fixed_targets:
            idx = target["dataset_idx"]
            if idx < 0 or idx >= len(ds):
                continue
            sample = ds[idx]
            batch = ds.collater([sample])
            gt = parse_gt(batch)
            if gt != target["gt_id"]:
                continue
            episode_stem, ep_idx, start_f = get_episode_meta(ds, idx)
            expected_stem = target["expected_episode_stem"]
            if expected_stem and expected_stem not in episode_stem:
                continue
            chosen_rows.append({
                "dataset_idx": idx,
                "episode_idx": ep_idx,
                "episode_stem": episode_stem,
                "start_frame": start_f,
                "subset": target["subset"],
                "gt_id": gt,
                "gt_name": CLASS_NAMES_8[gt],
                "sample": sample,
                "selection_mode": "fixed_split",
            })
            counts[gt] += 1
            if use_subset_limits and target["subset"] in subset_counts[gt]:
                subset_counts[gt][target["subset"]] += 1

    if not chosen_rows:
        print("  fixed split targets unavailable, falling back to dynamic discovery")
        for idx in range(len(ds)):
            if use_subset_limits:
                if all(
                    all(v >= args.limit_per_subset for v in pattern_counts.values())
                    for pattern_counts in subset_counts.values()
                ):
                    break
            elif all(v >= args.limit_per_class for v in counts.values()):
                break

            sample = ds[idx]
            batch = ds.collater([sample])
            gt = parse_gt(batch)
            if gt not in wanted:
                continue

            episode_stem, ep_idx, start_f = get_episode_meta(ds, idx)
            matched_subset = None
            for pattern in subset_patterns:
                if pattern in episode_stem:
                    matched_subset = pattern
                    break

            if use_subset_limits:
                if matched_subset is None:
                    continue
                if subset_counts[gt][matched_subset] >= args.limit_per_subset:
                    continue
            elif counts[gt] >= args.limit_per_class:
                continue

            chosen_rows.append({
                "dataset_idx": idx,
                "episode_idx": ep_idx,
                "episode_stem": episode_stem,
                "start_frame": start_f,
                "subset": matched_subset,
                "gt_id": gt,
                "gt_name": CLASS_NAMES_8[gt],
                "sample": sample,
                "selection_mode": "dynamic_discovery",
            })
            counts[gt] += 1
            if use_subset_limits:
                subset_counts[gt][matched_subset] += 1

    counts = {class_id: 0 for class_id in wanted}
    batch = ds.collater([row["sample"] for row in chosen_rows])
    print(f"  selected samples: {len(chosen_rows)}")
    if use_subset_limits:
        print(f"  selected subset_counts: {subset_counts}")
    gpu = {}
    for k, v in batch.items():
        if not isinstance(v, torch.Tensor):
            gpu[k] = v
            continue
        if device == "cuda":
            gpu[k] = v.cuda().half() if v.dtype.is_floating_point else v.cuda()
        else:
            gpu[k] = v.float() if v.dtype.is_floating_point else v

    with torch.no_grad():
        outputs = model.forward_action(
            vision_x=gpu["rgb"],
            lang_x=gpu["text"],
            attention_mask=gpu["text_mask"].bool(),
            vision_gripper=gpu.get("hand_rgb"),
            instr_and_action_ids=gpu.get("instr_and_action_ids"),
            instr_and_action_labels=gpu.get("instr_and_action_labels"),
            instr_and_action_mask=gpu.get("instr_and_action_mask"),
            mode="test",
        )

    for batch_idx, row in enumerate(chosen_rows):
        parsed = parse_logits(outputs, t=0, batch_idx=batch_idx)
        if parsed is None:
            continue
        pred, logits = parsed
        gt = row["gt_id"]

        img_rgb = tensor_to_image(batch["rgb"][batch_idx, 0])
        side, center, box = detect_basket_side(img_rgb)
        overlay = draw_overlay(
            img_rgb,
            CLASS_NAMES_8[gt],
            CLASS_NAMES_8.get(pred, str(pred)),
            side,
            center,
            box,
            row["dataset_idx"],
        )

        task_hint = "unknown"
        if "raw_text" in batch and isinstance(batch["raw_text"], list) and batch["raw_text"]:
            task_hint = str(batch["raw_text"][batch_idx])[:60].replace("/", "_").replace(" ", "_")

        save_path = out_dir / f"{wanted[gt].lower()}__{counts[gt]:02d}__idx{row['dataset_idx']}.jpg"
        cv2.imwrite(str(save_path), overlay)

        selected.append({
            "dataset_idx": row["dataset_idx"],
            "episode_idx": row["episode_idx"],
            "episode_stem": row["episode_stem"],
            "start_frame": row["start_frame"],
            "subset": row["subset"],
            "selection_mode": row["selection_mode"],
            "gt_id": gt,
            "gt_name": CLASS_NAMES_8[gt],
            "pred_id": int(pred),
            "pred_name": CLASS_NAMES_8.get(int(pred), str(pred)),
            "pred_top_logit": float(np.max(logits)),
            "detected_side": side,
            "detected_center_x": None if center is None else round(center[0], 3),
            "saved_image": str(save_path),
            "task_hint": task_hint,
        })
        counts[gt] += 1

    summary = {
        "config": args.config,
        "ckpt": args.ckpt,
        "split_file": args.split_file,
        "limit_per_class": args.limit_per_class,
        "limit_per_subset": args.limit_per_subset,
        "subset_patterns": subset_patterns,
        "counts": counts,
        "subset_counts": subset_counts,
        "samples": selected,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    print("\n=== LEFT/RIGHT SANITY SUMMARY ===")
    for gt_id, gt_name in wanted.items():
        rows = [r for r in selected if r["gt_id"] == gt_id]
        pred_stats = {}
        for row in rows:
            pred_stats[row["pred_name"]] = pred_stats.get(row["pred_name"], 0) + 1
        side_stats = {}
        for row in rows:
            key = row["detected_side"] or "none"
            side_stats[key] = side_stats.get(key, 0) + 1
        print(f"{gt_name}: {len(rows)} samples")
        print(f"  predicted: {pred_stats}")
        print(f"  detected_side: {side_stats}")
        if use_subset_limits:
            print(f"  subset_counts: {subset_counts[gt_id]}")
        for row in rows[:5]:
            print(
                "   - "
                f"idx={row['dataset_idx']} subset={row['subset']} pred={row['pred_name']} "
                f"side={row['detected_side']} cx={row['detected_center_x']} "
                f"img={Path(row['saved_image']).name}"
            )

    print(f"\nSaved artifacts to: {out_dir}")


if __name__ == "__main__":
    main()

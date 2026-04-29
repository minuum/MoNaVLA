#!/usr/bin/env python3
"""
Evaluate grounding auxiliary heads against human-reviewed bbox_truth_mini rows.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import torch
import torch.nn as nn

import lightning.fabric.plugins.environments.mpi as _mpi_env_mod

_mpi_env_mod._MPI4PY_AVAILABLE = False

ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "third_party" / "RoboVLMs"))

import robovlms.model.backbone as backbone_mod
import robovlms.model.policy_head as policy_head_mod
import robovlms.train.base_trainer as base_trainer_mod
import robovlms.train as train_mod

from main import load_config
import main as main_mod
from robovlms.train.mobile_vla_trainer import MobileVLATrainer
from robovlm_nav.datasets.nav_dataset import NavDataset
from robovlm_nav.models.nav_robokosmos import NavRoboKosMos
from robovlm_nav.models.policy_head.hybrid_action_head import HybridActionHead
from robovlm_nav.models.policy_head.nav_policy_impl import (
    MobileVLAClassificationDecoder,
    MobileVLALSTMDecoder,
)
from robovlm_nav.trainer.nav_trainer import NavTrainer

setattr(backbone_mod, "RoboKosMos", NavRoboKosMos)
setattr(backbone_mod, "RoboVLM-Nav", NavRoboKosMos)
setattr(policy_head_mod, "MobileVLAClassificationDecoder", MobileVLAClassificationDecoder)
setattr(policy_head_mod, "MobileVLALSTMDecoder", MobileVLALSTMDecoder)
setattr(policy_head_mod, "NavPolicy", MobileVLAClassificationDecoder)
setattr(policy_head_mod, "NavPolicyRegression", MobileVLALSTMDecoder)
setattr(policy_head_mod, "HybridActionHead", HybridActionHead)
base_trainer_mod.BaseTrainer = NavTrainer
setattr(train_mod, "NavTrainer", NavTrainer)
setattr(train_mod, "BaseTrainer", NavTrainer)
main_mod.BaseTrainer = NavTrainer

TRUTH_PATH = ROOT / "docs" / "v5" / "bbox_truth_mini.json"
COARSE_NAMES = ["left", "center", "right"]


def fix_paths(cfg: dict) -> dict:
    vlm_path = str(ROOT / ".vlms" / "kosmos-2-patch14-224")

    def rec(node: dict) -> None:
        for k, v in node.items():
            if isinstance(v, str) and "kosmos-2-patch14-224" in v:
                node[k] = vlm_path
            elif isinstance(v, dict):
                rec(v)

    rec(cfg)
    if isinstance(cfg.get("vlm"), dict):
        cfg["vlm"]["pretrained_model_name_or_path"] = vlm_path
    if isinstance(cfg.get("tokenizer"), dict):
        cfg["tokenizer"]["pretrained_model_name_or_path"] = vlm_path
    return cfg


def iou_xyxy(box_a: list[float], box_b: list[float]) -> float:
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


def center_l1(box_a: list[float], box_b: list[float]) -> float:
    ax = (box_a[0] + box_a[2]) / 2.0
    ay = (box_a[1] + box_a[3]) / 2.0
    bx = (box_b[0] + box_b[2]) / 2.0
    by = (box_b[1] + box_b[3]) / 2.0
    return abs(ax - bx) + abs(ay - by)


def load_datasets(cfg: dict) -> tuple[NavDataset, NavDataset]:
    base_cfg = dict(cfg["val_dataset"])
    base_cfg.pop("type", None)
    train_cfg = dict(base_cfg)
    train_cfg["is_validation"] = False
    val_cfg = dict(base_cfg)
    val_cfg["is_validation"] = True
    return NavDataset(**train_cfg), NavDataset(**val_cfg)


def build_frame_map(*datasets: NavDataset) -> dict[tuple[str, int], tuple[NavDataset, int, int, int, str]]:
    frame_map = {}
    for dataset in datasets:
        ds_name = "val" if dataset.is_validation else "train"
        for ds_idx, (ep_idx, start) in enumerate(dataset.frame_indices):
            ep = dataset.episode_files[ep_idx].stem
            for rel_t in range(dataset.window_size):
                key = (ep, start + rel_t)
                prev = frame_map.get(key)
                if prev is None or start > prev[3]:
                    frame_map[key] = (dataset, ds_idx, rel_t, start, ds_name)
    return frame_map


def build_aux_heads(cfg: dict, state_dict: dict, hidden_size: int) -> tuple[nn.Module, nn.Module]:
    aux_cfg = cfg.get("grounding_aux", {}) or {}
    mlp_hidden = int(aux_cfg.get("mlp_hidden", max(hidden_size // 2, 128)))
    dropout = float(aux_cfg.get("dropout", 0.1))

    bbox_head = nn.Sequential(
        nn.Linear(hidden_size, mlp_hidden),
        nn.ReLU(),
        nn.Dropout(dropout),
        nn.Linear(mlp_hidden, 4),
        nn.Sigmoid(),
    )
    coarse_head = nn.Sequential(
        nn.Linear(hidden_size, mlp_hidden),
        nn.ReLU(),
        nn.Dropout(dropout),
        nn.Linear(mlp_hidden, 3),
    )

    bbox_sd = {
        k.replace("grounding_bbox_head.", "", 1): v
        for k, v in state_dict.items()
        if k.startswith("grounding_bbox_head.")
    }
    coarse_sd = {
        k.replace("grounding_coarse_head.", "", 1): v
        for k, v in state_dict.items()
        if k.startswith("grounding_coarse_head.")
    }
    bbox_head.load_state_dict(bbox_sd, strict=True)
    coarse_head.load_state_dict(coarse_sd, strict=True)
    bbox_head = bbox_head.to("cuda").eval().half()
    coarse_head = coarse_head.to("cuda").eval().half()
    return bbox_head, coarse_head


def load_model(config_path: Path, ckpt_path: Path) -> tuple[MobileVLATrainer, nn.Module, nn.Module]:
    cfg = fix_paths(load_config(str(config_path)))
    trainer = MobileVLATrainer(cfg)
    state = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    state_dict = state.get("state_dict", state.get("model_state_dict", {}))
    state_dict = {k.replace("module.", "", 1) if k.startswith("module.") else k: v for k, v in state_dict.items()}
    trainer.load_state_dict(state_dict, strict=False)
    trainer = trainer.to("cuda").eval().half()
    act_head = trainer.model.act_head
    hidden_size = int(getattr(act_head, "hidden_size", 1024)) * int(getattr(act_head, "latent", 1))
    bbox_head, coarse_head = build_aux_heads(cfg, state_dict, hidden_size)
    return trainer, bbox_head, coarse_head


def summarize(rows: list[dict]) -> dict:
    mean_iou = sum(r["pred_iou"] for r in rows) / len(rows) if rows else None
    mean_center = sum(r["pred_center_l1"] for r in rows) / len(rows) if rows else None
    overall = sum(int(r["pred_coarse"] == r["gt_coarse"]) for r in rows) / len(rows) if rows else None
    by_coarse = {}
    for coarse in COARSE_NAMES:
        subset = [r for r in rows if r["gt_coarse"] == coarse]
        by_coarse[coarse] = {
            "n": len(subset),
            "acc": (sum(int(r["pred_coarse"] == r["gt_coarse"]) for r in subset) / len(subset)) if subset else None,
            "mean_iou": (sum(r["pred_iou"] for r in subset) / len(subset)) if subset else None,
        }
    return {
        "n": len(rows),
        "mean_iou": mean_iou,
        "iou_at_0_3": sum(int(r["pred_iou"] >= 0.3) for r in rows) / len(rows) if rows else None,
        "mean_center_l1": mean_center,
        "coarse_acc": overall,
        "by_coarse": by_coarse,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    payload = json.loads(TRUTH_PATH.read_text())
    anns = [a for a in payload["annotations"] if a.get("review_status") in {"done", "complete", "verified"}]
    trainer, bbox_head, coarse_head = load_model(Path(args.config), Path(args.ckpt))
    cfg = fix_paths(load_config(args.config))
    train_ds, val_ds = load_datasets(cfg)
    frame_map = build_frame_map(train_ds, val_ds)

    rows = []
    with torch.no_grad():
        for ann in anns:
            key = (ann["episode"], int(ann["frame_idx"]))
            mapped = frame_map.get(key)
            if mapped is None or not ann.get("target_visible") or not ann.get("bbox_xyxy_norm"):
                continue
            dataset, ds_idx, rel_t, _start, ds_name = mapped
            sample = dataset[ds_idx]
            batch = dataset.collater([sample])
            gpu = {
                k: (
                    v.cuda().half()
                    if isinstance(v, torch.Tensor) and v.dtype.is_floating_point
                    else v.cuda()
                    if isinstance(v, torch.Tensor)
                    else v
                )
                for k, v in batch.items()
            }
            processed = trainer._process_batch(gpu)
            trainer.model.forward(
                processed[0],
                processed[3],
                attention_mask=processed[4],
                action_labels=(processed[9], processed[10]),
                action_mask=processed[11],
                text_embedding=gpu.get("text_embedding"),
                raw_text=processed[16],
                data_source=processed[18],
            )
            hidden = trainer.model.act_head.last_hidden_states.to(next(bbox_head.parameters()).dtype)
            pred_bbox = bbox_head(hidden)[0, rel_t].float().cpu().tolist()
            pred_coarse = COARSE_NAMES[int(coarse_head(hidden)[0, rel_t].argmax().item())]
            gt_bbox = ann["bbox_xyxy_norm"]
            rows.append(
                {
                    "episode": ann["episode"],
                    "frame_idx": int(ann["frame_idx"]),
                    "path_type": ann["path_type"],
                    "split": ds_name,
                    "gt_coarse": ann.get("coarse_position"),
                    "pred_coarse": pred_coarse,
                    "gt_bbox": gt_bbox,
                    "pred_bbox": pred_bbox,
                    "pred_iou": iou_xyxy(gt_bbox, pred_bbox),
                    "pred_center_l1": center_l1(gt_bbox, pred_bbox),
                }
            )

    rows.sort(key=lambda r: (r["episode"], r["frame_idx"]))
    out = {
        "label": args.label,
        "config": args.config,
        "ckpt": args.ckpt,
        "summary": summarize(rows),
        "rows": rows,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

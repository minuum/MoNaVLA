#!/usr/bin/env python3
"""
Render GT / seed / exp28 auxiliary bbox overlays for human-reviewed bbox_truth_mini rows.

Outputs:
  docs/v5/bbox_truth_eval/exp28_aux_overlays/*.png
  docs/v5/bbox_truth_eval/exp28_aux_overlays/summary.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image, ImageDraw

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
from scripts.analysis.evaluate_rollout_degradation_v5 import MODEL_SPECS, resolve_ckpt_path

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
OUT_DIR = ROOT / "docs" / "v5" / "bbox_truth_eval" / "exp28_aux_overlays"
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


def draw_box(draw: ImageDraw.ImageDraw, box: list[float], size: tuple[int, int], color: str, width: int = 4) -> None:
    w, h = size
    x1, y1, x2, y2 = box
    # sort coords so invalid predicted ordering is still visible
    x1, x2 = sorted((x1, x2))
    y1, y2 = sorted((y1, y2))
    rect = [x1 * w, y1 * h, x2 * w, y2 * h]
    draw.rectangle(rect, outline=color, width=width)


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


def load_exp28() -> tuple[MobileVLATrainer, Path, nn.Module, nn.Module]:
    spec = MODEL_SPECS["exp28"]
    ckpt = resolve_ckpt_path(spec)
    cfg = fix_paths(load_config(str(spec["config"])))
    trainer = MobileVLATrainer(cfg)
    state = torch.load(str(ckpt), map_location="cpu", weights_only=False)
    state_dict = state.get("state_dict", state.get("model_state_dict", {}))
    state_dict = {k.replace("module.", "", 1) if k.startswith("module.") else k: v for k, v in state_dict.items()}
    trainer.load_state_dict(state_dict, strict=False)
    trainer = trainer.to("cuda").eval().half()
    act_head = trainer.model.act_head
    hidden_size = int(getattr(act_head, "hidden_size", 1024)) * int(getattr(act_head, "latent", 1))
    bbox_head, coarse_head = build_aux_heads(cfg, state_dict, hidden_size)
    return trainer, ckpt, bbox_head, coarse_head


def main() -> None:
    payload = json.loads(TRUTH_PATH.read_text())
    anns = [a for a in payload["annotations"] if a.get("review_status") in {"done", "complete", "verified"}]

    spec = MODEL_SPECS["exp28"]
    cfg = fix_paths(load_config(str(spec["config"])))
    train_ds, val_ds = load_datasets(cfg)
    frame_map = build_frame_map(train_ds, val_ds)
    trainer, ckpt, bbox_head, coarse_head = load_exp28()

    rows = []
    with torch.no_grad():
        for ann in anns:
            key = (ann["episode"], int(ann["frame_idx"]))
            mapped = frame_map.get(key)
            if mapped is None:
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
            _ = trainer.model.forward(
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
            seed_bbox = ann.get("seed_bbox_xyxy_norm")
            rows.append(
                {
                    "episode": ann["episode"],
                    "frame_idx": int(ann["frame_idx"]),
                    "path_type": ann["path_type"],
                    "anchor_tag": ann.get("anchor_tag"),
                    "split": ds_name,
                    "frame_path": ann["frame_path"],
                    "gt_bbox": gt_bbox,
                    "seed_bbox": seed_bbox,
                    "pred_bbox": pred_bbox,
                    "gt_coarse": ann.get("coarse_position"),
                    "seed_coarse": ann.get("seed_coarse_position"),
                    "pred_coarse": pred_coarse,
                    "pred_iou": iou_xyxy(gt_bbox, pred_bbox),
                    "seed_iou": iou_xyxy(gt_bbox, seed_bbox) if seed_bbox is not None else None,
                    "pred_center_l1": center_l1(gt_bbox, pred_bbox),
                    "seed_center_l1": center_l1(gt_bbox, seed_bbox) if seed_bbox is not None else None,
                }
            )

    rows.sort(key=lambda r: (r["pred_iou"], -r["pred_center_l1"]))
    selected = rows[:12]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for idx, row in enumerate(selected, start=1):
        img = Image.open(row["frame_path"]).convert("RGB")
        draw = ImageDraw.Draw(img)
        draw_box(draw, row["gt_bbox"], img.size, "#00ff66", width=5)
        if row["seed_bbox"] is not None:
            draw_box(draw, row["seed_bbox"], img.size, "#3399ff", width=4)
        draw_box(draw, row["pred_bbox"], img.size, "#ff3333", width=4)
        stem = f"{idx:02d}_{row['episode']}_f{row['frame_idx']:04d}"
        img.save(OUT_DIR / f"{stem}.png")

    summary = {
        "exp28_ckpt": str(ckpt),
        "matched_rows": len(rows),
        "selected_count": len(selected),
        "legend": {
            "gt_bbox": "#00ff66",
            "seed_bbox": "#3399ff",
            "exp28_aux_bbox": "#ff3333",
        },
        "selected_rows": selected,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote {len(selected)} overlays to {OUT_DIR}")
    print(f"Summary: {OUT_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()

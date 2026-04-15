#!/usr/bin/env python3
"""
V5 PM/DM 오프라인 평가 스크립트

- Dataset : V5 H5 (observations/images, 3D action)
- Model   : V5 best ckpt (epoch=05, val_loss=2.270)
- Classes : 6 (STOP / FORWARD / LEFT / RIGHT / FWD+LEFT / FWD+RIGHT)
- Metrics : PM (Perfect Match), per-class accuracy, confusion matrix
"""
import os, sys

# ── MPI hang 방지
import lightning.fabric.plugins.environments.mpi as _mpi_env_mod
_mpi_env_mod._MPI4PY_AVAILABLE = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "third_party", "RoboVLMs"))

import json, gc
import torch
import numpy as np
from tqdm import tqdm
from pathlib import Path

# ── robovlms 네임스페이스 주입 (train.py와 동일)
import robovlms.model.backbone as backbone_mod
import robovlms.model.policy_head as policy_head_mod
import robovlms.train.base_trainer as base_trainer_mod
import robovlms.train as train_mod

from robovlms.model.backbone.robokosmos import RoboKosMos
setattr(backbone_mod, "RoboKosMos", RoboKosMos)
setattr(backbone_mod, "RoboVLM-Nav", RoboKosMos)

from robovlm_nav.models.policy_head.nav_policy_impl import (
    MobileVLAClassificationDecoder,
    MobileVLALSTMDecoder,
)
from robovlm_nav.models.policy_head.hybrid_action_head import HybridActionHead
setattr(policy_head_mod, "MobileVLAClassificationDecoder", MobileVLAClassificationDecoder)
setattr(policy_head_mod, "MobileVLALSTMDecoder", MobileVLALSTMDecoder)
setattr(policy_head_mod, "NavPolicy", MobileVLAClassificationDecoder)
setattr(policy_head_mod, "NavPolicyRegression", MobileVLALSTMDecoder)
setattr(policy_head_mod, "HybridActionHead", HybridActionHead)

from robovlm_nav.trainer.nav_trainer import NavTrainer
base_trainer_mod.BaseTrainer = NavTrainer
setattr(train_mod, "NavTrainer", NavTrainer)
setattr(train_mod, "BaseTrainer", NavTrainer)

import main as main_mod
main_mod.BaseTrainer = NavTrainer

# ── CLI 인자 파싱 (하드코딩 대신)
import argparse as _argparse
_ap = _argparse.ArgumentParser(add_help=False)
_ap.add_argument("--ckpt",    default=None)
_ap.add_argument("--config",  default=None)
_ap.add_argument("--data",    default=None)
_ap.add_argument("--num_classes", type=int, default=None)
_ap.add_argument("--train_split", type=float, default=None)
_ap.add_argument("--window_size", type=int, default=None)
_ap.add_argument("--instruction_preset", default=None)
_cli, _ = _ap.parse_known_args()

# ── 설정 (CLI 우선, fallback으로 기본값)
CKPT = _cli.ckpt or os.path.join(ROOT, "runs/v5_nav/kosmos/mobile_vla_v5_exp01/2026-04-10/v5-exp01-discrete",
                    "epoch_epoch=epoch=05-val_loss=val_loss=2.270.ckpt")
CONFIG = _cli.config or os.path.join(ROOT, "configs/mobile_vla_v5_exp01_discrete.json")
V5_DATA = _cli.data or os.path.join(ROOT, "ROS_action/v5_data_bak/mobile_vla_dataset_v5")

NUM_CLASSES = _cli.num_classes or 6
_VAL_TRAIN_SPLIT = _cli.train_split or 0.85
_VAL_WINDOW_SIZE = _cli.window_size or 6
_VAL_INSTRUCTION_PRESET = _cli.instruction_preset or "default"

CLASS_NAMES_6 = {0:"STOP", 1:"FORWARD", 2:"LEFT", 3:"RIGHT", 4:"FWD+L", 5:"FWD+R"}
CLASS_NAMES_8 = {0:"STOP", 1:"FORWARD", 2:"LEFT", 3:"RIGHT", 4:"FWD+L", 5:"FWD+R", 6:"TURN_L", 7:"TURN_R"}
CLASS_NAMES = CLASS_NAMES_8 if NUM_CLASSES == 8 else CLASS_NAMES_6

# ── 모델 로드 (inference_server와 동일한 방식)
def load_model():
    os.chdir(ROOT)
    from main import load_config, update_configs
    configs = load_config(CONFIG)

    # 경로 패치
    vlm_path = os.path.join(ROOT, ".vlms", "kosmos-2-patch14-224")
    def _fix_paths(d):
        for k, v in d.items():
            if isinstance(v, str) and "kosmos-2-patch14-224" in v:
                d[k] = vlm_path
            elif isinstance(v, dict):
                _fix_paths(v)
    _fix_paths(configs)
    if isinstance(configs.get("vlm"), dict):
        configs["vlm"]["pretrained_model_name_or_path"] = vlm_path
    if isinstance(configs.get("tokenizer"), dict):
        configs["tokenizer"]["pretrained_model_name_or_path"] = vlm_path

    from robovlms.train.mobile_vla_trainer import MobileVLATrainer
    print("🔧 Building model...")
    model_wrapper = MobileVLATrainer(configs)

    # 필요한 가중치만 로드 (inference_server 방식)
    print(f"📦 Loading checkpoint: {Path(CKPT).name}")
    ckpt = torch.load(CKPT, map_location="cpu", weights_only=False)
    full_sd = ckpt.get("model_state_dict", ckpt.get("state_dict", {}))

    filtered = {}
    for k, v in full_sd.items():
        if any(x in k for x in ["image_to_text_projection","act_head","policy_head","resampler","action_token","lora"]):
            new_k = k.replace("model.", "", 1) if k.startswith("model.") and not hasattr(model_wrapper, "model") else k
            filtered[new_k] = v

    missing, unexpected = model_wrapper.load_state_dict(filtered, strict=False)
    print(f"✅ Loaded {len(filtered)} weights | missing={len(missing)} unexpected={len(unexpected)}")
    del full_sd, ckpt; gc.collect()

    model_wrapper.to("cuda").eval().half()
    return model_wrapper

# ── logit 파싱 (V4 스크립트와 동일 로직)
def parse_logits(outputs):
    if isinstance(outputs, (tuple, list)):
        outputs = outputs[0]
    if outputs is None or not isinstance(outputs, torch.Tensor):
        return None
    arr = outputs.detach().cpu().float().numpy()
    if arr.ndim == 4:   logits = arr[0, -1, 0, :]
    elif arr.ndim == 3: logits = arr[0, -1, :]
    elif arr.ndim == 2: logits = arr[0, :]
    else:               logits = arr
    return int(np.argmax(logits)), logits

def parse_gt(batch):
    if "action_chunck" in batch:
        ac = batch["action_chunck"].cpu().numpy()
        return int(ac[0, -1, 0])
    if "action" in batch:
        return int(batch["action"].cpu().numpy()[0, -1])
    return None

# ── 데이터셋 로드
def load_val_dataset():
    from robovlm_nav.datasets.nav_dataset import NavDataset
    ds = NavDataset(
        data_dir=V5_DATA,
        episode_pattern="episode_*.h5",
        model_name="kosmos",
        window_size=6,
        fwd_pred_next_n=3,
        discrete_action=True,
        num_classes=NUM_CLASSES,
        instruction_preset="default",
        grounding_prefix=True,
        is_validation=True,
        train_split=0.85,
        min_episode_frames=8,
    )
    return ds

# ── 메인 평가
def evaluate():
    print("=" * 65)
    print("  V5 PM/DM Offline Evaluation")
    print(f"  Ckpt : {Path(CKPT).name}")
    print(f"  Data : {V5_DATA}")
    print("=" * 65)

    model_wrapper = load_model()
    model = model_wrapper.model  # RoboKosMos backbone

    ds = load_val_dataset()
    print(f"📊 Val dataset: {len(ds)} sequences\n")

    confusion = np.zeros((NUM_CLASSES, NUM_CLASSES), dtype=int)
    pm, total, errors = 0, 0, 0

    with torch.no_grad():
        for i in tqdm(range(len(ds)), desc="Eval"):
            try:
                sample = ds[i]
                batch = ds.collater([sample])
                gpu = {k: v.cuda().half() if isinstance(v, torch.Tensor) and v.dtype.is_floating_point
                       else (v.cuda() if isinstance(v, torch.Tensor) else v)
                       for k, v in batch.items()}

                gt = parse_gt(gpu)
                if gt is None: continue
                gt = min(gt, NUM_CLASSES - 1)

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

                result = parse_logits(outputs)
                if result is None: errors += 1; continue

                pred, logits = result
                pred = min(pred, NUM_CLASSES - 1)

                confusion[gt, pred] += 1
                total += 1
                if pred == gt: pm += 1

                if i < 15:
                    gt_n, pred_n = CLASS_NAMES.get(gt,"?"), CLASS_NAMES.get(pred,"?")
                    mark = "✅" if pred == gt else "❌"
                    print(f"  [{i:3d}] GT={gt_n:<8} PRED={pred_n:<8} logits={np.round(logits,2)} {mark}")

            except Exception as e:
                errors += 1
                if errors <= 3:
                    import traceback; traceback.print_exc()

    # ── 결과 출력
    print(f"\n{'='*65}")
    print(f"  Result Summary")
    print(f"{'='*65}")
    print(f"  Total   : {total}  |  Errors: {errors}")
    if total == 0:
        print("❌ No valid samples!"); return

    pm_rate = pm / total * 100
    print(f"  PM (Perfect Match) : {pm_rate:.2f}%  ({pm}/{total})")

    print(f"\n  {'Class':<10} {'GT_cnt':>7} {'Correct':>8} {'Acc':>8}")
    print(f"  {'-'*40}")
    for c in range(NUM_CLASSES):
        gt_tot = int(confusion[c].sum())
        correct = int(confusion[c, c])
        acc = correct / gt_tot * 100 if gt_tot > 0 else 0.0
        print(f"  {CLASS_NAMES[c]:<10} {gt_tot:>7} {correct:>8} {acc:>7.1f}%")

    print(f"\n  Confusion Matrix (row=GT, col=PRED)")
    header = "  GT\\PRED  " + "".join(f"{CLASS_NAMES[c]:>8}" for c in range(NUM_CLASSES))
    print(header)
    for r in range(NUM_CLASSES):
        row = f"  {CLASS_NAMES[r]:<9} " + "".join(f"{confusion[r,c]:>8}" for c in range(NUM_CLASSES))
        print(row)
    print()

if __name__ == "__main__":
    os.chdir(ROOT)
    evaluate()

#!/usr/bin/env python3
"""
Tiny overfit check for Exp36 (pure HF Kosmos-2 + last-4 LoRA, left-family).

Goal: verify that non-FORWARD logits can move under gradient updates.
If they don't move at all, there's a deeper pipeline/gradient issue beyond
the fwd_pred_next_n mismatch we already fixed.

Usage:
    python3 scripts/test_v5_overfit_check.py \
        --config configs/mobile_vla_v5_exp36_pure_hf_last4_lora_left50_lossfix_5ep.json \
        --ckpt runs/v5_nav/kosmos/mobile_vla_v5_exp36/2026-04-25/v5-exp36-pure-hf-last4-lora-left50-lossfix-5ep/epoch_epoch=epoch=04-val_loss=val_loss=6.535.ckpt \
        --n_steps 30 \
        --n_samples 8 \
        --lr 1e-4
"""
import os, sys, gc, argparse

import lightning.fabric.plugins.environments.mpi as _mpi_env_mod
_mpi_env_mod._MPI4PY_AVAILABLE = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "third_party", "RoboVLMs"))

import torch
import numpy as np
from pathlib import Path

# ── namespace injection (same as train.py / test_v5_pm_dm.py)
import robovlms.model.backbone as backbone_mod
import robovlms.model.policy_head as policy_head_mod
import robovlms.train.base_trainer as base_trainer_mod
import robovlms.train as train_mod

from robovlms.model.backbone.robokosmos import RoboKosMos
from robovlm_nav.models.nav_robokosmos import NavRoboKosMos
setattr(backbone_mod, "RoboKosMos", NavRoboKosMos)
setattr(backbone_mod, "RoboVLM-Nav", NavRoboKosMos)

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

CLASS_NAMES = {
    0: "STOP", 1: "FORWARD", 2: "LEFT", 3: "RIGHT",
    4: "FWD+L", 5: "FWD+R", 6: "TURN_L", 7: "TURN_R",
}


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--ckpt",   required=True)
    ap.add_argument("--n_steps",   type=int,   default=30)
    ap.add_argument("--n_samples", type=int,   default=8,
                    help="Max non-FORWARD sequences to overfit on")
    ap.add_argument("--lr",        type=float, default=1e-4,
                    help="Learning rate for overfit steps (higher than training to see signal fast)")
    ap.add_argument("--include_path_families", default="left_straight,left_left,left_right")
    return ap.parse_args()


def load_model(config_path, ckpt_path):
    os.chdir(ROOT)
    from main import load_config
    configs = load_config(config_path)

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

    print(f"📦 Loading checkpoint: {Path(ckpt_path).name}")
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    full_sd = ckpt.get("model_state_dict", ckpt.get("state_dict", {}))
    filtered = {}
    for k, v in full_sd.items():
        if any(x in k for x in ["image_to_text_projection", "act_head", "policy_head",
                                  "resampler", "action_token", "lora"]):
            new_k = k.replace("model.", "", 1) if k.startswith("model.") else k
            filtered[new_k] = v
    missing, unexpected = model_wrapper.load_state_dict(filtered, strict=False)
    print(f"✅ Loaded {len(filtered)} weights | missing={len(missing)} unexpected={len(unexpected)}")
    del full_sd, ckpt; gc.collect()

    # Keep float32 for gradient computation (no .half())
    model_wrapper.to("cuda")
    return model_wrapper, configs


def build_dataset(configs, include_path_families):
    from robovlm_nav.datasets.nav_dataset import NavDataset
    val_cfg = configs.get("val_dataset", {})
    data_dir = val_cfg.get("data_dir", os.path.join(ROOT, "ROS_action/mobile_vla_dataset_v5"))
    num_classes = int(val_cfg.get("num_classes", 8))
    window_size = int(val_cfg.get("window_size", 8))
    fwd_pred_next_n = int(val_cfg.get("fwd_pred_next_n", 1))
    train_split = float(val_cfg.get("train_split", 0.8))

    families = [f.strip() for f in include_path_families.split(",") if f.strip()]
    ds = NavDataset(
        data_dir=data_dir,
        episode_pattern="episode_*.h5",
        model_name="kosmos",
        window_size=window_size,
        fwd_pred_next_n=fwd_pred_next_n,
        discrete_action=True,
        num_classes=num_classes,
        instruction_preset="default",
        grounding_prefix=True,
        is_validation=False,
        train_split=train_split,
        stratified_split=True,
        include_path_families=families,
        min_episode_frames=8,
    )
    return ds, fwd_pred_next_n


def collect_non_forward_samples(ds, n_samples, fwd_pred_next_n):
    """Collect at most n_samples sequences where GT action at t=0 is NOT FORWARD."""
    samples = []
    for i in range(len(ds)):
        sample = ds[i]
        batch = ds.collater([sample])
        ac = batch.get("action_chunck")
        if ac is None:
            continue
        gt = int(ac[0, 0, 0].item())
        if gt != 1:  # not FORWARD
            samples.append((gt, batch))
        if len(samples) >= n_samples:
            break
    return samples


def move_batch_to_gpu(batch):
    return {
        k: v.cuda().float() if isinstance(v, torch.Tensor) and v.dtype.is_floating_point
           else (v.cuda() if isinstance(v, torch.Tensor) else v)
        for k, v in batch.items()
    }


def get_logits_for_batch(model_wrapper, gpu_batch):
    """Run forward inference and return logit vector at (b=0, t=0, n=0)."""
    with torch.no_grad():
        outputs = model_wrapper.model.forward_action(
            vision_x=gpu_batch["rgb"],
            lang_x=gpu_batch["text"],
            attention_mask=gpu_batch["text_mask"].bool(),
            text_embedding=gpu_batch.get("text_embedding"),
            vision_gripper=gpu_batch.get("hand_rgb"),
            instr_and_action_ids=gpu_batch.get("instr_and_action_ids"),
            instr_and_action_labels=gpu_batch.get("instr_and_action_labels"),
            instr_and_action_mask=gpu_batch.get("instr_and_action_mask"),
            mode="test",
        )
    logits_raw = outputs[0] if isinstance(outputs, (tuple, list)) else outputs
    if logits_raw is None:
        return None
    arr = logits_raw.detach().cpu().float().numpy()
    # arr shape: (B, L, n, C) or (B, L, C)
    if arr.ndim == 4:
        return arr[0, 0, 0, :]  # (C,)
    elif arr.ndim == 3:
        return arr[0, 0, :]
    return arr[0]


def training_step(model_wrapper, gpu_batch):
    """Single training forward+backward step. Returns scalar loss."""
    model_wrapper.model.train()
    outputs = model_wrapper.model.forward_action(
        vision_x=gpu_batch["rgb"],
        lang_x=gpu_batch["text"],
        attention_mask=gpu_batch["text_mask"].bool(),
        text_embedding=gpu_batch.get("text_embedding"),
        vision_gripper=gpu_batch.get("hand_rgb"),
        instr_and_action_ids=gpu_batch.get("instr_and_action_ids"),
        instr_and_action_labels=gpu_batch.get("instr_and_action_labels"),
        instr_and_action_mask=gpu_batch.get("instr_and_action_mask"),
        mode="train",
    )
    # The model in train mode should return a loss dict
    if isinstance(outputs, dict):
        loss = outputs.get("loss", outputs.get("loss_arm_act"))
    elif isinstance(outputs, (tuple, list)):
        loss = outputs[0] if isinstance(outputs[0], torch.Tensor) else None
    else:
        loss = outputs
    return loss


def grad_norm(params):
    total = 0.0
    for p in params:
        if p.grad is not None:
            total += p.grad.detach().norm().item() ** 2
    return total ** 0.5


def main():
    args = parse_args()
    model_wrapper, configs = load_model(args.config, args.ckpt)

    print(f"\n📂 Building dataset (left-family)...")
    ds, fwd_pred_next_n = build_dataset(configs, args.include_path_families)
    print(f"   Dataset size: {len(ds)} sequences | fwd_pred_next_n={fwd_pred_next_n}")

    print(f"\n🔍 Collecting up to {args.n_samples} non-FORWARD sequences...")
    samples = collect_non_forward_samples(ds, args.n_samples, fwd_pred_next_n)
    if not samples:
        print("❌ No non-FORWARD sequences found! Check dataset/path family settings.")
        return
    print(f"   Found {len(samples)} non-FORWARD sequences:")
    for i, (gt, _) in enumerate(samples):
        print(f"   [{i}] GT={CLASS_NAMES.get(gt, gt)}")

    # -- Logit snapshot before training --
    print("\n📊 Logits BEFORE overfit (inference mode, first sequence):")
    model_wrapper.model.eval()
    gpu_batch_0 = move_batch_to_gpu(samples[0][1])
    logits_before = get_logits_for_batch(model_wrapper, gpu_batch_0)
    if logits_before is None:
        print("❌ Could not extract logits. Exiting.")
        return
    probs_before = torch.softmax(torch.tensor(logits_before), dim=0).numpy()
    for c in range(len(logits_before)):
        marker = " ← GT" if c == samples[0][0] else ""
        print(f"   {CLASS_NAMES.get(c, c):8s}: logit={logits_before[c]:+.4f}  prob={probs_before[c]:.4f}{marker}")

    # -- Setup optimizer (trainable params only) --
    trainable_params = [p for p in model_wrapper.parameters() if p.requires_grad]
    print(f"\n🏋️  Trainable params: {sum(p.numel() for p in trainable_params):,}")
    optimizer = torch.optim.AdamW(trainable_params, lr=args.lr, weight_decay=0.01)

    # -- Overfit loop --
    print(f"\n🔄 Running {args.n_steps} overfit steps (lr={args.lr})...")
    print(f"   Cycling over {len(samples)} non-FORWARD sequences.")
    print(f"   {'Step':>4s}  {'Loss':>8s}  {'GradNorm':>10s}  {'Predicted':>10s}  {'GT':>8s}")
    print("   " + "-" * 55)

    for step in range(args.n_steps):
        idx = step % len(samples)
        gt_cls, batch = samples[idx]
        gpu_batch = move_batch_to_gpu(batch)

        model_wrapper.model.train()
        optimizer.zero_grad()

        loss = training_step(model_wrapper, gpu_batch)
        if loss is None or not isinstance(loss, torch.Tensor):
            print(f"   [{step:4d}]  loss=None — model did not return a loss tensor")
            continue

        loss.backward()
        gnorm = grad_norm(trainable_params)
        optimizer.step()

        # Quick inference check (no grad)
        model_wrapper.model.eval()
        logits_step = get_logits_for_batch(model_wrapper, gpu_batch)
        pred_cls = int(np.argmax(logits_step)) if logits_step is not None else -1
        print(f"   {step:4d}  {loss.item():8.4f}  {gnorm:10.4f}  "
              f"{CLASS_NAMES.get(pred_cls, pred_cls):>10s}  {CLASS_NAMES.get(gt_cls, gt_cls):>8s}")

    # -- Logit snapshot after training --
    print("\n📊 Logits AFTER overfit (first sequence):")
    model_wrapper.model.eval()
    logits_after = get_logits_for_batch(model_wrapper, gpu_batch_0)
    probs_after = torch.softmax(torch.tensor(logits_after), dim=0).numpy()
    for c in range(len(logits_after)):
        delta = logits_after[c] - logits_before[c]
        marker = " ← GT" if c == samples[0][0] else ""
        print(f"   {CLASS_NAMES.get(c, c):8s}: logit={logits_after[c]:+.4f}  "
              f"prob={probs_after[c]:.4f}  Δlogit={delta:+.4f}{marker}")

    # -- Summary --
    max_non_fwd_before = max(logits_before[c] for c in range(len(logits_before)) if c != 1)
    max_non_fwd_after  = max(logits_after[c]  for c in range(len(logits_after))  if c != 1)
    fwd_before = logits_before[1]
    fwd_after  = logits_after[1]

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  FORWARD logit:       {fwd_before:+.4f} → {fwd_after:+.4f}  Δ={fwd_after-fwd_before:+.4f}")
    print(f"  max non-FWD logit:   {max_non_fwd_before:+.4f} → {max_non_fwd_after:+.4f}  Δ={max_non_fwd_after-max_non_fwd_before:+.4f}")
    print()

    non_fwd_moved = abs(max_non_fwd_after - max_non_fwd_before) > 0.01
    if non_fwd_moved:
        print("  ✅ Non-FORWARD logits DID move — gradient signal propagating correctly.")
        print("     Collapse is a training/data issue, not a pipeline break.")
    else:
        print("  ❌ Non-FORWARD logits did NOT move (Δ < 0.01).")
        print("     Possible causes:")
        print("     1. Gradients not reaching act_head (check requires_grad)")
        print("     2. Loss is constant (check class weight / label mapping)")
        print("     3. LoRA layers frozen despite config")
    print("=" * 60)


if __name__ == "__main__":
    main()

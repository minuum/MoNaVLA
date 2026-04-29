#!/usr/bin/env python3
"""
Compare Exp11 and Exp14 Step 2 on the exact same held-out episode split.

- Held-out episodes follow the Step 1/2 split rule:
  9 path types x 5 episodes, stratified 80/20 with RNG seed 42.
- Step 2 is retrained on the train episodes and evaluated only on the
  common Exp11-valid window subset.
- Exp11 is evaluated on the same held-out episodes through NavDataset.
"""

import gc
import json
import os
import random
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import h5py
import numpy as np
import torch
import torch.nn as nn
from PIL import Image

# Avoid MPI hang during Lightning import
import lightning.fabric.plugins.environments.mpi as _mpi_env_mod

_mpi_env_mod._MPI4PY_AVAILABLE = False

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "third_party" / "RoboVLMs"))

import robovlms.model.backbone as backbone_mod
import robovlms.model.policy_head as policy_head_mod
import robovlms.train as train_mod
import robovlms.train.base_trainer as base_trainer_mod
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

import main as main_mod

main_mod.BaseTrainer = NavTrainer

from main import load_config

DATA_DIR = ROOT / "ROS_action" / "mobile_vla_dataset_v5"
STEP1_DIR = ROOT / "docs" / "v5" / "bbox_nav_step1"
STEP2_EPOCHS = int(os.environ.get("STEP2_EPOCHS", "20"))
OUT_DIR_NAME = "exp11_vs_step2_same_split_fullep" if STEP2_EPOCHS > 50 else "exp11_vs_step2_same_split"
OUT_DIR = ROOT / "docs" / "v5" / OUT_DIR_NAME
OUT_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_FILE = OUT_DIR / "summary.json"
HTML_FILE = OUT_DIR / "index.html"

DATASET_FILE = STEP1_DIR / "bbox_dataset.json"
EXP11_CONFIG = ROOT / "configs" / "mobile_vla_v5_exp11_google_robot_8cls.json"
EXP11_CKPT = ROOT / "runs" / "v5_nav" / "kosmos" / "mobile_vla_v5_exp11" / "2026-04-16" / "v5-exp11-google-robot-8cls" / "epoch_epoch=epoch=14-val_loss=val_loss=1.010.ckpt"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
PATH_TYPES = [
    "center_straight", "center_left", "center_right",
    "left_straight", "left_left", "left_right",
    "right_straight", "right_left", "right_right",
]
CLASS_NAMES = ["STOP", "FORWARD", "LEFT", "RIGHT", "FWD+L", "FWD+R", "ROT_L", "ROT_R"]
NUM_CLASSES = 8
WINDOW = 3
IMG_SIZE = 16
EXP11_WINDOW = 8
EXP11_FWD = 5


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_bbox_dataset():
    return json.loads(DATASET_FILE.read_text())


def make_step_split(dataset, seed=42):
    rng = np.random.default_rng(seed)
    by_path = defaultdict(list)
    for i, ep in enumerate(dataset):
        by_path[ep["path_type"]].append(i)
    train_idx, test_idx = [], []
    for _, idxs in by_path.items():
        rng.shuffle(idxs)
        k = max(1, int(len(idxs) * 0.2))
        test_idx.extend(idxs[:k])
        train_idx.extend(idxs[k:])
    train_ds = [dataset[i] for i in train_idx]
    test_ds = [dataset[i] for i in test_idx]
    return train_ds, test_ds


def frame_to_small_feature(frame):
    img = Image.fromarray(frame.astype(np.uint8)).convert("L").resize((IMG_SIZE, IMG_SIZE))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return arr.reshape(-1)


def load_episode_frames(stem):
    path = DATA_DIR / f"{stem}.h5"
    with h5py.File(path, "r") as f:
        if "observations" in f and "images" in f["observations"]:
            imgs = f["observations"]["images"][:]
        else:
            imgs = f["images"][:]
    return imgs


def build_windows(dataset, only_exp11_valid=False):
    X, y, meta = [], [], []
    for ep in dataset:
        imgs = load_episode_frames(ep["episode"])
        frames = ep["frames"]
        img_feats = [frame_to_small_feature(imgs[f["frame_idx"]]) for f in frames]
        max_t = len(frames)
        if only_exp11_valid:
            max_t = max(0, len(frames) - EXP11_WINDOW - EXP11_FWD + 1)
        for t in range(max_t):
            feat = []
            for k in range(WINDOW):
                idx = max(0, t - (WINDOW - 1 - k))
                f = frames[idx]
                feat.extend([f["cx"], f["cy"], f["area"], float(f["has_bbox"])])
            feat.extend(img_feats[t].tolist())
            X.append(feat)
            y.append(frames[t]["gt_class"])
            meta.append(
                {
                    "path_type": ep["path_type"],
                    "episode": ep["episode"],
                    "frame_idx": frames[t]["frame_idx"],
                }
            )
    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.int64), meta


def train_step2(X_tr, y_tr, X_te, y_te, seed=42, epochs=20):
    set_seed(seed)
    d_in = X_tr.shape[1]
    model = nn.Sequential(
        nn.Linear(d_in, 256),
        nn.ReLU(),
        nn.Dropout(0.25),
        nn.Linear(256, 128),
        nn.ReLU(),
        nn.Dropout(0.2),
        nn.Linear(128, 64),
        nn.ReLU(),
        nn.Linear(64, NUM_CLASSES),
    ).to(DEVICE)

    cls_counts = np.bincount(y_tr, minlength=NUM_CLASSES).astype(np.float32)
    cls_counts = np.where(cls_counts == 0, 1.0, cls_counts)
    weights = torch.tensor(1.0 / cls_counts, dtype=torch.float32, device=DEVICE)
    weights = weights / weights.sum() * NUM_CLASSES

    loss_fn = nn.CrossEntropyLoss(weight=weights)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)

    X_tr_t = torch.tensor(X_tr, dtype=torch.float32, device=DEVICE)
    y_tr_t = torch.tensor(y_tr, dtype=torch.long, device=DEVICE)
    X_te_t = torch.tensor(X_te, dtype=torch.float32, device=DEVICE)
    y_te_t = torch.tensor(y_te, dtype=torch.long, device=DEVICE)

    best_acc = 0.0
    best_preds = None
    for ep in range(epochs):
        model.train()
        idx = torch.randperm(len(X_tr_t), device=DEVICE)
        for i in range(0, len(idx), 128):
            b = idx[i:i + 128]
            logits = model(X_tr_t[b])
            loss = loss_fn(logits, y_tr_t[b])
            opt.zero_grad()
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            preds = model(X_te_t).argmax(dim=-1)
            acc = (preds == y_te_t).float().mean().item()
            if acc > best_acc:
                best_acc = acc
                best_preds = preds.detach().cpu().numpy()
        if ep % 10 == 0 or ep == epochs - 1:
            print(f"Step2 ep{ep:3d}: loss={loss.item():.3f} acc={acc:.3f} best={best_acc:.3f}")
    return best_acc, best_preds


def path_type_from_stem(stem: str) -> str:
    for pt in PATH_TYPES:
        if f"target_{pt}_path" in stem:
            return pt
    return "unknown"


def load_exp11_model():
    configs = load_config(str(EXP11_CONFIG))
    vlm_path = ROOT / ".vlms" / "kosmos-2-patch14-224"

    def fix_paths(d):
        for k, v in d.items():
            if isinstance(v, str) and "kosmos-2-patch14-224" in v:
                d[k] = str(vlm_path)
            elif isinstance(v, dict):
                fix_paths(v)

    fix_paths(configs)
    if isinstance(configs.get("vlm"), dict):
        configs["vlm"]["pretrained_model_name_or_path"] = str(vlm_path)
    if isinstance(configs.get("tokenizer"), dict):
        configs["tokenizer"]["pretrained_model_name_or_path"] = str(vlm_path)

    from robovlms.train.mobile_vla_trainer import MobileVLATrainer

    model_wrapper = MobileVLATrainer(configs)
    ckpt = torch.load(EXP11_CKPT, map_location="cpu", weights_only=False)
    full_sd = ckpt.get("model_state_dict", ckpt.get("state_dict", {}))
    filtered = {}
    for k, v in full_sd.items():
        if any(x in k for x in ["image_to_text_projection", "act_head", "policy_head", "resampler", "action_token", "lora"]):
            new_k = k.replace("model.", "", 1) if k.startswith("model.") and not hasattr(model_wrapper, "model") else k
            filtered[new_k] = v
    model_wrapper.load_state_dict(filtered, strict=False)
    del ckpt, full_sd, filtered
    gc.collect()
    model_wrapper.to(DEVICE).eval()
    if DEVICE.type == "cuda":
        model_wrapper.half()
    return model_wrapper


def parse_gt(batch, t=0):
    if "action_chunck" in batch:
        ac = batch["action_chunck"].cpu().numpy()
        return int(ac[0, t, 0])
    if "action" in batch:
        return int(batch["action"].cpu().numpy()[0, -1])
    return None


def parse_logits(outputs, t=0):
    if isinstance(outputs, (tuple, list)):
        outputs = outputs[0]
    if outputs is None or not isinstance(outputs, torch.Tensor):
        return None
    arr = outputs.detach().cpu().float().numpy()
    if arr.ndim == 4:
        logits = arr[0, t, 0, :]
    elif arr.ndim == 3:
        logits = arr[0, t, :]
    elif arr.ndim == 2:
        logits = arr[0, :]
    else:
        logits = arr
    return int(np.argmax(logits))


def build_temp_split_dir(test_episodes):
    temp_root = Path(tempfile.mkdtemp(prefix="exp11_same_split_", dir="/tmp"))
    for stem in test_episodes:
        src = DATA_DIR / f"{stem}.h5"
        dst = temp_root / f"{stem}.h5"
        os.symlink(src, dst)
    return temp_root


def eval_exp11_same_split(test_episodes):
    temp_dir = build_temp_split_dir(test_episodes)
    try:
        ds = NavDataset(
            data_dir=str(temp_dir),
            episode_pattern="episode_*.h5",
            model_name="kosmos",
            window_size=EXP11_WINDOW,
            fwd_pred_next_n=EXP11_FWD,
            discrete_action=True,
            num_classes=NUM_CLASSES,
            instruction_preset="default",
            grounding_prefix=True,
            is_validation=True,
            train_split=0.0,
            stratified_split=False,
            exclude_path_types=[],
            min_episode_frames=8,
        )

        model_wrapper = load_exp11_model()
        model = model_wrapper.model

        preds, gts, metas = [], [], []
        with torch.no_grad():
            for i in range(len(ds)):
                sample = ds[i]
                batch = ds.collater([sample])
                device_batch = {}
                for k, v in batch.items():
                    if isinstance(v, torch.Tensor):
                        tensor = v.to(DEVICE)
                        if DEVICE.type == "cuda" and tensor.dtype.is_floating_point:
                            tensor = tensor.half()
                        elif DEVICE.type != "cuda" and tensor.dtype.is_floating_point:
                            tensor = tensor.float()
                        device_batch[k] = tensor
                    else:
                        device_batch[k] = v

                gt = parse_gt(device_batch, t=0)
                outputs = model.forward_action(
                    vision_x=device_batch["rgb"],
                    lang_x=device_batch["text"],
                    attention_mask=device_batch["text_mask"].bool(),
                    vision_gripper=device_batch.get("hand_rgb"),
                    instr_and_action_ids=device_batch.get("instr_and_action_ids"),
                    instr_and_action_labels=device_batch.get("instr_and_action_labels"),
                    instr_and_action_mask=device_batch.get("instr_and_action_mask"),
                    mode="test",
                )
                pred = parse_logits(outputs, t=0)
                ep_idx, start_f = ds.frame_indices[i]
                stem = ds.episode_files[ep_idx].stem
                metas.append(
                    {
                        "episode": stem,
                        "path_type": path_type_from_stem(stem),
                        "frame_idx": int(start_f),
                    }
                )
                preds.append(pred)
                gts.append(gt)

        return np.asarray(preds), np.asarray(gts), metas
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def per_path_summary(preds, gts, metas):
    out = {}
    for pt in PATH_TYPES:
        idxs = [i for i, m in enumerate(metas) if m["path_type"] == pt]
        correct = int(sum(int(preds[i] == gts[i]) for i in idxs))
        out[pt] = {"correct": correct, "total": len(idxs)}
    return out


def build_html(summary):
    rows = []
    for pt in PATH_TYPES:
        a = summary["exp11"]["pm_by_path"][pt]
        b = summary["step2"]["pm_by_path"][pt]
        ap = a["correct"] / max(a["total"], 1)
        bp = b["correct"] / max(b["total"], 1)
        delta = bp - ap
        sign = "+" if delta >= 0 else ""
        rows.append(
            f"<tr><td>{pt}</td><td>{a['correct']}/{a['total']} ({ap:.1%})</td>"
            f"<td>{b['correct']}/{b['total']} ({bp:.1%})</td><td>{sign}{delta:.1%}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Exp11 vs Step2 Same Split</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin:0; padding:24px; background:#0f172a; color:#e2e8f0; }}
  h1 {{ font-size:2rem; margin-bottom:8px; }}
  .sub {{ color:#94a3b8; line-height:1.6; max-width:980px; margin-bottom:24px; }}
  .back {{ color:#60a5fa; text-decoration:none; display:inline-block; margin-bottom:16px; }}
  .grid {{ display:grid; grid-template-columns:repeat(3, 1fr); gap:16px; margin-bottom:24px; }}
  .box {{ background:#1e293b; border-radius:10px; padding:16px 20px; }}
  .lbl {{ color:#94a3b8; text-transform:uppercase; font-size:.85rem; }}
  .num {{ font-size:2.3rem; font-weight:800; margin-top:6px; }}
  .good {{ color:#22c55e; }} .blue {{ color:#60a5fa; }} .warn {{ color:#fbbf24; }}
  table {{ width:100%; border-collapse:collapse; background:#1e293b; border-radius:8px; overflow:hidden; }}
  th, td {{ padding:9px 14px; border-bottom:1px solid #334155; text-align:left; }}
  th {{ background:#0b1220; }}
  .diag {{ background:#172554; border-left:4px solid #60a5fa; color:#dbeafe; padding:14px 18px; border-radius:6px; margin-top:20px; line-height:1.7; }}
</style>
</head>
<body>
  <a class="back" href="../bbox_nav_comparison.html">← Back to Exp14 Comparison</a>
  <h1>Exp11 vs Exp14 Step 2 on Same Split</h1>
  <p class="sub">Step 2의 held-out 9 episode split을 그대로 쓰고, Exp11이 실제로 예측 가능한 공통 valid window subset {summary['common_total']}개에서 직접 비교했습니다.</p>

  <div class="grid">
    <div class="box">
      <div class="lbl">Exp11</div>
      <div class="num blue">{summary['exp11']['overall_pm']:.1%}</div>
      <div>{summary['exp11']['correct']}/{summary['common_total']}</div>
    </div>
    <div class="box">
      <div class="lbl">Step 2</div>
      <div class="num good">{summary['step2']['overall_pm']:.1%}</div>
      <div>{summary['step2']['correct']}/{summary['common_total']}</div>
    </div>
    <div class="box">
      <div class="lbl">Delta</div>
      <div class="num warn">{summary['delta_vs_exp11']:+.1%}</div>
      <div>Step 2 - Exp11</div>
    </div>
  </div>

  <h2>Per Path Type</h2>
  <table>
    <tr><th>Path</th><th>Exp11</th><th>Step 2</th><th>Delta</th></tr>
    {''.join(rows)}
  </table>

  <div class="diag">
    <strong>Notes</strong><br>
    - Exp11은 `window_size=8`, `fwd_pred_next_n=5` 기준의 valid window에서만 예측 가능하므로 공통 subset으로 정렬했습니다.<br>
    - Step 2는 같은 train/test episode split에서 다시 학습한 뒤 같은 subset에서 평가했습니다.<br>
    - 이 페이지의 수치는 기존 Step 2 전체-frame 75.9%와 직접 같은 분모가 아닙니다.
  </div>
</body>
</html>"""
    HTML_FILE.write_text(html)


def main():
    print(f"Using device: {DEVICE}")
    dataset = load_bbox_dataset()
    train_ds, test_ds = make_step_split(dataset, seed=42)
    test_episode_names = [ep["episode"] for ep in test_ds]

    X_tr, y_tr, _ = build_windows(train_ds, only_exp11_valid=False)
    X_te, y_te, meta_te = build_windows(test_ds, only_exp11_valid=True)

    print(f"Train windows for Step 2: {len(X_tr)}")
    print(f"Common test subset: {len(X_te)}")
    print(f"Test episode names: {test_episode_names}")

    step2_acc, step2_preds = train_step2(X_tr, y_tr, X_te, y_te, seed=42, epochs=STEP2_EPOCHS)
    exp11_preds, exp11_gts, exp11_meta = eval_exp11_same_split(test_episode_names)

    if len(exp11_preds) != len(step2_preds):
        raise RuntimeError(f"Length mismatch: exp11={len(exp11_preds)} step2={len(step2_preds)}")

    exp11_keys = [(m["episode"], m["frame_idx"]) for m in exp11_meta]
    step2_key_to_idx = {(m["episode"], m["frame_idx"]): i for i, m in enumerate(meta_te)}
    missing = [k for k in exp11_keys if k not in step2_key_to_idx]
    if missing:
        raise RuntimeError(f"exp11 has {len(missing)} keys not in step2 (e.g. {missing[:3]})")
    order = [step2_key_to_idx[k] for k in exp11_keys]
    step2_preds = step2_preds[order]
    y_te = y_te[order]
    meta_te = [meta_te[i] for i in order]

    for a, b in zip(exp11_meta, meta_te):
        if a["episode"] != b["episode"] or a["frame_idx"] != b["frame_idx"]:
            raise RuntimeError(f"Meta mismatch: {a} != {b}")

    exp11_correct = int((exp11_preds == exp11_gts).sum())
    step2_correct = int((step2_preds == y_te).sum())

    summary = {
        "common_total": int(len(y_te)),
        "test_episodes": test_episode_names,
        "exp11": {
            "correct": exp11_correct,
            "overall_pm": float(exp11_correct / max(len(exp11_gts), 1)),
            "pm_by_path": per_path_summary(exp11_preds, exp11_gts, exp11_meta),
        },
        "step2": {
            "correct": step2_correct,
            "overall_pm": float(step2_acc),
            "pm_by_path": per_path_summary(step2_preds, y_te, meta_te),
        },
        "delta_vs_exp11": float(step2_acc - (exp11_correct / max(len(exp11_gts), 1))),
    }
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2))
    build_html(summary)
    print(json.dumps(summary, indent=2))
    print(f"\nWrote: {SUMMARY_FILE}")
    print(f"Wrote: {HTML_FILE}")


if __name__ == "__main__":
    main()

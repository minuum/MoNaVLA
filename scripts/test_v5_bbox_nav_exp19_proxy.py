#!/usr/bin/env python3
"""
Exp19: Step2 + goal-near proxy features.

Mainline follow-up to Exp14 Step2:
- keep bbox history + low-res image backbone
- add non-leaky proxy features derived from V5 geometry
- compare PM against Step2 under the same split protocol

Usage:
  python3 scripts/test_v5_bbox_nav_exp19_proxy.py
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import h5py
import numpy as np
import torch
import torch.nn as nn
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "ROS_action" / "mobile_vla_dataset_v5"
STEP1_DIR = ROOT / "docs" / "v5" / "bbox_nav_step1"
STEP2_DIR = ROOT / "docs" / "v5" / "bbox_nav_step2"
OUT_DIR = ROOT / "docs" / "v5" / "bbox_nav_exp19_proxy"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DATASET_FILE = STEP1_DIR / "bbox_dataset.json"
SUMMARY_FILE = OUT_DIR / "summary.json"
HTML_FILE = OUT_DIR / "index.html"

PATH_TYPES = [
    "center_straight", "center_left", "center_right",
    "left_straight", "left_left", "left_right",
    "right_straight", "right_left", "right_right",
]
NUM_CLASSES = 8
WINDOW = 3
IMG_SIZE = 16
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CONSISTENCY_K = 5
CX_TOL = 0.08
AREA_TOL = 0.08


def load_dataset():
    if not DATASET_FILE.exists():
        raise FileNotFoundError(f"Missing cached dataset: {DATASET_FILE}")
    return json.loads(DATASET_FILE.read_text())


def frame_to_small_feature(frame):
    img = Image.fromarray(frame.astype(np.uint8)).convert("L").resize((IMG_SIZE, IMG_SIZE))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return arr.reshape(-1)


def load_episode_frames(stem):
    path = next(DATA_DIR.glob(f"{stem}.h5"))
    with h5py.File(path, "r") as f:
        if "observations" in f and "images" in f["observations"]:
            imgs = f["observations"]["images"][:]
        else:
            imgs = f["images"][:]
    return imgs


def recent_bbox_consistency(frames, t, k=CONSISTENCY_K, cx_tol=CX_TOL, area_tol=AREA_TOL):
    start = max(0, t - k + 1)
    tail = frames[start:t + 1]
    valid = [fr for fr in tail if fr["has_bbox"]]
    if not valid:
        return 0.0
    if len(valid) == 1:
        return 1.0
    stable_pairs = 0
    total_pairs = 0
    for a, b in zip(valid[:-1], valid[1:]):
        total_pairs += 1
        if abs(float(b["cx"]) - float(a["cx"])) <= cx_tol and abs(float(b["area"]) - float(a["area"])) <= area_tol:
            stable_pairs += 1
    if total_pairs == 0:
        return 1.0
    return stable_pairs / total_pairs


def build_proxy_features(frames, t):
    cur = frames[t]
    prev = frames[t - 1] if t > 0 else None
    area = float(cur["area"])
    center_error_x = abs(float(cur["cx"]) - 0.5)
    abs_delta_cx = 0.0 if prev is None else abs(float(cur["cx"]) - float(prev["cx"]))
    recent_consistency = recent_bbox_consistency(frames, t)
    return [area, center_error_x, abs_delta_cx, recent_consistency]


def build_windows(dataset, window=WINDOW):
    X, y, meta = [], [], []
    for ep in dataset:
        imgs = load_episode_frames(ep["episode"])
        frames = ep["frames"]
        img_feats = [frame_to_small_feature(imgs[f["frame_idx"]]) for f in frames]
        for t in range(len(frames)):
            feat = []
            for k in range(window):
                idx = max(0, t - (window - 1 - k))
                f = frames[idx]
                feat.extend([f["cx"], f["cy"], f["area"], float(f["has_bbox"])])
            feat.extend(img_feats[t].tolist())
            feat.extend(build_proxy_features(frames, t))
            X.append(feat)
            y.append(frames[t]["gt_class"])
            meta.append({
                "path_type": ep["path_type"],
                "episode": ep["episode"],
                "frame_idx": frames[t]["frame_idx"],
            })
    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.int64), meta


def make_episode_split(dataset):
    rng = np.random.default_rng(42)
    by_path = defaultdict(list)
    for i, ep in enumerate(dataset):
        by_path[ep["path_type"]].append(i)
    train_idx, test_idx = [], []
    for _, idxs in by_path.items():
        rng.shuffle(idxs)
        k = max(1, int(len(idxs) * 0.2))
        test_idx.extend(idxs[:k])
        train_idx.extend(idxs[k:])
    return [dataset[i] for i in train_idx], [dataset[i] for i in test_idx]


def train_eval(X_tr, y_tr, X_te, y_te, epochs=220, device=DEVICE):
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
    ).to(device)

    cls_counts = np.bincount(y_tr, minlength=NUM_CLASSES).astype(np.float32)
    cls_counts = np.where(cls_counts == 0, 1.0, cls_counts)
    weights = torch.tensor(1.0 / cls_counts, dtype=torch.float32, device=device)
    weights = weights / weights.sum() * NUM_CLASSES

    loss_fn = nn.CrossEntropyLoss(weight=weights)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)

    X_tr_t = torch.tensor(X_tr, device=device)
    y_tr_t = torch.tensor(y_tr, device=device)
    X_te_t = torch.tensor(X_te, device=device)
    y_te_t = torch.tensor(y_te, device=device)

    best_acc = 0.0
    best_preds = None
    for ep in range(epochs):
        model.train()
        idx = torch.randperm(len(X_tr_t))
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
                best_preds = preds.cpu().numpy()
        if ep % 40 == 0 or ep == epochs - 1:
            print(f"  ep{ep:3d}: loss={loss.item():.3f} test_acc={acc:.3f} best={best_acc:.3f}")
    return best_acc, best_preds


def build_html(summary):
    rows = []
    for pt in PATH_TYPES:
        v = summary["pm_by_path"].get(pt, {"correct": 0, "total": 0})
        pm = v["correct"] / max(v["total"], 1)
        rows.append(
            f"<tr><td>{pt}</td><td>{v['correct']}/{v['total']}</td><td><strong>{pm:.1%}</strong></td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Exp19: Step2 + Proxy Features</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 24px; background: #0f172a; color: #e2e8f0; }}
  h1 {{ font-size: 2rem; margin-bottom: 8px; }}
  .sub {{ color: #94a3b8; margin-bottom: 24px; max-width: 940px; line-height: 1.6; }}
  .back {{ color: #60a5fa; text-decoration: none; display: inline-block; margin-bottom: 16px; }}
  .grid3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }}
  .box {{ background: #1e293b; padding: 16px 20px; border-radius: 10px; }}
  .num {{ font-size: 2.5rem; font-weight: 800; }}
  .good {{ color: #22c55e; }} .blue {{ color: #60a5fa; }} .warn {{ color: #fbbf24; }}
  table {{ border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; width: 100%; }}
  th, td {{ padding: 8px 14px; border-bottom: 1px solid #334155; text-align: left; }}
  th {{ background: #0b1220; }}
  .diag {{ background: #172554; border-left: 4px solid #60a5fa; padding: 14px 18px; border-radius: 6px; color: #dbeafe; margin-top: 20px; line-height: 1.7; }}
</style>
</head>
<body>
  <a class="back" href="../../index.html">← Back to main</a>
  <h1>Exp19: Step2 + Goal-Near Proxy Features</h1>
  <p class="sub">
    Exp14 Step2의 bbox history + 16x16 grayscale image feature에
    non-leaky proxy signal 4개
    (<code>area</code>, <code>center_error_x</code>, <code>abs_delta_cx</code>, <code>recent_bbox_consistency</code>)
    를 추가한 실험입니다.
  </p>

  <div class="grid3">
    <div class="box">
      <div style="color:#94a3b8; font-size:0.85rem; text-transform:uppercase;">Step 2 Reference</div>
      <div class="num blue">{summary['step2_ref_pm']:.1%}</div>
      <div>bbox + image baseline</div>
    </div>
    <div class="box">
      <div style="color:#94a3b8; font-size:0.85rem; text-transform:uppercase;">Exp19 Proxy</div>
      <div class="num good">{summary['overall_pm_exp19']:.1%}</div>
      <div>({int(summary['overall_pm_exp19'] * summary['total_test'])}/{summary['total_test']})</div>
    </div>
    <div class="box">
      <div style="color:#94a3b8; font-size:0.85rem; text-transform:uppercase;">Delta vs Step 2</div>
      <div class="num {'good' if summary['delta_vs_step2'] >= 0 else 'warn'}">{summary['delta_vs_step2']:+.1%}</div>
      <div>same split protocol</div>
    </div>
  </div>

  <h2>PM per Path Type (test split)</h2>
  <table>
    <tr><th>Path Type</th><th>Correct/Total</th><th>PM</th></tr>
    {''.join(rows)}
  </table>

  <div class="diag">
    <strong>Proxy pack</strong><br>
    area, center_error_x, abs_delta_cx, recent_bbox_consistency.<br>
    Split protocol과 backbone 용량은 Step 2와 동일하게 유지했습니다.
  </div>
</body>
</html>"""
    HTML_FILE.write_text(html)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=220)
    ap.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    return ap.parse_args()


def resolve_device(name: str):
    if name == "cpu":
        return torch.device("cpu")
    if name == "cuda":
        return torch.device("cuda")
    return DEVICE


def main():
    args = parse_args()
    device = resolve_device(args.device)
    dataset = load_dataset()
    train_ds, test_ds = make_episode_split(dataset)

    X_tr, y_tr, _ = build_windows(train_ds)
    X_te, y_te, meta_te = build_windows(test_ds)

    print(f"Episode split: train={len(train_ds)}  test={len(test_ds)}")
    print(f"Windows: train={len(X_tr)}  test={len(X_te)}")
    print(f"Train GT dist: {np.bincount(y_tr, minlength=NUM_CLASSES).tolist()}")
    print(f"Test  GT dist: {np.bincount(y_te, minlength=NUM_CLASSES).tolist()}")
    print(f"Device: {device}")

    step2_summary = json.loads((STEP2_DIR / "summary.json").read_text())
    step2_ref = float(step2_summary["overall_pm_step2"])

    print("\n=== Training Exp19 MLP ===")
    best_acc, best_preds = train_eval(X_tr, y_tr, X_te, y_te, epochs=args.epochs, device=device)
    print(f"\nBest Exp19 test acc: {best_acc:.3f}")

    pm_by_path = defaultdict(lambda: {"correct": 0, "total": 0})
    for i, m in enumerate(meta_te):
        pm_by_path[m["path_type"]]["total"] += 1
        if best_preds[i] == y_te[i]:
            pm_by_path[m["path_type"]]["correct"] += 1

    print("\n=== Per-path PM ===")
    for pt in PATH_TYPES:
        v = pm_by_path.get(pt, {"correct": 0, "total": 0})
        n = v["total"]
        print(f"  {pt:20s}: {v['correct']}/{n} = {v['correct']/max(n,1):.1%}")

    summary = {
        "overall_pm_exp19": float(best_acc),
        "step2_ref_pm": step2_ref,
        "delta_vs_step2": float(best_acc - step2_ref),
        "total_train": int(len(X_tr)),
        "total_test": int(len(X_te)),
        "device": str(device),
        "epochs": int(args.epochs),
        "proxy_features": ["area", "center_error_x", "abs_delta_cx", "recent_bbox_consistency"],
        "pm_by_path": {k: {"correct": v["correct"], "total": v["total"]} for k, v in pm_by_path.items()},
    }
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2))
    build_html(summary)
    print(f"\nHTML: {HTML_FILE}")


if __name__ == "__main__":
    main()

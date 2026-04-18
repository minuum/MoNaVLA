#!/usr/bin/env python3
"""
Exp14 Step 2: BBox history + low-res image feature -> learned MLP

Step 1이 bbox history만으로 68.4%까지 올렸다면,
Step 2는 같은 bbox history에 아주 작은 image feature를 붙여
center_left / center_right 같은 애매한 케이스를 더 구분할 수 있는지 본다.

Usage:
  python3 scripts/test_v5_bbox_nav_step2.py
"""

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
OUT_DIR = ROOT / "docs" / "v5" / "bbox_nav_step2"
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


def rule_pred_from_window(x):
    cx = x[8]
    area = x[10]
    if area > 0.35:
        return 0
    if cx < 0.30:
        return 2 if cx < 0.15 else 4
    if cx > 0.70:
        return 3 if cx > 0.85 else 5
    return 1


def train_eval(X_tr, y_tr, X_te, y_te, epochs=220):
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

    X_tr_t = torch.tensor(X_tr, device=DEVICE)
    y_tr_t = torch.tensor(y_tr, device=DEVICE)
    X_te_t = torch.tensor(X_te, device=DEVICE)
    y_te_t = torch.tensor(y_te, device=DEVICE)

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
<title>Exp14 Step 2: BBox + Image Feature MLP</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 24px; background: #0f172a; color: #e2e8f0; }}
  h1 {{ font-size: 2rem; margin-bottom: 8px; }}
  .sub {{ color: #94a3b8; margin-bottom: 24px; max-width: 900px; line-height: 1.6; }}
  .back {{ color: #60a5fa; text-decoration: none; display: inline-block; margin-bottom: 16px; }}
  .grid3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }}
  .box {{ background: #1e293b; padding: 16px 20px; border-radius: 10px; }}
  .num {{ font-size: 2.5rem; font-weight: 800; }}
  .good {{ color: #22c55e; }} .warn {{ color: #fbbf24; }} .blue {{ color: #60a5fa; }}
  table {{ border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; width: 100%; }}
  th, td {{ padding: 8px 14px; border-bottom: 1px solid #334155; text-align: left; }}
  th {{ background: #0b1220; }}
  .diag {{ background: #172554; border-left: 4px solid #60a5fa; padding: 14px 18px; border-radius: 6px; color: #dbeafe; margin-top: 20px; line-height: 1.7; }}
</style>
</head>
<body>
  <a class="back" href="../../index.html">← Back to main</a>
  <h1>Exp14 Step 2: BBox + Image Feature MLP</h1>
  <p class="sub">
    Step 1의 BBox history feature에 16x16 grayscale image feature를 추가한 경량 MLP입니다.
    목적은 center_left / center_right 같은 애매한 장면에서 bbox만으로 부족한 시각 정보를 보완하는 것입니다.
  </p>

  <div class="grid3">
    <div class="box">
      <div style="color:#94a3b8; font-size:0.85rem; text-transform:uppercase;">Rule on test split</div>
      <div class="num warn">{summary['overall_pm_rule']:.1%}</div>
      <div>Step 1 split 기준</div>
    </div>
    <div class="box">
      <div style="color:#94a3b8; font-size:0.85rem; text-transform:uppercase;">Step 1 MLP</div>
      <div class="num blue">{summary['overall_pm_step1_ref']:.1%}</div>
      <div>BBox only reference</div>
    </div>
    <div class="box">
      <div style="color:#94a3b8; font-size:0.85rem; text-transform:uppercase;">Step 2 MLP</div>
      <div class="num good">{summary['overall_pm_step2']:.1%}</div>
      <div>({int(summary['overall_pm_step2'] * summary['total_test'])}/{summary['total_test']})</div>
    </div>
  </div>

  <h2>PM per Path Type (test split)</h2>
  <table>
    <tr><th>Path Type</th><th>Correct/Total</th><th>PM</th></tr>
    {''.join(rows)}
  </table>

  <div class="diag">
    <strong>설정</strong><br>
    입력: recent {WINDOW} frame bbox history + current frame 16x16 grayscale image feature.<br>
    출력: 8-class discrete action.<br>
    기준 비교값: Step 1 bbox-only MLP {summary['overall_pm_step1_ref']:.1%}.
  </div>
</body>
</html>"""
    HTML_FILE.write_text(html)


def main():
    dataset = load_dataset()
    train_ds, test_ds = make_episode_split(dataset)

    X_tr, y_tr, _ = build_windows(train_ds)
    X_te, y_te, meta_te = build_windows(test_ds)

    print(f"Episode split: train={len(train_ds)}  test={len(test_ds)}")
    print(f"Windows: train={len(X_tr)}  test={len(X_te)}")
    print(f"Train GT dist: {np.bincount(y_tr, minlength=NUM_CLASSES).tolist()}")
    print(f"Test  GT dist: {np.bincount(y_te, minlength=NUM_CLASSES).tolist()}")

    rule_preds = [rule_pred_from_window(X_te[i]) for i in range(len(X_te))]
    rule_acc = np.mean([rule_preds[i] == y_te[i] for i in range(len(y_te))])
    print(f"\nRule test acc: {rule_acc:.3f}")

    step1_summary = json.loads((STEP1_DIR / "summary.json").read_text())
    step1_ref = float(step1_summary["overall_pm_mlp"])

    print("\n=== Training Step 2 MLP ===")
    best_acc, best_preds = train_eval(X_tr, y_tr, X_te, y_te)
    print(f"\nBest Step 2 test acc: {best_acc:.3f}")

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
        "overall_pm_rule": float(rule_acc),
        "overall_pm_step1_ref": step1_ref,
        "overall_pm_step2": float(best_acc),
        "total_train": int(len(X_tr)),
        "total_test": int(len(X_te)),
        "pm_by_path": {k: {"correct": v["correct"], "total": v["total"]} for k, v in pm_by_path.items()},
    }
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2))
    build_html(summary)
    print(f"\nHTML: {HTML_FILE}")


if __name__ == "__main__":
    main()

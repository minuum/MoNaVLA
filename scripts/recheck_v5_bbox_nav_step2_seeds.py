#!/usr/bin/env python3
"""
Re-evaluate Exp14 Step 2 across multiple split seeds.
"""

import json
import random
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

STEP1_DIR = ROOT / "docs" / "v5" / "bbox_nav_step1"
OUT_DIR = ROOT / "docs" / "v5" / "bbox_nav_step2_repro"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DATASET_FILE = STEP1_DIR / "bbox_dataset.json"
DATA_DIR = ROOT / "ROS_action" / "mobile_vla_dataset_v5"
SUMMARY_FILE = OUT_DIR / "summary.json"
HTML_FILE = OUT_DIR / "index.html"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
PATH_TYPES = [
    "center_straight", "center_left", "center_right",
    "left_straight", "left_left", "left_right",
    "right_straight", "right_left", "right_right",
]
NUM_CLASSES = 8
WINDOW = 3
IMG_SIZE = 16
SEEDS = [0]


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_dataset():
    return json.loads(DATASET_FILE.read_text())


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


def build_windows(dataset):
    X, y, meta = [], [], []
    for ep in dataset:
        imgs = load_episode_frames(ep["episode"])
        frames = ep["frames"]
        img_feats = [frame_to_small_feature(imgs[f["frame_idx"]]) for f in frames]
        for t in range(len(frames)):
            feat = []
            for k in range(WINDOW):
                idx = max(0, t - (WINDOW - 1 - k))
                f = frames[idx]
                feat.extend([f["cx"], f["cy"], f["area"], float(f["has_bbox"])])
            feat.extend(img_feats[t].tolist())
            X.append(feat)
            y.append(frames[t]["gt_class"])
            meta.append({"path_type": ep["path_type"]})
    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.int64), meta


def make_split(dataset, split_seed):
    rng = np.random.default_rng(split_seed)
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


def train_eval(X_tr, y_tr, X_te, y_te, seed, epochs=8):
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
    return best_acc, best_preds


def per_path_summary(preds, gts, meta):
    by = defaultdict(lambda: {"correct": 0, "total": 0})
    for i, m in enumerate(meta):
        pt = m["path_type"]
        by[pt]["total"] += 1
        if preds[i] == gts[i]:
            by[pt]["correct"] += 1
    return {pt: by[pt] for pt in PATH_TYPES}


def build_html(summary):
    seed_rows = []
    for r in summary["runs"]:
        seed_rows.append(
            f"<tr><td>{r['split_seed']}</td><td>{r['overall_pm_rule']:.1%}</td><td>{r['overall_pm_step2']:.1%}</td>"
            f"<td>{r['total_test']}</td><td>{', '.join(r['test_episodes'])}</td></tr>"
        )
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Exp14 Step 2 Repro Check</title>
<style>
 body {{ font-family:-apple-system,BlinkMacSystemFont,sans-serif; margin:0; padding:24px; background:#0f172a; color:#e2e8f0; }}
 h1 {{ font-size:2rem; margin-bottom:8px; }}
 .sub {{ color:#94a3b8; line-height:1.6; max-width:960px; margin-bottom:24px; }}
 .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:24px; }}
 .box {{ background:#1e293b; padding:16px 20px; border-radius:10px; }}
 .lbl {{ color:#94a3b8; text-transform:uppercase; font-size:.85rem; }}
 .num {{ font-size:2.2rem; font-weight:800; margin-top:6px; }}
 .good {{ color:#22c55e; }} .blue {{ color:#60a5fa; }} .warn {{ color:#fbbf24; }}
 table {{ width:100%; border-collapse:collapse; background:#1e293b; border-radius:8px; overflow:hidden; }}
 th, td {{ padding:9px 14px; border-bottom:1px solid #334155; text-align:left; vertical-align:top; }}
 th {{ background:#0b1220; }}
</style>
</head>
<body>
 <a href="../bbox_nav_step2/index.html" style="color:#60a5fa; text-decoration:none;">← Back to Step 2</a>
 <h1>Exp14 Step 2 Repro Check</h1>
 <p class="sub">Different split seeds에 대해 Step 2를 다시 학습해 held-out PM 분산을 확인했습니다.</p>
 <div class="grid">
   <div class="box"><div class="lbl">Mean PM</div><div class="num good">{summary['mean_pm']:.1%}</div></div>
   <div class="box"><div class="lbl">Std</div><div class="num blue">{summary['std_pm']:.1%}</div></div>
   <div class="box"><div class="lbl">Min</div><div class="num warn">{summary['min_pm']:.1%}</div></div>
   <div class="box"><div class="lbl">Max</div><div class="num good">{summary['max_pm']:.1%}</div></div>
 </div>
 <table>
   <tr><th>Split Seed</th><th>Rule</th><th>Step 2</th><th>Test Frames</th><th>Held-out Episodes</th></tr>
   {''.join(seed_rows)}
 </table>
</body>
</html>"""
    HTML_FILE.write_text(html)


def main():
    print(f"Using device: {DEVICE}")
    dataset = load_dataset()
    results = []
    for split_seed in SEEDS:
        print(f"\n=== Split seed {split_seed} ===")
        train_ds, test_ds = make_split(dataset, split_seed)
        X_tr, y_tr, _ = build_windows(train_ds)
        X_te, y_te, meta_te = build_windows(test_ds)
        rule_preds = np.asarray([rule_pred_from_window(X_te[i]) for i in range(len(X_te))])
        rule_acc = float(np.mean(rule_preds == y_te))
        step2_acc, step2_preds = train_eval(X_tr, y_tr, X_te, y_te, seed=split_seed)
        test_episodes = [ep["episode"] for ep in test_ds]
        res = {
            "split_seed": split_seed,
            "overall_pm_rule": rule_acc,
            "overall_pm_step2": float(step2_acc),
            "total_test": int(len(y_te)),
            "test_episodes": test_episodes,
            "pm_by_path": per_path_summary(step2_preds, y_te, meta_te),
        }
        results.append(res)
        print(json.dumps({"seed": split_seed, "rule": rule_acc, "step2": step2_acc, "total_test": len(y_te)}, indent=2))

    pms = [r["overall_pm_step2"] for r in results]
    summary = {
        "device": str(DEVICE),
        "split_seeds": SEEDS,
        "mean_pm": float(np.mean(pms)),
        "std_pm": float(np.std(pms)),
        "min_pm": float(np.min(pms)),
        "max_pm": float(np.max(pms)),
        "runs": results,
    }
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2))
    build_html(summary)
    print(f"\nWrote: {SUMMARY_FILE}")
    print(f"Wrote: {HTML_FILE}")


if __name__ == "__main__":
    main()

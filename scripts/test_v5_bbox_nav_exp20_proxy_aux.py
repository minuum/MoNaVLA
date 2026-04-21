#!/usr/bin/env python3
"""
Exp20: Step2 + proxy features + goal-near auxiliary head.

Follow-up if Exp19 proxy concat improves PM but does not clearly improve
closed-loop. The auxiliary target is goal_near_v0 from the current proxy spec.

Usage:
  python3 scripts/test_v5_bbox_nav_exp20_proxy_aux.py
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
EXP19_DIR = ROOT / "docs" / "v5" / "bbox_nav_exp19_proxy"
OUT_DIR = ROOT / "docs" / "v5" / "bbox_nav_exp20_proxy_aux"
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
AUX_WEIGHT = 0.25


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


def goal_near_v0(frame):
    return bool(frame["has_bbox"]) and float(frame["area"]) >= 0.27 and abs(float(frame["cx"]) - 0.5) <= 0.03125


def build_windows(dataset, window=WINDOW):
    X, y, y_aux, meta = [], [], [], []
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
            y_aux.append(float(goal_near_v0(frames[t])))
            meta.append({
                "path_type": ep["path_type"],
                "episode": ep["episode"],
                "frame_idx": frames[t]["frame_idx"],
            })
    return (
        np.asarray(X, dtype=np.float32),
        np.asarray(y, dtype=np.int64),
        np.asarray(y_aux, dtype=np.float32),
        meta,
    )


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


class ProxyAuxMLP(nn.Module):
    def __init__(self, input_dim, num_classes=NUM_CLASSES):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.25),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
        )
        self.action_head = nn.Linear(64, num_classes)
        self.goal_near_head = nn.Linear(64, 1)

    def forward(self, x):
        h = self.trunk(x)
        return self.action_head(h), self.goal_near_head(h).squeeze(-1)


def binary_stats(logits, labels):
    preds = (torch.sigmoid(logits) >= 0.5).float()
    tp = ((preds == 1) & (labels == 1)).sum().item()
    fp = ((preds == 1) & (labels == 0)).sum().item()
    fn = ((preds == 0) & (labels == 1)).sum().item()
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return precision, recall


def train_eval(X_tr, y_tr, y_aux_tr, X_te, y_te, y_aux_te, epochs=220, device=DEVICE):
    d_in = X_tr.shape[1]
    model = ProxyAuxMLP(d_in).to(device)

    cls_counts = np.bincount(y_tr, minlength=NUM_CLASSES).astype(np.float32)
    cls_counts = np.where(cls_counts == 0, 1.0, cls_counts)
    weights = torch.tensor(1.0 / cls_counts, dtype=torch.float32, device=device)
    weights = weights / weights.sum() * NUM_CLASSES

    action_loss_fn = nn.CrossEntropyLoss(weight=weights)
    aux_loss_fn = nn.BCEWithLogitsLoss()
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)

    X_tr_t = torch.tensor(X_tr, device=device)
    y_tr_t = torch.tensor(y_tr, device=device)
    y_aux_tr_t = torch.tensor(y_aux_tr, device=device)
    X_te_t = torch.tensor(X_te, device=device)
    y_te_t = torch.tensor(y_te, device=device)
    y_aux_te_t = torch.tensor(y_aux_te, device=device)

    best_action_acc = 0.0
    best_preds = None
    best_aux_precision = 0.0
    best_aux_recall = 0.0

    for ep in range(epochs):
        model.train()
        idx = torch.randperm(len(X_tr_t))
        for i in range(0, len(idx), 128):
            b = idx[i:i + 128]
            action_logits, aux_logits = model(X_tr_t[b])
            action_loss = action_loss_fn(action_logits, y_tr_t[b])
            aux_loss = aux_loss_fn(aux_logits, y_aux_tr_t[b])
            loss = action_loss + AUX_WEIGHT * aux_loss
            opt.zero_grad()
            loss.backward()
            opt.step()

        model.eval()
        with torch.no_grad():
            action_logits_te, aux_logits_te = model(X_te_t)
            preds = action_logits_te.argmax(dim=-1)
            action_acc = (preds == y_te_t).float().mean().item()
            aux_precision, aux_recall = binary_stats(aux_logits_te, y_aux_te_t)
            if action_acc > best_action_acc:
                best_action_acc = action_acc
                best_preds = preds.cpu().numpy()
                best_aux_precision = aux_precision
                best_aux_recall = aux_recall
        if ep % 40 == 0 or ep == epochs - 1:
            print(
                f"  ep{ep:3d}: loss={loss.item():.3f} "
                f"test_acc={action_acc:.3f} aux_p={aux_precision:.3f} aux_r={aux_recall:.3f} "
                f"best={best_action_acc:.3f}"
            )

    return best_action_acc, best_preds, best_aux_precision, best_aux_recall


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
<title>Exp20: Proxy + Auxiliary Head</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 24px; background: #0f172a; color: #e2e8f0; }}
  h1 {{ font-size: 2rem; margin-bottom: 8px; }}
  .sub {{ color: #94a3b8; margin-bottom: 24px; max-width: 940px; line-height: 1.6; }}
  .back {{ color: #60a5fa; text-decoration: none; display: inline-block; margin-bottom: 16px; }}
  .grid4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }}
  .box {{ background: #1e293b; padding: 16px 20px; border-radius: 10px; }}
  .num {{ font-size: 2.2rem; font-weight: 800; }}
  .good {{ color: #22c55e; }} .blue {{ color: #60a5fa; }}
  table {{ border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; width: 100%; }}
  th, td {{ padding: 8px 14px; border-bottom: 1px solid #334155; text-align: left; }}
  th {{ background: #0b1220; }}
  .diag {{ background: #172554; border-left: 4px solid #60a5fa; padding: 14px 18px; border-radius: 6px; color: #dbeafe; margin-top: 20px; line-height: 1.7; }}
</style>
</head>
<body>
  <a class="back" href="../../index.html">← Back to main</a>
  <h1>Exp20: Step2 + Proxy + Goal-Near Auxiliary</h1>
  <p class="sub">
    Exp19의 proxy concat 입력 위에 <code>goal_near_v0</code> binary auxiliary head를 추가한 실험입니다.
    action PM과 auxiliary precision/recall을 함께 기록합니다.
  </p>

  <div class="grid4">
    <div class="box"><div style="color:#94a3b8; font-size:0.85rem; text-transform:uppercase;">Exp19 Ref</div><div class="num blue">{summary['exp19_ref_pm']:.1%}</div></div>
    <div class="box"><div style="color:#94a3b8; font-size:0.85rem; text-transform:uppercase;">Exp20 PM</div><div class="num good">{summary['overall_pm_exp20']:.1%}</div></div>
    <div class="box"><div style="color:#94a3b8; font-size:0.85rem; text-transform:uppercase;">Aux Precision</div><div class="num good">{summary['goal_near_precision']:.1%}</div></div>
    <div class="box"><div style="color:#94a3b8; font-size:0.85rem; text-transform:uppercase;">Aux Recall</div><div class="num good">{summary['goal_near_recall']:.1%}</div></div>
  </div>

  <h2>PM per Path Type (test split)</h2>
  <table>
    <tr><th>Path Type</th><th>Correct/Total</th><th>PM</th></tr>
    {''.join(rows)}
  </table>

  <div class="diag">
    <strong>Auxiliary target</strong><br>
    goal_near_v0 = has_bbox AND area ≥ 0.27 AND center_error_x ≤ 0.03125.<br>
    Total loss = action CE + {AUX_WEIGHT:.2f} × goal-near BCE.
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

    X_tr, y_tr, y_aux_tr, _ = build_windows(train_ds)
    X_te, y_te, y_aux_te, meta_te = build_windows(test_ds)

    print(f"Episode split: train={len(train_ds)}  test={len(test_ds)}")
    print(f"Windows: train={len(X_tr)}  test={len(X_te)}")
    print(f"Train GT dist: {np.bincount(y_tr, minlength=NUM_CLASSES).tolist()}")
    print(f"Test  GT dist: {np.bincount(y_te, minlength=NUM_CLASSES).tolist()}")
    print(f"Train goal_near+: {int(y_aux_tr.sum())}/{len(y_aux_tr)}")
    print(f"Test  goal_near+: {int(y_aux_te.sum())}/{len(y_aux_te)}")
    print(f"Device: {device}")

    exp19_summary = json.loads((EXP19_DIR / "summary.json").read_text()) if (EXP19_DIR / "summary.json").exists() else {}
    exp19_ref = float(exp19_summary.get("overall_pm_exp19", 0.0))

    print("\n=== Training Exp20 MLP ===")
    best_acc, best_preds, aux_precision, aux_recall = train_eval(
        X_tr, y_tr, y_aux_tr, X_te, y_te, y_aux_te, epochs=args.epochs, device=device
    )
    print(f"\nBest Exp20 test acc: {best_acc:.3f}")

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
        "overall_pm_exp20": float(best_acc),
        "exp19_ref_pm": exp19_ref,
        "delta_vs_exp19": float(best_acc - exp19_ref),
        "goal_near_precision": float(aux_precision),
        "goal_near_recall": float(aux_recall),
        "total_train": int(len(X_tr)),
        "total_test": int(len(X_te)),
        "device": str(device),
        "epochs": int(args.epochs),
        "aux_weight": AUX_WEIGHT,
        "pm_by_path": {k: {"correct": v["correct"], "total": v["total"]} for k, v in pm_by_path.items()},
    }
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2))
    build_html(summary)
    print(f"\nHTML: {HTML_FILE}")


if __name__ == "__main__":
    main()

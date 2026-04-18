#!/usr/bin/env python3
"""
Exp14 Step 2 Feature Ablation: BBox vs Image vs BBox+Image

Step 1(68.4%)과 Step 2(75.9%)의 +7.5%p가
- image feature 추가 효과인지
- MLP 용량 증가 효과인지
분리하기 위한 공정 비교.

3 conditions × 5 seeds, 동일 MLP backbone, 동일 하이퍼파라미터.
캐시된 bbox_dataset.json 재사용 (Pure HF Kosmos-2 grounding 재실행 불필요).

Usage:
  python3 scripts/ablate_bbox_image_features.py
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
OUT_DIR = ROOT / "docs" / "v5" / "bbox_nav_feature_ablation"
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

FEATURE_SPECS = {
    "bbox_only":  {"use_bbox": True,  "use_image": False, "d_in": WINDOW * 4},
    "image_only": {"use_bbox": False, "use_image": True,  "d_in": IMG_SIZE * IMG_SIZE},
    "bbox_image": {"use_bbox": True,  "use_image": True,  "d_in": WINDOW * 4 + IMG_SIZE * IMG_SIZE},
}
SEEDS = [0, 1, 2, 3, 4]
EPOCHS = 220


def load_dataset():
    if not DATASET_FILE.exists():
        raise FileNotFoundError(f"Missing cached dataset: {DATASET_FILE}\nRun test_v5_bbox_nav_step1.py first.")
    return json.loads(DATASET_FILE.read_text())


def load_episode_frames(stem):
    path = next(DATA_DIR.glob(f"{stem}.h5"))
    with h5py.File(path, "r") as f:
        if "observations" in f and "images" in f["observations"]:
            imgs = f["observations"]["images"][:]
        else:
            imgs = f["images"][:]
    return imgs


def frame_to_image_feature(frame):
    img = Image.fromarray(frame.astype(np.uint8)).convert("L").resize((IMG_SIZE, IMG_SIZE))
    return np.asarray(img, dtype=np.float32).reshape(-1) / 255.0


def build_windows(dataset, spec, window=WINDOW):
    use_bbox = spec["use_bbox"]
    use_image = spec["use_image"]
    X, y, meta = [], [], []
    for ep in dataset:
        frames = ep["frames"]
        # Load raw images if needed
        img_feats = None
        if use_image:
            imgs = load_episode_frames(ep["episode"])
            img_feats = [frame_to_image_feature(imgs[f["frame_idx"]]) for f in frames]

        for t in range(len(frames)):
            feat = []
            if use_bbox:
                for k in range(window):
                    idx = max(0, t - (window - 1 - k))
                    f = frames[idx]
                    feat.extend([f["cx"], f["cy"], f["area"], float(f["has_bbox"])])
            if use_image:
                feat.extend(img_feats[t].tolist())
            X.append(feat)
            y.append(frames[t]["gt_class"])
            meta.append({
                "path_type": ep["path_type"],
                "episode": ep["episode"],
                "frame_idx": frames[t]["frame_idx"],
            })
    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.int64), meta


def make_episode_split(dataset, seed):
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
    return [dataset[i] for i in train_idx], [dataset[i] for i in test_idx]


def make_mlp(d_in):
    """Fixed backbone across all 3 conditions (same capacity as Step 2)."""
    return nn.Sequential(
        nn.Linear(d_in, 256), nn.ReLU(), nn.Dropout(0.25),
        nn.Linear(256, 128), nn.ReLU(), nn.Dropout(0.2),
        nn.Linear(128, 64), nn.ReLU(),
        nn.Linear(64, NUM_CLASSES),
    ).to(DEVICE)


def train_eval(X_tr, y_tr, X_te, y_te, d_in, seed):
    torch.manual_seed(seed)
    model = make_mlp(d_in)

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
    for ep in range(EPOCHS):
        model.train()
        idx = torch.randperm(len(X_tr_t))
        for i in range(0, len(idx), 128):
            b = idx[i:i + 128]
            logits = model(X_tr_t[b])
            loss = loss_fn(logits, y_tr_t[b])
            opt.zero_grad(); loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            preds = model(X_te_t).argmax(dim=-1)
            acc = (preds == y_te_t).float().mean().item()
            if acc > best_acc:
                best_acc = acc
                best_preds = preds.cpu().numpy()
        if ep % 44 == 0 or ep == EPOCHS - 1:
            print(f"    ep{ep:3d}: loss={loss.item():.3f} acc={acc:.3f} best={best_acc:.3f}")
    return best_acc, best_preds


def per_path_pm(meta_te, y_te, preds):
    pm = defaultdict(lambda: {"correct": 0, "total": 0})
    for i, m in enumerate(meta_te):
        pm[m["path_type"]]["total"] += 1
        if preds[i] == y_te[i]:
            pm[m["path_type"]]["correct"] += 1
    return {k: dict(v) for k, v in pm.items()}


def build_html(results):
    spec_order = ["bbox_only", "image_only", "bbox_image"]
    colors = {"bbox_only": "#60a5fa", "image_only": "#fbbf24", "bbox_image": "#22c55e"}
    labels = {"bbox_only": "BBox-only", "image_only": "Image-only", "bbox_image": "BBox+Image"}

    # Summary boxes
    boxes = ""
    for name in spec_order:
        r = results[name]
        col = colors[name]
        boxes += f"""
    <div class="box">
      <div style="color:#94a3b8; font-size:0.85rem; text-transform:uppercase;">{labels[name]}</div>
      <div class="num" style="color:{col};">{r['mean_pm']:.1%}</div>
      <div style="color:#64748b;">± {r['std_pm']:.1%} (5 seeds)</div>
    </div>"""

    # Per-path table
    header = "<th>Path Type</th>" + "".join(f"<th style='color:{colors[n]}'>{labels[n]}</th>" for n in spec_order)
    rows = ""
    for pt in PATH_TYPES:
        cells = f"<td>{pt}</td>"
        for name in spec_order:
            r = results[name]
            v = r["pm_by_path_mean"].get(pt, 0.0)
            cells += f"<td>{v:.1%}</td>"
        rows += f"<tr>{cells}</tr>"

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Exp14 Feature Ablation: BBox vs Image</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 24px; background: #0f172a; color: #e2e8f0; }}
  h1 {{ font-size: 2rem; margin-bottom: 8px; }}
  .sub {{ color: #94a3b8; margin-bottom: 24px; max-width: 900px; line-height: 1.6; }}
  .back {{ color: #60a5fa; text-decoration: none; display: inline-block; margin-bottom: 16px; }}
  .grid3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }}
  .box {{ background: #1e293b; padding: 16px 20px; border-radius: 10px; }}
  .num {{ font-size: 2.5rem; font-weight: 800; }}
  table {{ border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; width: 100%; margin-top: 16px; }}
  th, td {{ padding: 8px 14px; border-bottom: 1px solid #334155; text-align: left; }}
  th {{ background: #0b1220; }}
  .diag {{ background: #172554; border-left: 4px solid #60a5fa; padding: 14px 18px; border-radius: 6px; color: #dbeafe; margin-top: 20px; line-height: 1.7; }}
</style>
</head>
<body>
  <a class="back" href="../../index.html">← Back to main</a>
  <h1>Exp14 Feature Ablation: BBox vs Image</h1>
  <p class="sub">
    동일 MLP 용량(256→128→64)에서 input feature 조합만 바꿔 Step 1→Step 2의
    +7.5%p 향상이 image feature 덕분인지 아키텍처 용량 증가 덕분인지 분리한다.
    각 조건 5 split seed로 mean ± std 보고.
  </p>

  <div class="grid3">{boxes}
  </div>

  <h2>PM per Path Type (seed-averaged)</h2>
  <table>
    <tr>{header}</tr>
    {rows}
  </table>

  <div class="diag">
    <strong>설정</strong><br>
    MLP backbone: Linear(d, 256)→ReLU→Dropout(0.25)→Linear(256,128)→ReLU→Dropout(0.2)→Linear(128,64)→ReLU→Linear(64,8)<br>
    lr=2e-3, epochs=220, batch=128, AdamW, inverse-frequency class weights.<br>
    Dataset: bbox_dataset.json (45 eps, 794 frames, Pure HF Kosmos-2 grounding).
    Split: episode-level stratified 80/20, 5 seeds.
  </div>
</body>
</html>"""
    HTML_FILE.write_text(html)


def main():
    print(f"Device: {DEVICE}")
    dataset = json.loads(DATASET_FILE.read_text())
    print(f"Dataset: {len(dataset)} episodes, {sum(len(e['frames']) for e in dataset)} frames")

    results = {}
    for spec_name, spec in FEATURE_SPECS.items():
        print(f"\n{'='*60}")
        print(f"Condition: {spec_name}  (d_in={spec['d_in']})")
        print(f"{'='*60}")
        seed_accs = []
        per_path_all = defaultdict(list)

        for seed in SEEDS:
            print(f"\n  Seed {seed}:")
            train_ds, test_ds = make_episode_split(dataset, seed=seed)
            X_tr, y_tr, _ = build_windows(train_ds, spec)
            X_te, y_te, meta_te = build_windows(test_ds, spec)

            acc, preds = train_eval(X_tr, y_tr, X_te, y_te, d_in=spec["d_in"], seed=seed)
            seed_accs.append(acc)
            print(f"    → best PM: {acc:.3f}")

            pm = per_path_pm(meta_te, y_te, preds)
            for pt in PATH_TYPES:
                v = pm.get(pt, {"correct": 0, "total": 1})
                per_path_all[pt].append(v["correct"] / max(v["total"], 1))

        mean_pm = float(np.mean(seed_accs))
        std_pm = float(np.std(seed_accs))
        print(f"\n  {spec_name}: {mean_pm:.3f} ± {std_pm:.3f}")

        results[spec_name] = {
            "mean_pm": mean_pm,
            "std_pm": std_pm,
            "seed_pms": seed_accs,
            "pm_by_path_mean": {pt: float(np.mean(v)) for pt, v in per_path_all.items()},
        }

    SUMMARY_FILE.write_text(json.dumps(results, indent=2))
    build_html(results)

    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    for name, r in results.items():
        print(f"  {name:12s}: {r['mean_pm']:.1%} ± {r['std_pm']:.1%}")
    print(f"\nSummary: {SUMMARY_FILE}")
    print(f"HTML:    {HTML_FILE}")


if __name__ == "__main__":
    main()

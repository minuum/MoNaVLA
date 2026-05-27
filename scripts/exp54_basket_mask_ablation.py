#!/usr/bin/env python3
"""
Track 3: Basket Masking Ablation

basket 영역을 회색(128,128,128)으로 가리면 Stage 1 v2 예측이 바뀌는가?
인과적 증거 — basket이 사라지면 confidence 떨어지면 "basket을 보고 있었다"

방법:
  1. consistent=True 프레임, area_det > MIN_AREA 인 것만 (basket이 충분히 커야 마스킹 의미 있음)
  2. cx_det, cy_det, area_det로 basket 위치 특정 → 1.5배 영역 gray masking
  3. Stage 1 v2에 원본/마스킹 각각 입력
  4. confidence(정답 클래스 cosine similarity) 변화 측정

결과 해석:
  confidence 감소 30%↑ → basket 영역에 의존 ✅
  confidence 감소 10~30% → 부분 의존
  confidence 변화 없음  → basket 외 정보로 분류 ⚠️

Usage:
  .venv/bin/python3 scripts/exp54_basket_mask_ablation.py
"""

import json, sys, warnings
from pathlib import Path
from collections import defaultdict

import h5py
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, ImageDraw

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

VLM_PATH  = ROOT / ".vlms" / "kosmos-2-patch14-224"
DATA_PATH = ROOT / "docs" / "v5" / "bbox_frame_level" / "bbox_dataset_frame_level.json"
CKPT_PATH = ROOT / "runs" / "v5_nav" / "mlp" / "exp54" / "stage1_v2" / "stage1_v2_projs.pt"

PROJ_DIM  = 256
LM_DIM    = 2048
VIS_DIM   = 1024
DIR_IDX   = {"left": 0, "center": 1, "right": 2}
DIRS      = ["left", "center", "right"]

MIN_AREA  = 0.005   # 마스킹 의미 있으려면 최소 이 면적 이상
MASK_SCALE = 1.5    # bbox 크기의 1.5배로 마스킹 (약간 넉넉하게)
MASK_COLOR = (128, 128, 128)
N_SAMPLE   = 15     # 방향별 샘플 수


def load_model(device):
    from transformers import AutoModelForVision2Seq, AutoProcessor
    ckpt = torch.load(str(CKPT_PATH), map_location=device, weights_only=False)
    print(f"[MODEL] Stage1 v2 val_acc={ckpt['val_acc']:.4f}")

    processor = AutoProcessor.from_pretrained(str(VLM_PATH))
    base = AutoModelForVision2Seq.from_pretrained(
        str(VLM_PATH), torch_dtype=torch.float16
    )
    vm = base.vision_model.to(device).eval()

    image_proj = nn.Linear(VIS_DIM, PROJ_DIM).to(device)
    image_proj.load_state_dict(ckpt["image_proj"])
    image_proj.eval()

    text_proj = nn.Linear(LM_DIM, PROJ_DIM).to(device)
    text_proj.load_state_dict(ckpt["text_proj"])
    text_proj.eval()

    anchor_feats = F.normalize(text_proj(ckpt["anchor_raw"].to(device)), dim=-1)
    return processor, vm, image_proj, anchor_feats


@torch.no_grad()
def get_conf(vm, image_proj, processor, anchor_feats, img, device, gt_idx):
    """gt 클래스에 대한 cosine similarity 반환"""
    inputs = processor(images=[img], return_tensors="pt")
    pv = inputs["pixel_values"].to(device, dtype=torch.float16)
    out = vm(pixel_values=pv)
    feat = out.last_hidden_state.mean(dim=1).float()
    proj = F.normalize(image_proj(feat), dim=-1)
    sims = (proj @ anchor_feats.T)[0]  # (3,)
    pred_idx = sims.argmax().item()
    return sims[gt_idx].item(), pred_idx


def mask_basket(img_pil, cx, cy, area, scale=MASK_SCALE):
    """cx/cy/area 기반 영역을 gray로 마스킹"""
    W, H = img_pil.size
    side = int(np.sqrt(area) * min(W, H) * scale)
    half = side // 2
    bx = int(cx * W)
    by = int(cy * H)
    x1, y1 = max(0, bx - half), max(0, by - half)
    x2, y2 = min(W, bx + half), min(H, by + half)

    masked = img_pil.copy()
    draw = ImageDraw.Draw(masked)
    draw.rectangle([x1, y1, x2, y2], fill=MASK_COLOR)
    return masked, (x1, y1, x2, y2)


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[DEVICE] {device}")
    processor, vm, image_proj, anchor_feats = load_model(device)

    data = json.loads(DATA_PATH.read_text())

    # 방향별로 area_det 충분한 프레임 수집
    dir_samples = defaultdict(list)
    for ep in data:
        d = ep["direction"]
        if len(dir_samples[d]) >= N_SAMPLE:
            continue
        frames = [
            f for f in ep["frames"]
            if f["consistent"] and f["label"]
            and f.get("area_det") and f["area_det"] >= MIN_AREA
        ]
        for fr in frames:
            if len(dir_samples[d]) < N_SAMPLE:
                dir_samples[d].append((ep["episode"], fr))

    results = []
    dir_stats = defaultdict(lambda: {"conf_drop": [], "flip": 0, "total": 0})

    print(f"\n[MASK] basket 마스킹 ablation 시작 (MIN_AREA={MIN_AREA}, scale={MASK_SCALE}×)\n")
    print(f"  {'방향':<8} {'cx':>5} {'area':>6} {'conf_orig':>10} {'conf_mask':>10} {'drop':>8} {'pred변화':>8}")
    print("  " + "-" * 65)

    for direction in DIRS:
        samples = dir_samples[direction]
        if not samples:
            print(f"  [{direction}] 유효 샘플 없음 (area_det >= {MIN_AREA} 없음)")
            continue

        for ep_path, fr in samples:
            gt_idx = DIR_IDX[fr["label"]]
            cx     = fr["cx_det"]
            cy     = fr["cy_det"]
            area   = fr["area_det"]

            try:
                with h5py.File(ep_path, "r") as f:
                    img = Image.fromarray(f["observations"]["images"][fr["frame_idx"]]).convert("RGB")
            except:
                continue

            masked_img, bbox_px = mask_basket(img, cx, cy, area)

            conf_orig, pred_orig = get_conf(vm, image_proj, processor, anchor_feats, img,        device, gt_idx)
            conf_mask, pred_mask = get_conf(vm, image_proj, processor, anchor_feats, masked_img, device, gt_idx)

            drop = conf_orig - conf_mask
            flipped = (pred_orig != pred_mask)

            row = {
                "direction": direction,
                "cx": round(cx, 3), "area": round(area, 4),
                "conf_orig": round(conf_orig, 4),
                "conf_mask": round(conf_mask, 4),
                "conf_drop": round(drop, 4),
                "pred_orig": DIRS[pred_orig],
                "pred_mask": DIRS[pred_mask],
                "flipped":   flipped,
            }
            results.append(row)
            dir_stats[direction]["conf_drop"].append(drop)
            dir_stats[direction]["total"] += 1
            if flipped:
                dir_stats[direction]["flip"] += 1

            flip_str = f"{'→'+DIRS[pred_mask]:>8}" if flipped else "      —"
            print(
                f"  {direction:<8} {cx:>5.2f} {area:>6.4f} "
                f"{conf_orig:>10.4f} {conf_mask:>10.4f} "
                f"{drop:>+8.4f} {flip_str}"
            )

        print()

    # 요약
    print(f"\n{'='*65}")
    print(f"  Track 3: Basket Masking Ablation 요약")
    print(f"{'='*65}")
    print(f"\n  {'방향':<8} {'n':>4} {'conf_drop 평균':>14} {'flip 비율':>12}  {'판정':>20}")
    print("  " + "-" * 62)

    all_drops = []
    for d in DIRS:
        s = dir_stats[d]
        if not s["conf_drop"]:
            print(f"  {d:<8}   -          N/A             N/A")
            continue
        drops = s["conf_drop"]
        mean_drop = np.mean(drops)
        flip_rate = s["flip"] / s["total"] * 100
        all_drops.extend(drops)

        if mean_drop >= 0.10:
            v = "basket 의존 ✅"
        elif mean_drop >= 0.03:
            v = "부분 의존"
        else:
            v = "독립적 ⚠️"
        print(f"  {d:<8} {s['total']:>4} {mean_drop:>+14.4f} {flip_rate:>11.1f}%  {v}")

    if all_drops:
        overall_mean = np.mean(all_drops)
        overall_flip = sum(s["flip"] for s in dir_stats.values())
        overall_total = sum(s["total"] for s in dir_stats.values())
        flip_pct = overall_flip / overall_total * 100 if overall_total > 0 else 0

        print(f"\n  전체 평균 conf drop:  {overall_mean:+.4f}")
        print(f"  예측 반전 비율:       {overall_flip}/{overall_total} ({flip_pct:.1f}%)")

        if overall_mean >= 0.10:
            verdict = "basket 영역에 유의미하게 의존 ✅"
        elif overall_mean >= 0.03:
            verdict = "약한 의존 (보조 신호로 사용)"
        else:
            verdict = "basket 외 정보만으로 분류 ⚠️"
        print(f"  → 판정: {verdict}")

    print(f"{'='*65}")


if __name__ == "__main__":
    main()

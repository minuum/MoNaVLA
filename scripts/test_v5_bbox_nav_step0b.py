#!/usr/bin/env python3
"""
Exp14 Step 0-B: BBox-based Navigation using Exp10 checkpoint

Step 0 (pure HF Kosmos-2)의 PM 31% 개선 시도.
Exp10 trained ckpt (IoU 0.87, val_loss 0.012)로 basket BBox 추출 → rule-based action.

Usage:
  python3 scripts/test_v5_bbox_nav_step0b.py
"""

import os
import sys
import json
import re
from pathlib import Path
from collections import defaultdict

os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["USE_FLASH_ATTENTION"] = "0"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(1, str(ROOT))
sys.path.insert(0, str(ROOT / "third_party" / "RoboVLMs"))

import torch
import numpy as np
import h5py
from PIL import Image, ImageDraw
from transformers import AutoProcessor

from robovlms.model.backbone.base_backbone import load_config
from robovlms.train.mobile_vla_trainer import MobileVLATrainer

CONFIG_PATH = ROOT / "configs" / "mobile_vla_v5_exp10_bbox.json"
CKPT_PATH = ROOT / "runs" / "v5_nav" / "kosmos" / "mobile_vla_v5_bbox" / "2026-04-15" / "v5-exp10-track2-bbox" / "epoch_epoch=epoch=07-val_loss=val_loss=0.012.ckpt"
KOSMOS_PATH = ROOT / ".vlms" / "kosmos-2-patch14-224"
DATA_DIR = ROOT / "ROS_action" / "mobile_vla_dataset_v5"
OUT_DIR = ROOT / "docs" / "v5" / "bbox_nav_step0b"
OUT_DIR.mkdir(parents=True, exist_ok=True)
IMG_DIR = OUT_DIR / "images"
IMG_DIR.mkdir(exist_ok=True)

PATH_TYPES = [
    "center_straight", "center_left", "center_right",
    "left_straight",   "left_left",   "left_right",
    "right_straight",  "right_left",  "right_right",
]

CLASS_NAMES = ["STOP", "FORWARD", "LEFT", "RIGHT", "FWD+L", "FWD+R", "ROT_L", "ROT_R"]
EPS_PER_PATH = 2
FRAMES_PER_EP = 5


def gt_action_class(lx, ly, az):
    is_x = abs(lx) > 0.3
    is_y = abs(ly) > 0.3
    if not is_x and not is_y:
        if az > 0.1:
            return 6
        if az < -0.1:
            return 7
        return 0
    if lx > 0.3:
        if ly > 0.3:
            return 4
        if ly < -0.3:
            return 5
        return 1
    if abs(lx) < 0.3:
        if ly > 0.3:
            return 2
        if ly < -0.3:
            return 3
    return 0


def bbox_to_action(cx, area):
    if area is None or cx is None:
        return 1
    if area > 0.35:
        return 0
    if cx < 0.30:
        return 2 if cx < 0.15 else 4
    if cx > 0.70:
        return 3 if cx > 0.85 else 5
    return 1


def patch_to_norm(p):
    """patch_index 0..1023 → (cx, cy) normalized 0..1"""
    row = p // 32
    col = p % 32
    return (col + 0.5) / 32.0, (row + 0.5) / 32.0


def parse_bbox_from_text(text):
    """
    Exp10 출력에서 BBox 추출. 실제 출력은 `<pad>` 사이에 patch_index 한두 개만 있음:
        <pad><pad><pad><patch_index_0320><pad><pad></s>

    Returns: (p1, p2) tuple. p1=p2 if only single patch found.
    """
    # 모든 patch_index 추출
    patches = [int(m) for m in re.findall(r"<patch_index_(\d+)>", text)]
    if not patches:
        return None, None
    if len(patches) >= 2:
        return patches[0], patches[1]
    return patches[0], patches[0]  # single patch → same corners


def pick_episodes(path_type, k):
    cands = sorted(DATA_DIR.glob(f"episode_*target_{path_type}_path*.h5"))
    return cands[:k]


def sample_frame_indices(total, n):
    if total <= n:
        return list(range(total))
    return [int(i * (total - 1) / (n - 1)) for i in range(n)]


def draw_bbox(pil_img, bbox, pred_name, gt_name):
    img = pil_img.copy()
    draw = ImageDraw.Draw(img)
    W, H = img.size
    if bbox is not None:
        x1, y1, x2, y2 = bbox["x1"] * W, bbox["y1"] * H, bbox["x2"] * W, bbox["y2"] * H
        color = (34, 197, 94) if pred_name == gt_name else (239, 68, 68)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=4)
    mark = "OK" if pred_name == gt_name else "X"
    draw.rectangle([0, 0, W, 28], fill=(15, 23, 42))
    draw.text((8, 6), f"{mark} pred={pred_name}  gt={gt_name}", fill=(255, 255, 255))
    return img


def main():
    print("Loading config + trainer...")
    configs = load_config(str(CONFIG_PATH))
    trainer = MobileVLATrainer(configs)

    print(f"Loading ckpt {CKPT_PATH.name}")
    ckpt = torch.load(str(CKPT_PATH), map_location="cpu", weights_only=False)
    state_dict = ckpt.get("state_dict", ckpt)
    if any(k.startswith("model.") for k in state_dict.keys()):
        state_dict = {k[6:] if k.startswith("model.") else k: v for k, v in state_dict.items()}
    missing, unexpected = trainer.model.load_state_dict(state_dict, strict=False)
    print(f"  missing={len(missing)}, unexpected={len(unexpected)}")

    model = trainer.model.to("cuda:0").eval()
    processor = AutoProcessor.from_pretrained(str(KOSMOS_PATH))
    print("Loaded.")

    all_results = []
    pm_by_path = defaultdict(lambda: {"correct": 0, "total": 0})

    for pt in PATH_TYPES:
        eps = pick_episodes(pt, EPS_PER_PATH)
        print(f"\n=== {pt}: {len(eps)} episodes ===")
        for ep in eps:
            with h5py.File(ep, "r") as f:
                if "observations" in f and "images" in f["observations"]:
                    imgs = f["observations"]["images"][:]
                else:
                    imgs = f["images"][:]
                actions = f["actions"][:]
                instr = f["language_instruction"][0]
                if isinstance(instr, bytes):
                    instr = instr.decode("utf-8", errors="ignore")

            idxs = sample_frame_indices(len(imgs), FRAMES_PER_EP)
            for fi in idxs:
                gt_cls = gt_action_class(*actions[fi])
                frame = imgs[fi].astype(np.uint8)
                pil = Image.fromarray(frame).convert("RGB")

                prompt = f"Instruction: {instr} Action: "
                inputs = processor(text=prompt, images=pil, return_tensors="pt").to("cuda:0")
                with torch.no_grad():
                    out = model.model.generate(
                        pixel_values=inputs["pixel_values"],
                        input_ids=inputs["input_ids"],
                        attention_mask=inputs["attention_mask"],
                        image_embeds_position_mask=inputs.get("image_embeds_position_mask"),
                        max_new_tokens=32,
                        use_cache=True,
                    )
                pred_text = processor.tokenizer.decode(out[0], skip_special_tokens=False)
                # strip input prompt from decoded output
                if pred_text.startswith(prompt):
                    pred_after = pred_text[len(prompt):]
                else:
                    pred_after = pred_text
                p1, p2 = parse_bbox_from_text(pred_after)

                if p1 is not None:
                    x1, y1 = patch_to_norm(p1)
                    x2, y2 = patch_to_norm(p2)
                    if x2 < x1:
                        x1, x2 = x2, x1
                    if y2 < y1:
                        y1, y2 = y2, y1
                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2
                    # single-patch case: use small fixed box area
                    area = max((x2 - x1) * (y2 - y1), 1.0 / 32 / 32)
                    bbox = {
                        "x1": max(x1 - 0.02, 0.0), "y1": max(y1 - 0.02, 0.0),
                        "x2": min(x2 + 0.02, 1.0), "y2": min(y2 + 0.02, 1.0),
                        "cx": cx, "cy": cy, "area": area,
                        "patch_p1": p1, "patch_p2": p2,
                    }
                    pred_cls = bbox_to_action(cx, area)
                else:
                    bbox = None
                    pred_cls = 1

                pred_name = CLASS_NAMES[pred_cls]
                gt_name = CLASS_NAMES[gt_cls]
                pm_by_path[pt]["total"] += 1
                if pred_cls == gt_cls:
                    pm_by_path[pt]["correct"] += 1

                img_name = f"{pt}__{ep.stem.split('_')[1]}__f{fi:03d}.jpg"
                overlay = draw_bbox(pil.resize((640, 360)), bbox, pred_name, gt_name)
                overlay.save(IMG_DIR / img_name, quality=82)

                all_results.append({
                    "path_type": pt, "episode": ep.stem, "frame_idx": fi,
                    "gt_class": gt_cls, "gt_name": gt_name,
                    "pred_class": pred_cls, "pred_name": pred_name,
                    "bbox": bbox,
                    "raw_pred": pred_after[:200],
                    "image": f"images/{img_name}",
                })

    total_correct = sum(v["correct"] for v in pm_by_path.values())
    total_all = sum(v["total"] for v in pm_by_path.values())
    overall_pm = total_correct / max(total_all, 1)
    summary = {
        "overall_pm": overall_pm,
        "total": total_all,
        "correct": total_correct,
        "pm_by_path": dict(pm_by_path),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    (OUT_DIR / "results.json").write_text(json.dumps(all_results, indent=2, ensure_ascii=False))

    build_html(all_results, summary)
    print(f"\n=== Summary ===")
    print(f"Overall PM: {overall_pm:.2%} ({total_correct}/{total_all})")
    for k, v in pm_by_path.items():
        print(f"  {k:20s}: {v['correct']}/{v['total']} = {v['correct']/max(v['total'],1):.1%}")
    print(f"\nHTML: {OUT_DIR / 'index.html'}")


def build_html(results, summary):
    by_path = defaultdict(list)
    for r in results:
        by_path[r["path_type"]].append(r)

    pm_rows = []
    for pt in PATH_TYPES:
        v = summary["pm_by_path"].get(pt, {"correct": 0, "total": 0})
        pm = v["correct"] / max(v["total"], 1)
        pm_rows.append(
            f"<tr><td>{pt}</td><td>{v['correct']}/{v['total']}</td>"
            f"<td><strong>{pm:.1%}</strong></td></tr>"
        )

    sections = []
    for pt in PATH_TYPES:
        rows = by_path.get(pt, [])
        if not rows:
            continue
        correct = sum(1 for r in rows if r["pred_class"] == r["gt_class"])
        total = len(rows)
        cells = []
        for r in rows:
            ok = "ok" if r["pred_class"] == r["gt_class"] else "bad"
            bbox_info = ""
            if r.get("bbox"):
                b = r["bbox"]
                bbox_info = f"cx={b['cx']:.2f} area={b['area']:.2f}"
            cells.append(f"""
              <div class="sample {ok}">
                <img src="{r['image']}" alt="">
                <div class="meta">
                  <div><strong>{r['pred_name']}</strong> vs GT <strong>{r['gt_name']}</strong></div>
                  <div class="cap">{bbox_info}</div>
                  <div class="src">{r['raw_pred'][:100]}</div>
                </div>
              </div>""")
        sections.append(f"""
          <div class="path-section">
            <h2>{pt} <span class="pm">{correct}/{total} = {correct/total:.1%}</span></h2>
            <div class="grid">{''.join(cells)}</div>
          </div>""")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Exp14 Step 0-B: BBox Nav (Exp10 ckpt)</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 24px; background: #0f172a; color: #e2e8f0; }}
  h1 {{ font-size: 2rem; margin-bottom: 8px; }}
  .sub {{ color: #94a3b8; margin-bottom: 24px; max-width: 800px; line-height: 1.6; }}
  .back {{ display: inline-block; margin-bottom: 16px; color: #60a5fa; text-decoration: none; }}
  .overall {{ display: inline-block; padding: 12px 24px; background: #1e293b; border-radius: 8px; margin-bottom: 20px; font-size: 1.3rem; }}
  .overall strong {{ color: #22c55e; }}
  table {{ border-collapse: collapse; margin-bottom: 28px; background: #1e293b; border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 8px 16px; text-align: left; border-bottom: 1px solid #334155; }}
  th {{ background: #0b1220; }}
  .path-section {{ margin-bottom: 36px; }}
  .path-section h2 {{ font-size: 1.3rem; padding: 8px 12px; background: #1e293b; border-radius: 6px; }}
  .path-section h2 .pm {{ color: #facc15; font-size: 0.9rem; margin-left: 8px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; margin-top: 10px; }}
  .sample {{ background: #1e293b; border-radius: 8px; overflow: hidden; border: 2px solid transparent; }}
  .sample.ok {{ border-color: #22c55e; }}
  .sample.bad {{ border-color: #ef4444; }}
  .sample img {{ width: 100%; display: block; }}
  .meta {{ padding: 8px 10px; font-size: 0.85rem; }}
  .cap {{ color: #facc15; margin-top: 4px; font-size: 0.75rem; font-family: monospace; }}
  .src {{ color: #64748b; margin-top: 2px; font-size: 0.7rem; font-family: monospace; }}
</style>
</head>
<body>
  <a class="back" href="../../index.html">← Back to main</a>
  <h1>Exp14 Step 0-B: BBox Nav (Exp10 ckpt)</h1>
  <p class="sub">
    Exp10 학습된 체크포인트(IoU 0.87)로 basket BBox 추출 → rule-based action.
    Step 0 (pure Kosmos-2, PM 31%) 대비 grounding 품질 개선으로 얼마나 올라가는가?
  </p>
  <div class="overall">Overall PM: <strong>{summary['overall_pm']:.1%}</strong> ({summary['correct']}/{summary['total']})</div>
  <h2>PM per Path Type</h2>
  <table><tr><th>Path Type</th><th>Correct/Total</th><th>PM</th></tr>{''.join(pm_rows)}</table>
  {''.join(sections)}
</body>
</html>"""
    (OUT_DIR / "index.html").write_text(html)


if __name__ == "__main__":
    main()

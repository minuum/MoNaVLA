#!/usr/bin/env python3
"""
Exp14 Step 0: BBox-based Navigation (rule-based, no training)

Pure HF Kosmos-2 grounding으로 각 프레임의 basket 위치를 추정하고,
rule-based mapping (basket_x → action)으로 action 예측.
GT action과 비교해 PM 측정.

목적: 학습 없이 foundation의 공간 인식만으로 얼마나 navigation 가능한지 확인.

Usage:
  python3 scripts/test_v5_bbox_nav_step0.py
"""

import sys
import json
import re
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch
import numpy as np
import h5py
from PIL import Image, ImageDraw, ImageFont
from transformers import AutoProcessor, AutoModelForVision2Seq

HF_KOSMOS_PATH = ROOT / ".vlms" / "kosmos-2-patch14-224"
DATA_DIR = ROOT / "ROS_action" / "mobile_vla_dataset_v5"
OUT_DIR = ROOT / "docs" / "v5" / "bbox_nav_step0"
OUT_DIR.mkdir(parents=True, exist_ok=True)
IMG_DIR = OUT_DIR / "images"
IMG_DIR.mkdir(exist_ok=True)

PATH_TYPES = [
    "center_straight", "center_left", "center_right",
    "left_straight",   "left_left",   "left_right",
    "right_straight",  "right_left",  "right_right",
]

CLASS_NAMES = ["STOP", "FORWARD", "LEFT", "RIGHT", "FWD+L", "FWD+R", "ROT_L", "ROT_R"]
GROUNDING_PROMPT = "<grounding>The gray basket is at"
EPS_PER_PATH = 2      # 각 path_type당 에피소드 수
FRAMES_PER_EP = 5     # 각 에피소드에서 샘플링할 프레임 수


def gt_action_class(lx, ly, az):
    """V5 8-class discrete mapping (from nav_h5_dataset_impl.py)"""
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
    """
    Rule-based: basket 위치 → 8-class action

    cx: 0~1 normalized x-center
    area: 0~1 normalized bbox area
    """
    if area is None or cx is None:
        return 1  # default: FORWARD
    if area > 0.35:
        return 0  # STOP (close)
    if cx < 0.30:
        return 2 if cx < 0.15 else 4  # LEFT vs FWD+L
    if cx > 0.70:
        return 3 if cx > 0.85 else 5  # RIGHT vs FWD+R
    return 1  # FORWARD


def pick_episodes(path_type: str, k: int):
    cands = sorted(DATA_DIR.glob(f"episode_*target_{path_type}_path*.h5"))
    return cands[:k]


def sample_frame_indices(total: int, n: int):
    if total <= n:
        return list(range(total))
    return [int(i * (total - 1) / (n - 1)) for i in range(n)]


def parse_basket_bbox(caption: str, entities):
    """
    Kosmos-2 grounding 결과에서 basket 추정 BBox 추출.

    우선순위:
      1. entity 이름에 "basket"/"box"/"container"/"gray" 포함 → 그 박스
      2. caption에 "far left/right/center" 키워드 → 텍스트 기반 추정
      3. 비 fullscreen entity 중 첫 번째 (fallback)
    """
    kw = ("basket", "gray box", "container", "gray")
    basket_candidates = []
    for ent_name, span, boxes in entities:
        for box in boxes:
            x1, y1, x2, y2 = box
            area = (x2 - x1) * (y2 - y1)
            if area > 0.85:  # fullscreen drop
                continue
            is_basket = any(k in ent_name.lower() for k in kw)
            basket_candidates.append({
                "entity": ent_name, "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "area": area, "cx": (x1 + x2) / 2, "cy": (y1 + y2) / 2,
                "is_basket": is_basket,
            })

    # 1. basket 키워드 매칭 우선
    matched = [b for b in basket_candidates if b["is_basket"]]
    if matched:
        return matched[0], "entity_match"

    # 2. caption keyword 기반 추정
    cap_low = caption.lower()
    if "far left" in cap_low:
        return {"cx": 0.1, "cy": 0.5, "area": 0.1, "entity": "caption:far_left",
                "x1": 0.0, "y1": 0.4, "x2": 0.2, "y2": 0.6, "is_basket": False}, "caption"
    if "far right" in cap_low:
        return {"cx": 0.9, "cy": 0.5, "area": 0.1, "entity": "caption:far_right",
                "x1": 0.8, "y1": 0.4, "x2": 1.0, "y2": 0.6, "is_basket": False}, "caption"
    if "left" in cap_low and "right" not in cap_low:
        return {"cx": 0.25, "cy": 0.5, "area": 0.1, "entity": "caption:left",
                "x1": 0.15, "y1": 0.4, "x2": 0.35, "y2": 0.6, "is_basket": False}, "caption"
    if "right" in cap_low and "left" not in cap_low:
        return {"cx": 0.75, "cy": 0.5, "area": 0.1, "entity": "caption:right",
                "x1": 0.65, "y1": 0.4, "x2": 0.85, "y2": 0.6, "is_basket": False}, "caption"
    if "center" in cap_low:
        return {"cx": 0.5, "cy": 0.5, "area": 0.1, "entity": "caption:center",
                "x1": 0.4, "y1": 0.4, "x2": 0.6, "y2": 0.6, "is_basket": False}, "caption"

    # 3. fallback: first non-fullscreen entity
    if basket_candidates:
        return basket_candidates[0], "fallback"

    return None, "none"


def run_grounding(model, processor, pil_img):
    inputs = processor(text=GROUNDING_PROMPT, images=pil_img, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    pv = inputs["pixel_values"].to(torch.float16)

    with torch.no_grad():
        gen_ids = model.generate(
            pixel_values=pv,
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            image_embeds=None,
            image_embeds_position_mask=inputs.get("image_embeds_position_mask"),
            max_new_tokens=80,
        )
    new_ids = gen_ids[:, inputs["input_ids"].shape[1]:]
    raw = processor.batch_decode(new_ids, skip_special_tokens=False)[0]
    caption, entities = processor.post_process_generation(raw)
    return caption, entities


def draw_bbox(pil_img, bbox, pred_name, gt_name):
    img = pil_img.copy()
    draw = ImageDraw.Draw(img)
    W, H = img.size
    if bbox is not None:
        x1, y1, x2, y2 = bbox["x1"] * W, bbox["y1"] * H, bbox["x2"] * W, bbox["y2"] * H
        color = (34, 197, 94) if pred_name == gt_name else (239, 68, 68)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=4)
        tag = f"{bbox.get('entity','?')[:24]}"
        draw.text((x1 + 4, max(y1 - 18, 4)), tag, fill=color)
    mark_ok = "OK" if pred_name == gt_name else "X"
    header = f"{mark_ok} pred={pred_name}  gt={gt_name}"
    draw.rectangle([0, 0, W, 28], fill=(15, 23, 42))
    draw.text((8, 6), header, fill=(255, 255, 255))
    return img


def main():
    print(f"Loading Pure HF Kosmos-2 from {HF_KOSMOS_PATH}")
    processor = AutoProcessor.from_pretrained(str(HF_KOSMOS_PATH))
    model = AutoModelForVision2Seq.from_pretrained(
        str(HF_KOSMOS_PATH), torch_dtype=torch.float16,
    ).cuda().eval()
    print("Loaded.")

    all_results = []
    pm_by_path = defaultdict(lambda: {"correct": 0, "total": 0})
    confusion = defaultdict(int)

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
            idxs = sample_frame_indices(len(imgs), FRAMES_PER_EP)
            for fi in idxs:
                gt_cls = gt_action_class(*actions[fi])
                frame = imgs[fi].astype(np.uint8)
                pil = Image.fromarray(frame).convert("RGB")
                caption, entities = run_grounding(model, processor, pil)
                bbox, source = parse_basket_bbox(caption, entities)
                if bbox:
                    pred_cls = bbox_to_action(bbox["cx"], bbox["area"])
                else:
                    pred_cls = 1

                pred_name = CLASS_NAMES[pred_cls]
                gt_name = CLASS_NAMES[gt_cls]
                pm_by_path[pt]["total"] += 1
                if pred_cls == gt_cls:
                    pm_by_path[pt]["correct"] += 1
                confusion[(gt_name, pred_name)] += 1

                img_name = f"{pt}__{ep.stem.split('_')[1]}__f{fi:03d}.jpg"
                img_path = IMG_DIR / img_name
                overlay = draw_bbox(pil.resize((640, 360)), bbox, pred_name, gt_name)
                overlay.save(img_path, quality=82)

                all_results.append({
                    "path_type": pt,
                    "episode": ep.stem,
                    "frame_idx": fi,
                    "gt_class": gt_cls,
                    "gt_name": gt_name,
                    "pred_class": pred_cls,
                    "pred_name": pred_name,
                    "bbox": bbox,
                    "bbox_source": source,
                    "caption": caption,
                    "image": f"images/{img_name}",
                })

    # Summary
    total_correct = sum(v["correct"] for v in pm_by_path.values())
    total_all = sum(v["total"] for v in pm_by_path.values())
    overall_pm = total_correct / max(total_all, 1)

    summary = {
        "overall_pm": overall_pm,
        "total": total_all,
        "correct": total_correct,
        "pm_by_path": {k: v for k, v in pm_by_path.items()},
        "confusion": {f"{g}->{p}": c for (g, p), c in confusion.items()},
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
            cells.append(f"""
              <div class="sample {ok}">
                <img src="{r['image']}" alt="">
                <div class="meta">
                  <div><strong>{r['pred_name']}</strong> vs GT <strong>{r['gt_name']}</strong></div>
                  <div class="cap">{r['caption'][:120]}</div>
                  <div class="src">source: {r['bbox_source']}</div>
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
<title>Exp14 Step 0: BBox-based Navigation</title>
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
  .cap {{ color: #94a3b8; margin-top: 4px; font-size: 0.75rem; }}
  .src {{ color: #64748b; margin-top: 2px; font-size: 0.7rem; }}
</style>
</head>
<body>
  <a class="back" href="../../index.html">← Back to main</a>
  <h1>Exp14 Step 0: BBox-based Navigation</h1>
  <p class="sub">
    Pure HF Kosmos-2 grounding으로 basket 위치 추정 → rule-based로 action 예측.
    학습 없이 foundation의 공간 인식만으로 얼마나 navigation 가능한가?
  </p>
  <div class="overall">Overall PM: <strong>{summary['overall_pm']:.1%}</strong> ({summary['correct']}/{summary['total']})</div>

  <h2>PM per Path Type</h2>
  <table>
    <tr><th>Path Type</th><th>Correct/Total</th><th>PM</th></tr>
    {''.join(pm_rows)}
  </table>

  {''.join(sections)}
</body>
</html>"""
    (OUT_DIR / "index.html").write_text(html)


if __name__ == "__main__":
    main()

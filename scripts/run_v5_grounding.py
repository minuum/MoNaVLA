#!/usr/bin/env python3
"""
V5 데이터셋 전 프레임에 Kosmos-2 Grounding 실행 → v5_grounding.json 저장

순수 HF Kosmos-2 사용 + 최적 프롬프트 형식으로 gray basket 탐지.

프롬프트 연구 결과:
  - "<grounding>The gray basket is at" → "the gray box" 엔티티 + 정확한 bbox 반환 (최선)
  - "<grounding><phrase>gray basket</phrase>" → 이상한 엔티티명이지만 동일 bbox 반환
  - "<grounding>An image of a robot. Where is..." → 전화면 "The room" 환각 (최악)

Usage:
  python3 scripts/run_v5_grounding.py
  python3 scripts/run_v5_grounding.py --max_episodes 5

Output:
  ROS_action/v5_data_bak/v5_grounding.json
"""

import argparse
import json
import os
import time
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForVision2Seq

# ── 경로 ─────────────────────────────────────────────────────────
BASE_DIR    = Path("/home/billy/25-1kp/MoNaVLA/ROS_action/v5_data_bak")
IMG_DIR     = BASE_DIR / "mobile_vla_dataset_v5(Image)"
OUTPUT_JSON = BASE_DIR / "v5_grounding.json"

MODEL_PATH  = Path("/home/billy/.cache/huggingface/hub/models--microsoft--kosmos-2-patch14-224/snapshots/e91cfbcb4ce051b6a55bfb5f96165a3bbf5eb82c")
DEVICE      = "cuda" if torch.cuda.is_available() else "cpu"

# 최적 프롬프트 (연구 결과: 이 형식이 non-hallucination bbox 생성)
DEFAULT_PROMPT = "<grounding>The gray basket is at"

# 전화면 bbox 필터링 기준 (area > 90%)
FULLSCREEN_AREA_THRESHOLD = 0.90


def load_model():
    print(f"Kosmos-2 로딩: {MODEL_PATH}")
    processor = AutoProcessor.from_pretrained(str(MODEL_PATH))
    model = AutoModelForVision2Seq.from_pretrained(
        str(MODEL_PATH),
        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
    ).to(DEVICE).eval()
    print(f"  ✅ 로드 완료 ({DEVICE})")
    return processor, model


def run_grounding(processor, model, image: Image.Image, prompt: str) -> dict:
    """단일 이미지에 대해 grounding 실행. bbox는 0~1 normalized."""
    inputs = processor(text=prompt, images=image, return_tensors="pt")
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
    pv = inputs["pixel_values"].to(torch.float16 if DEVICE == "cuda" else torch.float32)

    with torch.no_grad():
        generated_ids = model.generate(
            pixel_values=pv,
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            image_embeds=None,
            image_embeds_position_mask=inputs.get("image_embeds_position_mask"),
            use_cache=True,
            max_new_tokens=128,
        )

    new_ids = generated_ids[:, inputs["input_ids"].shape[1]:]
    raw_text = processor.batch_decode(new_ids, skip_special_tokens=True)[0]
    processed_text, entities = processor.post_process_generation(raw_text)

    bboxes = []
    for entity_name, _span, boxes in entities:
        for box in boxes:
            x1, y1, x2, y2 = box
            if max(x1, y1, x2, y2) > 1.5:
                x1, y1, x2, y2 = x1 / 1000, y1 / 1000, x2 / 1000, y2 / 1000

            area = (x2 - x1) * (y2 - y1)
            bboxes.append({
                "entity": entity_name,
                "x1": round(float(x1), 4),
                "y1": round(float(y1), 4),
                "x2": round(float(x2), 4),
                "y2": round(float(y2), 4),
                "area": round(float(area), 4),
                "is_fullscreen": area > FULLSCREEN_AREA_THRESHOLD,
            })

    # 전화면 BBox 필터링 후 유효 BBox만 선별
    valid_bboxes = [b for b in bboxes if not b["is_fullscreen"]]

    return {
        "caption": processed_text,
        "bboxes": bboxes,
        "valid_bboxes": valid_bboxes,  # 전화면 제외
        "raw": raw_text,
    }


def main(args):
    processor, model = load_model()

    episodes = sorted([d for d in os.listdir(IMG_DIR) if (IMG_DIR / d).is_dir()])
    if args.max_episodes:
        episodes = episodes[:args.max_episodes]

    results = {}
    total_frames = 0
    valid_detections = 0
    t_start = time.time()

    for ep_idx, ep_name in enumerate(episodes):
        ep_dir = IMG_DIR / ep_name
        frames = sorted([f for f in os.listdir(ep_dir) if f.endswith(".png")])

        ep_results = {}
        for frame_file in frames:
            # frame_0000.png → 0
            frame_idx = int(frame_file.replace("frame_", "").replace(".png", ""))
            img_path = ep_dir / frame_file

            try:
                image = Image.open(img_path).convert("RGB")
                result = run_grounding(processor, model, image, args.prompt)
                ep_results[frame_idx] = result
                total_frames += 1

                has_valid = len(result["valid_bboxes"]) > 0
                if has_valid:
                    valid_detections += 1

                if has_valid:
                    b = result["valid_bboxes"][0]
                    bbox_summary = f"[{b['entity'][:20]}: ({b['x1']:.2f},{b['y1']:.2f})→({b['x2']:.2f},{b['y2']:.2f}) area={b['area']:.3f}]"
                else:
                    fullscreen_count = sum(1 for b in result["bboxes"] if b["is_fullscreen"])
                    bbox_summary = f"[NO VALID BBOX{' (fullscreen×'+str(fullscreen_count)+')' if fullscreen_count else ''}]"

                print(f"  [{ep_idx+1}/{len(episodes)}] {ep_name[:30]}... f{frame_idx:02d} {bbox_summary}")

            except Exception as e:
                print(f"  ❌ {ep_name} frame {frame_idx}: {e}")
                ep_results[frame_idx] = {"caption": f"ERROR: {e}", "bboxes": [], "valid_bboxes": [], "raw": ""}

        results[ep_name] = ep_results

        if (ep_idx + 1) % 10 == 0:
            OUTPUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2))
            elapsed = time.time() - t_start
            fps = total_frames / max(elapsed, 0.001)
            rate = valid_detections / max(total_frames, 1) * 100
            print(f"\n  💾 중간 저장 ({total_frames}프레임, {fps:.1f} fps, 유효탐지율 {rate:.1f}%)\n")

    OUTPUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    elapsed = time.time() - t_start
    rate = valid_detections / max(total_frames, 1) * 100
    print(f"\n✅ 완료: {total_frames}프레임 / {len(episodes)}에피소드 ({elapsed:.1f}초)")
    print(f"   유효 탐지율: {valid_detections}/{total_frames} = {rate:.1f}%")
    print(f"   저장: {OUTPUT_JSON}")
    print(f"\n다음 단계: python3 scripts/generate_v5_viewer.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prompt", default=DEFAULT_PROMPT,
        help="Grounding prompt (기본: '<grounding>The gray basket is at')"
    )
    parser.add_argument(
        "--max_episodes", type=int, default=None,
        help="테스트용: 처리할 최대 에피소드 수"
    )
    args = parser.parse_args()
    print(f"Prompt: {args.prompt}")
    main(args)

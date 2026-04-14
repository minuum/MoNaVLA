#!/usr/bin/env python3
"""
V5 Gray Basket 인식 & 방향 분석 스크립트

두 가지 분석 모드:
  --fast  : 기존 v5_grounding.json bbox로 즉시 분석 (GPU 불필요)
  --vqa   : 여러 VQA 프롬프트 새로 실행 (GPU 필요)

VQA 프롬프트들:
  P1_presence    : "Is there a gray basket?"           → yes/no
  P2_direction   : "The gray basket is located on the" → left/right/center
  P3_nav         : "To approach the basket, turn"      → left/right/forward
  P4_size        : "The gray basket appears"           → large/small/close/far
  P5_free        : "An image of a robot."              → free caption, keyword parse

방향-액션 상관관계:
  basket_left   ↔ FWD+LEFT / LEFT
  basket_center ↔ FORWARD
  basket_right  ↔ FWD+RIGHT / RIGHT

Usage:
  python3 scripts/run_v5_basket_analysis.py --fast
  python3 scripts/run_v5_basket_analysis.py --vqa --sample 100
  python3 scripts/run_v5_basket_analysis.py --vqa
  python3 scripts/run_v5_basket_analysis.py --fast --vqa   # 둘 다

Output:
  ROS_action/v5_data_bak/v5_basket_analysis.json
"""

import argparse
import json
import os
import time
from pathlib import Path
from collections import defaultdict

import h5py
import torch
from PIL import Image

# ── 경로 ────────────────────────────────────────────────────────
BASE_DIR       = Path("/home/billy/25-1kp/MoNaVLA/ROS_action/v5_data_bak")
H5_DIR         = BASE_DIR / "mobile_vla_dataset_v5"
IMG_DIR        = BASE_DIR / "mobile_vla_dataset_v5(Image)"
GROUNDING_JSON = BASE_DIR / "v5_grounding.json"
OUTPUT_JSON    = BASE_DIR / "v5_basket_analysis.json"
MODEL_PATH     = Path("/home/billy/.cache/huggingface/hub/models--microsoft--kosmos-2-patch14-224/snapshots/e91cfbcb4ce051b6a55bfb5f96165a3bbf5eb82c")
DEVICE         = "cuda" if torch.cuda.is_available() else "cpu"

# ── 액션 레이블 매핑 (generate_v5_viewer.py 와 동일) ─────────────
def action_label(action):
    lx, az = float(action[0]), float(action[1])
    if lx == 0.0 and az == 0.0: return "STOP"
    if lx > 0 and az > 0:       return "FWD+LEFT"
    if lx > 0 and az < 0:       return "FWD+RIGHT"
    if lx > 0:                   return "FORWARD"
    if az > 0:                   return "LEFT"
    if az < 0:                   return "RIGHT"
    return "STOP"

# 방향과 기대 액션 매핑
DIRECTION_EXPECTED_ACTIONS = {
    "left":   {"FWD+LEFT", "LEFT"},
    "center": {"FORWARD"},
    "right":  {"FWD+RIGHT", "RIGHT"},
}

# ── VQA 프롬프트 정의 ────────────────────────────────────────────
# 각 프롬프트의 파싱 방식:
#   - keywords_pos: 이 단어가 있으면 해당 방향/결과
#   - parse: "presence" | "direction" | "nav" | "size" | "free"
PROMPTS = {
    "P1_presence": {
        "text":  "Question: Is there a gray basket or container in the image? Answer:",
        "parse": "presence",
        "desc":  "바구니 존재 여부 (yes/no)",
    },
    "P2_direction": {
        "text":  "<grounding>The gray basket is located on the",
        "parse": "direction",
        "desc":  "바구니 위치 완성형 (left/center/right)",
    },
    "P3_nav": {
        "text":  "To center the gray basket in view, the robot should turn",
        "parse": "nav",
        "desc":  "중앙 정렬 위한 회전 방향 (left/right/already centered)",
    },
    "P4_size": {
        "text":  "<grounding>The gray basket appears",
        "parse": "size",
        "desc":  "바구니 크기/거리 추정 (large/small/close/far)",
    },
    "P5_free": {
        "text":  "An image of a robot navigating in a room.",
        "parse": "free",
        "desc":  "자유 캡션 → 바구니 키워드 + 방향 파싱",
    },
}

BASKET_KEYWORDS  = {"basket", "box", "container", "bin", "gray box", "grey box"}
DIRECT_LEFT      = {"left", "left side", "to the left", "on the left"}
DIRECT_RIGHT     = {"right", "right side", "to the right", "on the right"}
DIRECT_CENTER    = {"center", "middle", "front", "directly", "straight", "centered"}
SIZE_LARGE       = {"large", "big", "close", "near", "fills", "wide"}
SIZE_SMALL       = {"small", "tiny", "far", "distant", "away"}


def parse_output(raw: str, mode: str) -> dict:
    """VQA 출력 텍스트를 파싱해서 구조화된 결과 반환."""
    text = raw.lower().strip()

    result = {
        "raw":           raw[:200],
        "basket_mentioned": False,
        "direction":     None,   # left / center / right / unknown
        "size":          None,   # large / small / unknown
        "presence":      None,   # yes / no / unknown
        "nav_turn":      None,   # left / right / none / unknown
    }

    # 공통: 바구니 키워드 체크
    result["basket_mentioned"] = any(kw in text for kw in BASKET_KEYWORDS)

    if mode == "presence":
        if text.startswith("yes") or " yes" in text[:30]:
            result["presence"] = "yes"
        elif text.startswith("no") or " no" in text[:30]:
            result["presence"] = "no"
        else:
            result["presence"] = "unknown"
        # presence 텍스트에서도 방향 파싱 시도
        _parse_direction(text, result)

    elif mode in ("direction", "nav", "free"):
        _parse_direction(text, result)

    elif mode == "size":
        if any(kw in text for kw in SIZE_LARGE):
            result["size"] = "large"
        elif any(kw in text for kw in SIZE_SMALL):
            result["size"] = "small"
        else:
            result["size"] = "unknown"

    if mode == "nav":
        # nav는 "turn left" "turn right" "already centered" 등
        if "left" in text[:60]:
            result["nav_turn"] = "left"
        elif "right" in text[:60]:
            result["nav_turn"] = "right"
        elif any(kw in text[:60] for kw in ("already", "forward", "straight", "centered", "center")):
            result["nav_turn"] = "none"
        else:
            result["nav_turn"] = "unknown"

    return result


def _parse_direction(text: str, result: dict):
    """텍스트에서 방향 키워드 파싱 (result 딕셔너리를 in-place로 수정)."""
    found_left   = any(kw in text for kw in DIRECT_LEFT)
    found_right  = any(kw in text for kw in DIRECT_RIGHT)
    found_center = any(kw in text for kw in DIRECT_CENTER)

    if found_left and not found_right:
        result["direction"] = "left"
    elif found_right and not found_left:
        result["direction"] = "right"
    elif found_center and not found_left and not found_right:
        result["direction"] = "center"
    elif found_left and found_right:
        # 둘 다 있으면 먼저 나온 쪽
        li = next((i for i, w in enumerate(text.split()) if w in DIRECT_LEFT), 9999)
        ri = next((i for i, w in enumerate(text.split()) if w in DIRECT_RIGHT), 9999)
        result["direction"] = "left" if li < ri else "right"
    else:
        result["direction"] = "unknown"


# ── Fast 분석: 기존 grounding JSON으로 bbox 기반 방향 추출 ──────────
def analyze_from_grounding(grounding_data: dict, h5_data: dict) -> dict:
    """
    v5_grounding.json의 valid_bboxes center_x → direction
    action label과 cross-correlate
    """
    print("\n[ Fast 분석: 기존 v5_grounding.json 활용 ]")
    results = {}

    for ep_id, frames in grounding_data.items():
        if ep_id not in h5_data:
            continue
        actions = h5_data[ep_id]
        ep_result = {}

        for frame_str, gr in frames.items():
            frame_idx = int(frame_str)
            act = actions[frame_idx] if frame_idx < len(actions) else [0, 0, 0]
            act_label = action_label(act)

            valid = gr.get("valid_bboxes", [])
            caption = gr.get("caption", "")

            # 바구니 감지 여부
            basket_bboxes = [b for b in valid
                             if any(kw in b.get("entity", "").lower()
                                    for kw in ("basket", "box", "container", "bin"))]
            gray_bboxes   = [b for b in valid
                             if "gray" in b.get("entity", "").lower()
                             or "grey" in b.get("entity", "").lower()]

            best_bbox = (basket_bboxes or gray_bboxes or valid or [None])[0]

            if best_bbox:
                cx = (best_bbox["x1"] + best_bbox["x2"]) / 2
                direction = "left" if cx < 0.40 else "right" if cx > 0.60 else "center"
                bbox_area  = best_bbox["area"]
                entity     = best_bbox["entity"]
            else:
                direction = "unknown"
                bbox_area  = 0.0
                entity     = None

            basket_detected = bool(basket_bboxes or gray_bboxes)

            # 방향-액션 정합성
            expected = DIRECTION_EXPECTED_ACTIONS.get(direction, set())
            direction_match = act_label in expected if direction != "unknown" else None

            ep_result[frame_idx] = {
                "action":          act_label,
                "action_raw":      [round(float(v), 3) for v in act],
                "basket_detected": basket_detected,
                "entity":          entity,
                "direction_bbox":  direction,
                "bbox_area":       round(bbox_area, 4),
                "direction_match": direction_match,
                "caption":         caption[:120],
            }

        results[ep_id] = ep_result

    return results


# ── VQA 분석 ────────────────────────────────────────────────────
def load_model():
    from transformers import AutoProcessor, AutoModelForVision2Seq
    print(f"Kosmos-2 로딩 ({DEVICE})...")
    processor = AutoProcessor.from_pretrained(str(MODEL_PATH))
    model = AutoModelForVision2Seq.from_pretrained(
        str(MODEL_PATH),
        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
    ).to(DEVICE).eval()
    print("  ✅ 로드 완료")
    return processor, model


def run_vqa(processor, model, image: Image.Image, prompt_text: str) -> str:
    """단일 이미지 + 프롬프트 → raw 텍스트 출력."""
    inputs = processor(text=prompt_text, images=image, return_tensors="pt")
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
    pv = inputs["pixel_values"].to(torch.float16 if DEVICE == "cuda" else torch.float32)

    with torch.no_grad():
        gen = model.generate(
            pixel_values=pv,
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            image_embeds=None,
            image_embeds_position_mask=inputs.get("image_embeds_position_mask"),
            use_cache=True,
            max_new_tokens=64,
        )
    new_ids = gen[:, inputs["input_ids"].shape[1]:]
    raw = processor.batch_decode(new_ids, skip_special_tokens=True)[0]
    # post_process로 entity 제거한 순수 텍스트
    text, _ = processor.post_process_generation(raw)
    return text.strip()


def analyze_vqa(h5_data: dict, sample_frames: int | None = None) -> dict:
    """모든 V5 프레임에 5개 VQA 프롬프트 실행."""
    processor, model = load_model()

    # 에피소드 목록
    episodes = sorted([d for d in os.listdir(IMG_DIR) if (IMG_DIR / d).is_dir()])
    results = {}

    sampled = 0
    total_target = sample_frames

    print(f"\n[ VQA 분석: {len(PROMPTS)}개 프롬프트 × {'전체' if not sample_frames else sample_frames} 프레임 ]")
    for pname, pcfg in PROMPTS.items():
        print(f"  {pname}: {pcfg['desc']}")

    t_start = time.time()

    for ep_name in episodes:
        ep_dir = IMG_DIR / ep_name
        frames = sorted([f for f in os.listdir(ep_dir) if f.endswith(".png")])
        ep_result = {}

        actions = h5_data.get(ep_name, [])

        for frame_file in frames:
            frame_idx = int(frame_file.replace("frame_", "").replace(".png", ""))
            act = actions[frame_idx] if frame_idx < len(actions) else [0, 0, 0]
            act_label = action_label(act)

            image = Image.open(ep_dir / frame_file).convert("RGB")

            frame_result = {
                "action": act_label,
                "action_raw": [round(float(v), 3) for v in act],
                "prompts": {},
            }

            for pname, pcfg in PROMPTS.items():
                raw_output = run_vqa(processor, model, image, pcfg["text"])
                parsed = parse_output(raw_output, pcfg["parse"])
                frame_result["prompts"][pname] = parsed

            # 프롬프트들 합산: 방향 투표
            directions = [
                frame_result["prompts"][p]["direction"]
                for p in ("P2_direction", "P3_nav", "P5_free")
                if frame_result["prompts"][p]["direction"] not in (None, "unknown")
            ]
            if directions:
                from collections import Counter
                voted = Counter(directions).most_common(1)[0][0]
            else:
                voted = "unknown"
            frame_result["voted_direction"] = voted

            # 방향-액션 정합성
            expected = DIRECTION_EXPECTED_ACTIONS.get(voted, set())
            frame_result["direction_match"] = act_label in expected if voted != "unknown" else None

            ep_result[frame_idx] = frame_result
            sampled += 1

            if sampled % 20 == 0:
                elapsed = time.time() - t_start
                fps = sampled / max(elapsed, 0.001)
                print(f"  {sampled}프레임 완료 ({fps:.1f} fps)")

            if total_target and sampled >= total_target:
                break

        results[ep_name] = ep_result
        if total_target and sampled >= total_target:
            break

    return results


# ── 통계 출력 ────────────────────────────────────────────────────
def print_stats(results: dict, mode: str):
    print(f"\n{'='*60}")
    print(f"  {mode} 분석 결과 통계")
    print(f"{'='*60}")

    total = 0
    basket_detected = 0
    direction_counts = defaultdict(int)
    action_counts    = defaultdict(int)
    match_total      = 0
    match_correct    = 0

    # 방향별 액션 분포 매트릭스
    dir_action_matrix = defaultdict(lambda: defaultdict(int))

    for ep_id, frames in results.items():
        for frame_idx, fr in frames.items():
            total += 1

            if mode.lower().startswith("fast"):
                det = fr.get("basket_detected", False)
                direction = fr.get("direction_bbox", "unknown")
                act = fr.get("action", "?")
                match = fr.get("direction_match")
            else:
                # VQA 모드
                det = any(
                    fr["prompts"][p].get("basket_mentioned", False)
                    for p in fr.get("prompts", {})
                )
                direction = fr.get("voted_direction", "unknown")
                act = fr.get("action", "?")
                match = fr.get("direction_match")

            if det:
                basket_detected += 1
            direction_counts[direction] += 1
            action_counts[act] += 1

            dir_action_matrix[direction][act] += 1

            if match is not None:
                match_total += 1
                if match:
                    match_correct += 1

    detection_rate = basket_detected / total * 100 if total else 0
    match_rate = match_correct / match_total * 100 if match_total else 0

    print(f"\n총 프레임: {total}")
    print(f"바구니 감지율: {basket_detected}/{total} = {detection_rate:.1f}%")

    print(f"\n방향 분포:")
    for d, cnt in sorted(direction_counts.items(), key=lambda x: -x[1]):
        pct = cnt / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {d:<10} {cnt:4d} ({pct:5.1f}%)  {bar}")

    print(f"\n방향-액션 정합률: {match_correct}/{match_total} = {match_rate:.1f}%")
    print(f"  (방향 unknown 제외)")

    print(f"\n방향별 액션 분포 매트릭스:")
    actions_sorted = sorted(action_counts.keys())
    header = f"  {'방향':<10}" + "".join(f"{a:>12}" for a in actions_sorted)
    print(header)
    print("  " + "-" * (10 + 12 * len(actions_sorted)))
    for d in ("left", "center", "right", "unknown"):
        if d not in dir_action_matrix:
            continue
        row = dir_action_matrix[d]
        row_total = sum(row.values())
        cells = "".join(
            f"{row.get(a, 0):>10d}{'*' if a in DIRECTION_EXPECTED_ACTIONS.get(d, set()) else ' ':>2}"
            for a in actions_sorted
        )
        print(f"  {d:<10}{cells}  (n={row_total})")
    print("  * = 방향과 기대 액션 일치")


# ── 결과 병합 ────────────────────────────────────────────────────
def merge_results(fast_res: dict | None, vqa_res: dict | None) -> dict:
    """fast와 vqa 결과를 프레임별로 병합."""
    merged = {}
    all_eps = set()
    if fast_res: all_eps |= set(fast_res.keys())
    if vqa_res:  all_eps |= set(vqa_res.keys())

    for ep in all_eps:
        merged[ep] = {}
        fast_ep = (fast_res or {}).get(ep, {})
        vqa_ep  = (vqa_res  or {}).get(ep, {})
        all_frames = set(fast_ep.keys()) | set(vqa_ep.keys())
        for f in all_frames:
            merged[ep][f] = {}
            if f in fast_ep: merged[ep][f]["fast"] = fast_ep[f]
            if f in vqa_ep:  merged[ep][f]["vqa"]  = vqa_ep[f]

    return merged


# ── H5 데이터 로드 ───────────────────────────────────────────────
def load_h5_actions() -> dict:
    h5_data = {}
    for fname in os.listdir(H5_DIR):
        if not fname.endswith(".h5"):
            continue
        ep_id = fname.replace(".h5", "")
        with h5py.File(H5_DIR / fname, "r") as f:
            h5_data[ep_id] = f["actions"][:].tolist()
    return h5_data


# ── 메인 ────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast",   action="store_true", help="기존 grounding JSON으로 즉시 분석")
    parser.add_argument("--vqa",    action="store_true", help="VQA 프롬프트 실행 (GPU)")
    parser.add_argument("--sample", type=int, default=None, help="VQA용 샘플 프레임 수 (기본: 전체)")
    args = parser.parse_args()

    if not args.fast and not args.vqa:
        args.fast = True  # 기본값: fast 모드

    print("V5 Basket Analysis 시작")
    print(f"  모드: {'fast ' if args.fast else ''}{'vqa' if args.vqa else ''}")

    # H5 액션 데이터 로드
    print("H5 액션 데이터 로드 중...")
    h5_data = load_h5_actions()
    print(f"  {len(h5_data)}개 에피소드 로드 완료")

    fast_results = None
    vqa_results  = None

    # ── Fast 분석 ──
    if args.fast:
        if not GROUNDING_JSON.exists():
            print("⚠️  v5_grounding.json 없음 — run_v5_grounding.py 먼저 실행 필요")
        else:
            with open(GROUNDING_JSON, encoding="utf-8") as f:
                grounding_data = json.load(f)
            fast_results = analyze_from_grounding(grounding_data, h5_data)
            print_stats(fast_results, "Fast (BBox 기반)")

    # ── VQA 분석 ──
    if args.vqa:
        # 전역에서 sample_targets 사용
        sample_targets = args.sample
        vqa_results = analyze_vqa(h5_data, sample_frames=args.sample)
        print_stats(vqa_results, "VQA")

    # ── 결과 저장 ──
    merged = merge_results(fast_results, vqa_results)
    OUTPUT_JSON.write_text(json.dumps(merged, ensure_ascii=False, indent=2))
    print(f"\n✅ 저장 완료: {OUTPUT_JSON}")

    if fast_results and not vqa_results:
        print("\n팁: --vqa 추가하면 5개 프롬프트로 심층 분석 가능")
        print("     --vqa --sample 50  (50프레임만 빠르게 테스트)")

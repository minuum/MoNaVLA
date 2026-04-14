#!/usr/bin/env python3
"""
basket_dataset_v3 Action 다양성 분석 스크립트
사용법: python3 docs/scripts/analyze_action_diversity.py --dataset ROS_action/basket_dataset_v3/

목적: 수집된 데이터가 타이밍 암기 방지 기준을 충족하는지 검증
  - 유니크 시퀀스 수 ≥ 10개 (기존 basket_dataset_v2: 2개)
  - 프레임별 액션 결정성 < 80% (기존: 100%)
"""

import argparse
import glob
import os
import json
from collections import Counter
import numpy as np

try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False
    print("⚠️  h5py 없음. JSON 분석 모드로 실행합니다.")

# Action 매핑: (linear_x, angular_y) → 문자
ACTION_CHAR_MAP = {
    (0.0,  0.0):   "STOP",
    (1.15, 0.0):   "F",
    (-1.15, 0.0):  "B",
    (0.0,  1.15):  "L",
    (0.0, -1.15):  "R",
    (1.15, 1.15):  "FL",
    (1.15, -1.15): "FR",
    (-1.15, 1.15): "BL",
    (-1.15,-1.15): "BR",
}

def snap(val, threshold=0.5):
    """연속 값을 이산 값(0, ±1.15)으로 스냅"""
    if abs(val) < threshold:
        return 0.0
    return 1.15 if val > 0 else -1.15

def action_to_char(linear_x, angular_y):
    """액션 벡터를 문자로 변환"""
    sx = snap(linear_x)
    sy = snap(angular_y)
    return ACTION_CHAR_MAP.get((sx, sy), f"[{linear_x:.2f},{angular_y:.2f}]")

def load_h5_episode(path):
    """H5 에피소드에서 (sequence_chars, instruction) 반환"""
    with h5py.File(path, "r") as f:
        actions = np.array(f["actions"])  # shape: (N, 3) or (N, 2)
        instr = f["instruction"][()] if "instruction" in f else b"unknown"
        instr = instr.decode("utf-8") if isinstance(instr, bytes) else str(instr)
    seq = [action_to_char(a[0], a[1]) for a in actions]
    return seq, instr

def load_json_episode(path):
    """JSON 분석 파일에서 (sequence_chars, instruction) 반환"""
    with open(path) as f:
        data = json.load(f)
    frames = data.get("frames", [])
    seq = [f.get("char", "?") for f in frames]
    return seq, data.get("instruction", "unknown")

def analyze_dataset(dataset_dir):
    """데이터셋 다양성 분석"""
    # H5 파일 우선, 없으면 JSON
    h5_files = glob.glob(os.path.join(dataset_dir, "**/*.h5"), recursive=True)
    json_files = glob.glob(os.path.join(dataset_dir, "**/*_analysis.json"), recursive=True)

    episodes = []
    if HAS_H5PY and h5_files:
        print(f"📂 H5 파일 {len(h5_files)}개 발견")
        for p in h5_files:
            try:
                seq, instr = load_h5_episode(p)
                episodes.append({"seq": seq, "instr": instr, "file": os.path.basename(p)})
            except Exception as e:
                print(f"  ⚠️  {os.path.basename(p)} 로드 실패: {e}")
    elif json_files:
        print(f"📂 JSON 파일 {len(json_files)}개 발견")
        for p in json_files:
            try:
                seq, instr = load_json_episode(p)
                episodes.append({"seq": seq, "instr": instr, "file": os.path.basename(p)})
            except Exception as e:
                print(f"  ⚠️  {os.path.basename(p)} 로드 실패: {e}")
    else:
        print("❌ H5/JSON 파일을 찾을 수 없습니다.")
        return

    total = len(episodes)
    print(f"\n총 {total}개 에피소드 로드\n")

    # ── 1. 유니크 시퀀스 수 ────────────────────────────────────────
    seq_counter = Counter([tuple(ep["seq"]) for ep in episodes])
    unique_count = len(seq_counter)
    print("=" * 60)
    print(f"■ 유니크 시퀀스 수: {unique_count}개  (목표: ≥ 10개)")
    print(f"  {'✅ PASS' if unique_count >= 10 else '❌ FAIL — 타이밍 암기 의심'}")
    print()
    print(f"  상위 5개 시퀀스:")
    for seq, cnt in seq_counter.most_common(5):
        pct = 100 * cnt / total
        print(f"    [{' → '.join(seq[:8])}...] × {cnt}회 ({pct:.1f}%)")

    # ── 2. 프레임별 결정성 ─────────────────────────────────────────
    max_len = max(len(ep["seq"]) for ep in episodes)
    frame_actions = [[] for _ in range(max_len)]
    for ep in episodes:
        for i, a in enumerate(ep["seq"]):
            frame_actions[i].append(a)

    print()
    print("=" * 60)
    max_det = 0.0
    low_div_frames = []
    for i, actions in enumerate(frame_actions):
        if not actions:
            continue
        cnt = Counter(actions)
        dominant_ratio = cnt.most_common(1)[0][1] / len(actions)
        max_det = max(max_det, dominant_ratio)
        if dominant_ratio > 0.80:
            low_div_frames.append((i+1, dominant_ratio, cnt.most_common(1)[0][0]))

    avg_det = np.mean([
        Counter(frame_actions[i]).most_common(1)[0][1] / len(frame_actions[i])
        for i in range(len(frame_actions)) if frame_actions[i]
    ])
    print(f"■ 프레임별 최대 결정성: {max_det:.1%}  (목표: < 80%)")
    print(f"  평균 결정성: {avg_det:.1%}")
    print(f"  {'✅ PASS' if max_det < 0.80 else '❌ FAIL — 결정성 너무 높음'}")
    if low_div_frames:
        print(f"\n  ⚠️  결정성 80% 초과 프레임 ({len(low_div_frames)}개):")
        for frame, ratio, dominant in low_div_frames[:5]:
            print(f"    Frame {frame:>2}: {dominant} = {ratio:.1%}")

    # ── 3. Instruction 분포 ────────────────────────────────────────
    instr_counter = Counter([ep["instr"] for ep in episodes])
    print()
    print("=" * 60)
    print(f"■ Instruction 종류: {len(instr_counter)}개")
    for instr, cnt in instr_counter.most_common():
        print(f"  [{cnt:>3}회] {instr}")

    # ── 최종 판정 ──────────────────────────────────────────────────
    print()
    print("=" * 60)
    passed = unique_count >= 10 and max_det < 0.80
    print(f"■ 최종 판정: {'✅ PASS — 타이밍 암기 방지 조건 충족' if passed else '❌ FAIL — 추가 Variant 수집 필요'}")
    print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="basket_dataset_v3 Action 다양성 검증")
    parser.add_argument("--dataset", required=True, help="데이터셋 디렉토리 경로")
    args = parser.parse_args()
    analyze_dataset(args.dataset)

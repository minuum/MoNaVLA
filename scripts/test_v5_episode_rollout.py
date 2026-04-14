#!/usr/bin/env python3
"""
V5 Episode Rollout 평가 — 추론 서버 API 사용
에피소드를 처음부터 끝까지 순서대로 프레임 넣어서 히스토리 쌓으며 평가

Usage: python3 scripts/test_v5_episode_rollout.py
"""
import os, sys, json, base64, time
import urllib.request
import urllib.error
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V5_DATA = ROOT / "ROS_action/v5_data_bak/mobile_vla_dataset_v5"
INFER_URL = "http://localhost:8000"

CLASS_NAMES = {0:"STOP", 1:"FORWARD", 2:"LEFT", 3:"RIGHT", 4:"FWD+L", 5:"FWD+R"}
NUM_CLASSES = 6

# V5 3D action → 6-class label (nav_h5_dataset_impl.py와 동일 로직)
def action_to_label(a):
    x, y, az = float(a[0]), float(a[1]), float(a[2]) if len(a) > 2 else 0.0
    is_x_pos = x > 0.3;  is_x_neg = x < -0.3
    is_y_pos = y > 0.3;  is_y_neg = y < -0.3
    is_az_pos = az > 0.15; is_az_neg = az < -0.15

    if not is_x_pos and not is_x_neg and not is_y_pos and not is_y_neg:
        if not is_az_pos and not is_az_neg:
            return 0  # STOP
        if is_az_pos:  return 4  # RIGHT (in-place)
        if is_az_neg:  return 3  # LEFT (in-place)
    if is_x_pos and not is_y_pos and not is_y_neg:
        return 1  # FORWARD
    if not is_x_pos and not is_x_neg and is_y_pos:
        return 2  # LEFT
    if not is_x_pos and not is_x_neg and is_y_neg:
        return 3  # RIGHT
    if is_x_pos and is_y_pos:
        return 4  # FWD+L
    if is_x_pos and is_y_neg:
        return 5  # FWD+R
    if is_x_neg:
        return 0  # backward → STOP
    return 0

def img_to_b64(img_array):
    from PIL import Image
    import io
    pil = Image.fromarray(img_array.astype(np.uint8)).resize((224, 224))
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()

def api_call(b64_img, instruction, api_key, reset=False):
    payload = json.dumps({"image": b64_img, "instruction": instruction,
                          "reset": reset}).encode()
    req = urllib.request.Request(
        f"{INFER_URL}/predict",
        data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def get_api_key():
    try:
        log = Path("/tmp/v5_infer_log.txt").read_text(errors="ignore")
        for line in log.splitlines():
            if "API Key:" in line:
                return line.strip().split()[-1]
    except:
        pass
    return os.getenv("VLA_API_KEY", "")

def action_to_class_from_response(action):
    """inference server response action [lx, ly] → class"""
    # class_action_map 역매핑 (inference_server의 6-class 매핑과 동일)
    lx, ly = float(action[0]), float(action[1])
    if lx == 0.0 and ly == 0.0:  return 0   # STOP (first-frame enforcement도 포함)
    if lx > 0.5 and abs(ly) < 0.3: return 1  # FORWARD
    if abs(lx) < 0.3 and ly > 0.3: return 2  # LEFT
    if abs(lx) < 0.3 and ly < -0.3: return 3 # RIGHT
    if lx > 0.5 and ly > 0.3: return 4        # FWD+L
    if lx > 0.5 and ly < -0.3: return 5       # FWD+R
    return 1  # default FORWARD

def evaluate_episodes():
    import h5py

    api_key = get_api_key()
    if not api_key:
        print("❌ API key not found. Is inference server running?")
        sys.exit(1)

    # health check
    try:
        req = urllib.request.Request(f"{INFER_URL}/health",
                                     headers={"X-API-Key": api_key})
        with urllib.request.urlopen(req, timeout=3) as r:
            health = json.loads(r.read())
        print(f"✅ Server: {health.get('model_name')} | GPU: {health.get('gpu_memory',{}).get('allocated_gb',0):.1f}GB")
    except Exception as e:
        print(f"❌ Server not reachable: {e}")
        sys.exit(1)

    episodes = sorted(V5_DATA.glob("episode_*.h5"))
    print(f"📂 Total episodes: {len(episodes)}")

    # 전체 episodes → val split 80% 이후 (train_split=0.85 기준)
    n_val = max(1, int(len(episodes) * 0.15))
    val_episodes = episodes[-n_val:]
    print(f"📊 Val episodes: {len(val_episodes)}\n")

    # 집계
    confusion = np.zeros((NUM_CLASSES, NUM_CLASSES), dtype=int)
    ep_pm_rates = []
    total_pm, total_frames = 0, 0
    skip_first = True  # 첫 프레임은 zero enforcement라 GT 비교 제외

    results_per_ep = []

    for ep_path in val_episodes:
        print(f"\n{'─'*55}")
        print(f"📹 {ep_path.name}")

        with h5py.File(ep_path, "r") as f:
            imgs = f["observations"]["images"][:]       # (N, H, W, 3)
            actions = f["actions"][:]                    # (N, 3)
            instr_raw = f["language_instruction"][0]
            instruction = instr_raw.decode() if hasattr(instr_raw, "decode") else str(instr_raw)

        n_frames = len(imgs)
        print(f"   Instruction : {instruction[:70]}")
        print(f"   Frames      : {n_frames}")

        ep_pm, ep_total = 0, 0
        frame_log = []

        for t in range(n_frames):
            is_first = (t == 0)
            b64 = img_to_b64(imgs[t])

            try:
                resp = api_call(b64, instruction, api_key, reset=is_first)
                pred_action = resp["action"]  # [lx, ly]
            except Exception as e:
                print(f"   ⚠️  Frame {t}: API error: {e}")
                continue

            gt_label = action_to_label(actions[t])
            pred_label = action_to_class_from_response(pred_action)

            # 첫 프레임은 zero enforcement → skip
            if skip_first and is_first:
                frame_log.append((t, gt_label, pred_label, False, True))
                continue

            confusion[gt_label, pred_label] += 1
            total_frames += 1
            ep_total += 1
            match = (pred_label == gt_label)
            if match:
                total_pm += 1
                ep_pm += 1
            frame_log.append((t, gt_label, pred_label, match, False))

        # 에피소드별 결과
        ep_rate = ep_pm / ep_total * 100 if ep_total > 0 else 0
        ep_pm_rates.append(ep_rate)
        results_per_ep.append({"ep": ep_path.name, "pm": ep_rate, "n": ep_total})

        print(f"   PM: {ep_rate:.1f}% ({ep_pm}/{ep_total})")
        for t, gt, pred, match, skipped in frame_log:
            mark = "⏭" if skipped else ("✅" if match else "❌")
            print(f"     t={t:02d} GT={CLASS_NAMES.get(gt,'?'):<8} PRED={CLASS_NAMES.get(pred,'?'):<8} {mark}")

    # ── 최종 집계
    print(f"\n{'='*55}")
    print(f"  V5 Episode Rollout Evaluation — Final Results")
    print(f"{'='*55}")
    print(f"  Episodes  : {len(val_episodes)}")
    print(f"  Frames    : {total_frames}  (first-frame skipped)")
    if total_frames == 0:
        print("❌ No valid frames!"); return

    pm_rate = total_pm / total_frames * 100
    print(f"  PM (overall) : {pm_rate:.2f}%  ({total_pm}/{total_frames})")
    print(f"  PM (per-ep mean) : {np.mean(ep_pm_rates):.2f}%")

    print(f"\n  Per-Episode PM:")
    for r in results_per_ep:
        print(f"    {r['ep'][:50]:<50}  {r['pm']:5.1f}% ({r['n']} frames)")

    print(f"\n  {'Class':<10} {'GT':>6} {'Correct':>8} {'Acc':>8}")
    print(f"  {'─'*36}")
    for c in range(NUM_CLASSES):
        gt_tot = int(confusion[c].sum())
        correct = int(confusion[c, c])
        acc = correct / gt_tot * 100 if gt_tot > 0 else 0.0
        print(f"  {CLASS_NAMES[c]:<10} {gt_tot:>6} {correct:>8} {acc:>7.1f}%")

    print(f"\n  Confusion Matrix (row=GT, col=PRED)")
    print("  GT\\PRED  " + "".join(f"{CLASS_NAMES[c]:>8}" for c in range(NUM_CLASSES)))
    for r in range(NUM_CLASSES):
        row = f"  {CLASS_NAMES[r]:<8} " + "".join(f"{confusion[r,c]:>8}" for c in range(NUM_CLASSES))
        print(row)
    print()

    # JSON 저장
    out = {
        "pm_overall": pm_rate,
        "pm_per_ep_mean": float(np.mean(ep_pm_rates)),
        "total_frames": total_frames,
        "per_episode": results_per_ep,
        "confusion": confusion.tolist(),
    }
    out_path = Path("/tmp/v5_rollout_result.json")
    out_path.write_text(json.dumps(out, indent=2))
    print(f"  💾 Saved: {out_path}")

if __name__ == "__main__":
    evaluate_episodes()

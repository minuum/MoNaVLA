#!/usr/bin/env python3
"""
V5 체크포인트 순차 비교 평가
- 추론 서버를 각 ckpt로 재시작하고 val 에피소드 rollout PM/DM 측정
- GPU 메모리 제한 환경(학습과 공존)에서 작동

Usage: python3 scripts/test_v5_ckpt_compare.py
"""
import os, sys, json, subprocess, time, base64
import urllib.request, urllib.error
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V5_DATA = ROOT / "ROS_action/v5_data_bak/mobile_vla_dataset_v5"
INFER_URL = "http://localhost:8001"   # 학습 서버(8000)와 포트 분리
API_KEY   = "nav-vla-compare-2024"
LOG_OUT   = Path("/tmp/v5_ckpt_compare_result.json")

CLASS_NAMES = {0:"STOP",1:"FORWARD",2:"LEFT",3:"RIGHT",4:"FWD+L",5:"FWD+R"}

# ── 비교할 체크포인트 목록 ──────────────────────────────────────────────────
CHECKPOINTS = [
    {
        "name": "exp01_best (val=2.270, full data+straight)",
        "ckpt": "runs/v5_nav/kosmos/mobile_vla_v5_exp01/2026-04-10/v5-exp01-discrete/epoch_epoch=epoch=05-val_loss=val_loss=2.270.ckpt",
        "config": "configs/mobile_vla_v5_exp01_discrete.json",
    },
    {
        "name": "exp02_best (val=2.210, no-straight+stratified)",
        "ckpt": "runs/v5_nav/kosmos/mobile_vla_v5_exp02/2026-04-10/v5-exp02-no-straight/epoch_epoch=epoch=05-val_loss=val_loss=2.210.ckpt",
        "config": "configs/mobile_vla_v5_exp02_no_straight.json",
    },
    {
        "name": "exp02_last (no-straight+stratified, last)",
        "ckpt": "runs/v5_nav/kosmos/mobile_vla_v5_exp02/2026-04-10/v5-exp02-no-straight/last.ckpt",
        "config": "configs/mobile_vla_v5_exp02_no_straight.json",
    },
]

# ── Val 에피소드: left+right, 마지막 20% ──────────────────────────────────
def get_val_episodes():
    all_files = sorted(V5_DATA.glob("episode_*.h5"))
    left  = [f for f in all_files if "left_path"  in f.name]
    right = [f for f in all_files if "right_path" in f.name]
    val = []
    for group in [left, right]:
        split = int(len(group) * 0.8)
        val.extend(group[split:])
    return sorted(val)

def action_to_label(a):
    x, y, az = float(a[0]), float(a[1]), float(a[2]) if len(a) > 2 else 0.0
    is_x_pos = x > 0.3;  is_x_neg = x < -0.3
    is_y_pos = y > 0.3;  is_y_neg = y < -0.3
    is_az_pos = az > 0.15; is_az_neg = az < -0.15
    if not is_x_pos and not is_x_neg and not is_y_pos and not is_y_neg:
        if not is_az_pos and not is_az_neg: return 0
        if is_az_pos:  return 4
        if is_az_neg:  return 3
    if is_x_pos and not is_y_pos and not is_y_neg: return 1
    if not is_x_pos and not is_x_neg and is_y_pos: return 2
    if not is_x_pos and not is_x_neg and is_y_neg: return 3
    if is_x_pos and is_y_pos: return 4
    if is_x_pos and is_y_neg: return 5
    return 0

def img_to_b64(img_array):
    from PIL import Image; import io
    pil = Image.fromarray(img_array.astype(np.uint8)).resize((224, 224))
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()

def api_call(b64_img, instruction, reset=False, retries=3):
    payload = json.dumps({"image": b64_img, "instruction": instruction, "reset": reset}).encode()
    req = urllib.request.Request(
        f"{INFER_URL}/predict",
        data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
        method="POST"
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                action = data.get("action", [0.0, 0.0])
                # inference_server does not return class_index; derive from action
                cls_idx = action_to_label(action)
                return action, cls_idx
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(1)

def wait_server_ready(timeout=500):
    """추론 서버가 뜨고 model_loaded=true 될 때까지 대기 (모델 선로딩 후 uvicorn 시작)"""
    print(f"  ⏳ 서버 준비 대기 중 (최대 {timeout}초)...", end="", flush=True)
    for i in range(timeout):
        try:
            with urllib.request.urlopen(f"{INFER_URL}/health", timeout=3) as r:
                data = json.loads(r.read())
                if data.get("model_loaded"):
                    print(f" 완료! ({i+1}초)")
                    return True
        except:
            pass
        time.sleep(1)
        if i % 15 == 14:
            print(".", end="", flush=True)
    print(" 타임아웃!")
    return False

def start_infer_server(ckpt_path, config_path):
    """추론 서버 subprocess 시작 (포트 8001, 메모리 제한 환경변수)"""
    env = os.environ.copy()
    env["VLA_CHECKPOINT_PATH"] = str(ROOT / ckpt_path)
    env["VLA_CONFIG_PATH"]     = str(ROOT / config_path)
    env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    # 학습과 공존: 추론 서버는 4GB 이내로 동작 (FP16 lean loading)
    env["VLA_USE_QUANT"] = "false"
    env["VLA_PORT"] = "8001"
    env["VLA_API_KEY"] = API_KEY

    OPENVLA_PYTHON = "/home/billy/anaconda3/envs/openvla/bin/python"
    python_exec = OPENVLA_PYTHON if os.path.exists(OPENVLA_PYTHON) else sys.executable

    cmd = [
        python_exec,
        str(ROOT / "robovlm_nav/serve/inference_server.py"),
        "--port", "8001"
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=open("/tmp/infer_server_subprocess.log", "w"),
        stderr=subprocess.STDOUT,
    )
    return proc

def stop_server(proc):
    """서버 종료 후 GPU 메모리 회수 대기"""
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    time.sleep(3)  # GPU 메모리 해제 대기

def eval_ckpt(ckpt_info, val_episodes):
    """단일 체크포인트에 대해 val rollout 평가"""
    name   = ckpt_info["name"]
    ckpt   = ckpt_info["ckpt"]
    config = ckpt_info["config"]

    # ckpt 존재 여부 확인
    ckpt_full = ROOT / ckpt
    if not ckpt_full.exists():
        print(f"  ⚠️  체크포인트 없음, 스킵: {ckpt_full.name}")
        return None

    print(f"\n{'='*60}")
    print(f"🔬 {name}")
    print(f"   ckpt: {ckpt_full.name}")
    print(f"{'='*60}")

    # 서버 시작
    proc = start_infer_server(ckpt, config)
    if not wait_server_ready(timeout=500):
        print("  ❌ 서버 시작 실패, 스킵")
        stop_server(proc)
        return None

    # 평가
    import h5py
    results_per_ep = []
    confusion = [[0]*6 for _ in range(6)]
    total_correct = total_frames = 0

    for ep_path in val_episodes:
        with h5py.File(ep_path, 'r') as f:
            images  = f['observations']['images'][:]
            actions = f['actions'][:]
            raw_inst = f['language_instruction'][0]
            instruction = raw_inst.decode() if isinstance(raw_inst, bytes) else str(raw_inst)

        n_frames = len(images)
        ep_correct = ep_total = 0
        ep_rows = []

        for t in range(n_frames):
            b64 = img_to_b64(images[t])
            reset = (t == 0)
            try:
                _, pred_cls = api_call(b64, instruction, reset=reset)
            except Exception as e:
                print(f"    API 오류 t={t}: {e}")
                continue

            # frame 0은 zero-enforcement → 스킵
            if reset:
                ep_rows.append(f"     t={t:02d} GT={CLASS_NAMES[action_to_label(actions[t])]:7s} PRED=SKIP(zero) ⏭")
                continue

            gt_cls = action_to_label(actions[t])
            match  = (pred_cls == gt_cls)
            confusion[gt_cls][pred_cls] += 1
            ep_total   += 1
            total_frames += 1
            if match:
                ep_correct += 1
                total_correct += 1

            ep_rows.append(
                f"     t={t:02d} GT={CLASS_NAMES[gt_cls]:7s} PRED={CLASS_NAMES.get(pred_cls,'?'):7s} {'✅' if match else '❌'}"
            )

        ep_pm = ep_correct / ep_total * 100 if ep_total else 0
        print(f"\n  📹 {ep_path.name[:55]}")
        print(f"     PM: {ep_pm:.1f}% ({ep_correct}/{ep_total})")
        for row in ep_rows:
            print(row)
        results_per_ep.append({"episode": ep_path.name, "pm": ep_pm, "n": ep_total})

    overall_pm = total_correct / total_frames * 100 if total_frames else 0

    # per-class accuracy
    per_class = {}
    for c in range(6):
        gt_total = sum(confusion[c])
        correct  = confusion[c][c]
        per_class[CLASS_NAMES[c]] = {"correct": correct, "total": gt_total,
                                      "acc": correct/gt_total*100 if gt_total else 0}

    print(f"\n  📊 Overall PM: {overall_pm:.2f}% ({total_correct}/{total_frames})")
    print(f"  Class Acc:")
    for cn, v in per_class.items():
        print(f"    {cn:8s}: {v['acc']:5.1f}% ({v['correct']}/{v['total']})")

    stop_server(proc)

    return {
        "name": name, "ckpt": ckpt,
        "overall_pm": overall_pm,
        "total_correct": total_correct, "total_frames": total_frames,
        "per_class": per_class,
        "per_episode": results_per_ep,
        "confusion": confusion,
    }


def main():
    import h5py
    val_eps = get_val_episodes()
    print(f"📂 Val 에피소드: {len(val_eps)}개")
    for e in val_eps:
        tag = "left" if "left" in e.name else "right"
        print(f"  [{tag}] {e.name[:60]}")

    all_results = []
    for ckpt_info in CHECKPOINTS:
        result = eval_ckpt(ckpt_info, val_eps)
        if result:
            all_results.append(result)
        time.sleep(5)  # GPU 메모리 완전 해제 여유

    # 최종 요약
    print(f"\n{'='*60}")
    print("  📋 최종 비교 요약")
    print(f"{'='*60}")
    print(f"  {'모델':<45} {'PM':>7}  {'LEFT':>6}  {'RIGHT':>6}  {'FWD+L':>6}  {'FWD+R':>6}")
    print(f"  {'-'*85}")
    for r in all_results:
        pc = r["per_class"]
        print(
            f"  {r['name']:<45} {r['overall_pm']:>6.1f}%"
            f"  {pc['LEFT']['acc']:>5.1f}%"
            f"  {pc['RIGHT']['acc']:>5.1f}%"
            f"  {pc['FWD+L']['acc']:>5.1f}%"
            f"  {pc['FWD+R']['acc']:>5.1f}%"
        )

    LOG_OUT.write_text(json.dumps(all_results, indent=2))
    print(f"\n  💾 저장: {LOG_OUT}")


if __name__ == "__main__":
    main()

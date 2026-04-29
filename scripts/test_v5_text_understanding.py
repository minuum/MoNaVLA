#!/usr/bin/env python3
"""
V5 VLM 텍스트 이해 테스트
- 동일 이미지 + 다른 instruction → action이 달라지는지 확인
- 테스트 A: inference_server 기반 (exp01_best, exp02_best)
- 테스트 B: Raw Kosmos-2 직접 hidden state 비교 (텍스트 이해 기준점)

Usage: /home/billy/anaconda3/envs/openvla/bin/python scripts/test_v5_text_understanding.py
"""
import os, sys, json, time, base64
import urllib.request
import subprocess
import numpy as np
from pathlib import Path
from PIL import Image
import io

ROOT = Path(__file__).resolve().parent.parent
V5_DATA = ROOT / "ROS_action/mobile_vla_dataset_v5"
INFER_URL = "http://localhost:8001"
API_KEY   = "nav-vla-text-test-2024"
LOG_OUT   = Path("/tmp/v5_text_understanding_result.json")

OPENVLA_PYTHON = "/home/billy/anaconda3/envs/openvla/bin/python"

CLASS_NAMES = {0:"STOP",1:"FORWARD",2:"LEFT",3:"RIGHT",4:"FWD+L",5:"FWD+R",6:"ROT_L",7:"ROT_R"}

INSTRUCTIONS = {
    # Exp07 PATH_TYPE_INSTRUCTIONS와 정확히 일치하는 문장 사용
    "left_1":    "Navigate to the left toward the gray basket",
    "left_2":    "Move left to approach the target",
    "left_3":    "Steer left to reach the basket",
    "right_1":   "Navigate to the right toward the gray basket",
    "right_2":   "Move right to approach the target",
    "right_3":   "Steer right to reach the basket",
    "forward_1": "Navigate straight forward to the gray basket",
    "forward_2": "Go directly ahead to the target",
}

CHECKPOINTS = [
    {
        "name": "exp07_path_type (last-v1)",
        "ckpt": "runs/v5_nav/kosmos/mobile_vla_v5_exp07/2026-04-13/v5-exp07-path-type/last-v1.ckpt",
        "config": "configs/mobile_vla_v5_exp07_path_type.json",
    },
    {
        "name": "exp21_pure_hf_head_only",
        "ckpt": "/tmp/monavla_resume_runs/kosmos/mobile_vla_v5_exp21/2026-04-21/v5-exp21-pure-hf-head-only/epoch_epoch=epoch=14-val_loss=val_loss=2.009.ckpt",
        "config": "configs/mobile_vla_v5_exp21_pure_hf_head_only.json",
    },
    {
        "name": "exp22_pure_hf_lora",
        "exp_dir": "runs/v5_nav/kosmos/mobile_vla_v5_exp22",
        "config": "configs/mobile_vla_v5_exp22_pure_hf_lora.json",
    },
    {
        "name": "exp23_pure_hf_both",
        "exp_dir": "runs/v5_nav/kosmos/mobile_vla_v5_exp23",
        "config": "configs/mobile_vla_v5_exp23_pure_hf_both.json",
    },
]


# ── 유틸 ──────────────────────────────────────────────────────────────────────

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
    pil = Image.fromarray(img_array.astype(np.uint8)).resize((224, 224))
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


def resolve_ckpt_path(ckpt_info):
    ckpt = ckpt_info.get("ckpt")
    if ckpt:
        ckpt_full = ROOT / ckpt
        return ckpt if ckpt_full.exists() else None

    exp_dir = ckpt_info.get("exp_dir")
    if not exp_dir:
        return None
    exp_root = ROOT / exp_dir
    if not exp_root.exists():
        return None

    candidates = sorted(exp_root.glob("**/epoch*.ckpt"))
    if not candidates:
        candidates = sorted(exp_root.glob("**/last*.ckpt"))
    if not candidates:
        return None
    best = max(candidates, key=lambda p: p.stat().st_mtime)
    return str(best.relative_to(ROOT))

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
                cls_idx = action_to_label(action)
                return action, cls_idx
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(1)

def wait_server_ready(timeout=500):
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
    env = os.environ.copy()
    env["VLA_CHECKPOINT_PATH"] = str(ROOT / ckpt_path)
    env["VLA_CONFIG_PATH"]     = str(ROOT / config_path)
    env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    env["VLA_USE_QUANT"] = "false"
    env["VLA_PORT"] = "8001"
    env["VLA_API_KEY"] = API_KEY

    python_exec = OPENVLA_PYTHON if os.path.exists(OPENVLA_PYTHON) else sys.executable
    cmd = [python_exec, str(ROOT / "robovlm_nav/serve/inference_server.py"), "--port", "8001"]
    proc = subprocess.Popen(
        cmd, cwd=str(ROOT), env=env,
        stdout=open("/tmp/infer_server_text_test.log", "w"),
        stderr=subprocess.STDOUT,
    )
    return proc

def stop_server(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    time.sleep(3)

def get_test_frame():
    """neutral 테스트 프레임: left_path val 에피소드 첫 프레임.
    Exp07은 straight_path 제외하고 left/right만 학습.
    첫 프레임은 아직 이동 전 → 바구니가 비교적 중앙에 가까움.
    left vs right instruction에 따라 다른 action이 나와야 텍스트 이해 확인 가능.
    """
    import h5py
    left_eps = sorted(V5_DATA.glob("episode_*left_path*.h5"))
    # stratified val: 마지막 20%
    split = int(len(left_eps) * 0.8)
    val_ep = left_eps[split]  # val 첫 번째
    with h5py.File(val_ep, 'r') as f:
        images = f['observations']['images'][:]
        raw_inst = f['language_instruction'][0]
        instruction_orig = raw_inst.decode() if isinstance(raw_inst, bytes) else str(raw_inst)
    # 첫 프레임 (이동 시작 전, 바구니 중앙 근처)
    return images[0], instruction_orig, val_ep.name


# ── 테스트 A: inference_server 기반 ──────────────────────────────────────────

def test_server_text_sensitivity(ckpt_info, test_img, orig_instruction):
    name   = ckpt_info["name"]
    config = ckpt_info["config"]
    ckpt   = resolve_ckpt_path(ckpt_info)

    if not ckpt:
        print(f"  ⚠️  체크포인트 없음, 스킵: {name}")
        return None
    ckpt_full = ROOT / ckpt

    print(f"\n{'='*60}")
    print(f"🔬 {name}")
    print(f"{'='*60}")

    proc = start_infer_server(ckpt, config)
    if not wait_server_ready(timeout=500):
        print("  ❌ 서버 시작 실패, 스킵")
        stop_server(proc)
        return None

    b64 = img_to_b64(test_img)
    results = {}

    # 원본 instruction도 포함
    all_instructions = {"[ORIGINAL]": orig_instruction}
    all_instructions.update(INSTRUCTIONS)

    print(f"\n  {'Instruction':12s}  {'action':22s}  class")
    print(f"  {'-'*55}")
    for key, instr in all_instructions.items():
        try:
            # reset=True로 매번 히스토리 초기화
            action, cls_idx = api_call(b64, instr, reset=True)
            cls_name = CLASS_NAMES.get(cls_idx, '?')
            print(f"  {key:12s}  {str([round(v,3) for v in action]):22s}  {cls_name}")
            results[key] = {"instruction": instr, "action": action, "class": cls_name, "class_idx": cls_idx}
        except Exception as e:
            print(f"  {key:12s}  ERROR: {e}")
            results[key] = {"instruction": instr, "error": str(e)}

    # left vs right 차이 (left_1 vs right_1 기준)
    if "left_1" in results and "right_1" in results and "error" not in results["left_1"] and "error" not in results["right_1"]:
        al = np.array(results["left_1"]["action"])
        ar = np.array(results["right_1"]["action"])
        diff = float(np.linalg.norm(al - ar))
        same = results["left_1"]["class"] == results["right_1"]["class"]
        print(f"\n  📊 left vs right 차이: {diff:.4f}  {'❌ 동일 클래스 (텍스트 무시)' if same else '✅ 다른 클래스 (텍스트 이해!)'}")
        results["_left_right_diff"] = diff
        results["_left_right_same_class"] = same

    stop_server(proc)
    return {"name": name, "results": results}


# ── 테스트 B: Raw Kosmos-2 hidden state ──────────────────────────────────────

def test_raw_kosmos_hidden_state(test_img):
    print(f"\n{'='*60}")
    print("🔬 Raw Kosmos-2 (pretrained, no LoRA) — hidden state 비교")
    print(f"{'='*60}")

    import torch
    from transformers import AutoProcessor, AutoModelForVision2Seq

    MODEL_PATH = str(ROOT / ".vlms/kosmos-2-patch14-224")
    if not Path(MODEL_PATH).exists():
        print("  ⚠️  .vlms/kosmos-2-patch14-224 없음, 스킵")
        return None

    print("  모델 로딩 중...")
    processor = AutoProcessor.from_pretrained(MODEL_PATH)
    model = AutoModelForVision2Seq.from_pretrained(
        MODEL_PATH, torch_dtype=torch.float16
    ).cuda().eval()
    print("  ✅ 로드 완료")

    pil_img = Image.fromarray(test_img.astype(np.uint8))
    hiddens = {}

    for key, instr in INSTRUCTIONS.items():
        prompt = f"<grounding>{instr}"
        inputs = processor(text=prompt, images=pil_img, return_tensors="pt")
        inputs = {k: v.cuda() for k, v in inputs.items()}
        with torch.no_grad():
            out = model(
                **inputs,
                output_hidden_states=True,
            )
            # last hidden state, last token
            h = out.hidden_states[-1][0, -1, :].float().cpu().numpy()
        hiddens[key] = h

    print(f"\n  {'비교':20s}  L2 거리")
    print(f"  {'-'*35}")
    pairs = [
        ("left", "right"),
        ("left", "forward"),
        ("left", "stop"),
        ("turn_l", "turn_r"),
        ("forward", "stop"),
    ]
    dists = {}
    for a, b in pairs:
        d = float(np.linalg.norm(hiddens[a] - hiddens[b]))
        dists[f"{a}_vs_{b}"] = d
        verdict = "✅ 구분됨" if d > 1.0 else ("△ 약간" if d > 0.1 else "❌ 거의 동일")
        print(f"  {a:8s} vs {b:8s}  {d:8.4f}  {verdict}")

    del model
    torch.cuda.empty_cache()
    return {"name": "raw_kosmos2", "hidden_state_dists": dists}


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    import h5py  # noqa: ensure h5py available

    print("📋 V5 VLM 텍스트 이해 테스트")
    print("   동일 이미지 + 다른 instruction → action 차이 확인\n")

    test_img, orig_instruction, ep_name = get_test_frame()
    print(f"📸 테스트 이미지: {ep_name[:60]}")
    print(f"   원본 instruction: {orig_instruction}")

    all_results = []

    # 테스트 B: Raw Kosmos-2 (--skip-raw 인자로 스킵 가능)
    if "--skip-raw" not in sys.argv:
        raw_result = test_raw_kosmos_hidden_state(test_img)
        if raw_result:
            all_results.append(raw_result)
        time.sleep(3)
    else:
        print("  [Raw Kosmos-2 스킵]")

    # --extra-ckpt / --extra-config / --extra-name 인자로 동적 추가
    checkpoints = list(CHECKPOINTS)
    if "--extra-ckpt" in sys.argv:
        idx = sys.argv.index("--extra-ckpt")
        extra_ckpt = sys.argv[idx + 1]
        extra_config = sys.argv[sys.argv.index("--extra-config") + 1] if "--extra-config" in sys.argv else "configs/mobile_vla_v5_exp01_discrete.json"
        extra_name = sys.argv[sys.argv.index("--extra-name") + 1] if "--extra-name" in sys.argv else "extra"
        checkpoints.append({"name": extra_name, "ckpt": extra_ckpt, "config": extra_config})

    # 테스트 A: 각 체크포인트
    for ckpt_info in checkpoints:
        result = test_server_text_sensitivity(ckpt_info, test_img, orig_instruction)
        if result:
            all_results.append(result)
        time.sleep(5)

    # 최종 요약
    print(f"\n{'='*60}")
    print("📋 최종 요약")
    print(f"{'='*60}")
    for r in all_results:
        if r["name"] == "raw_kosmos2":
            d = r["hidden_state_dists"]
            print(f"\n[Raw Kosmos-2] left vs right L2: {d.get('left_vs_right', 0):.4f}")
        else:
            res = r.get("results", {})
            diff = res.get("_left_right_diff", "N/A")
            same = res.get("_left_right_same_class", None)
            verdict = "❌ 텍스트 무시" if same else "✅ 텍스트 이해"
            diff_str = f"{diff:.4f}" if isinstance(diff, float) else str(diff)
        print(f"\n[{r['name']}] left vs right: diff={diff_str}  {verdict}")

    LOG_OUT.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\n💾 저장: {LOG_OUT}")


if __name__ == "__main__":
    main()

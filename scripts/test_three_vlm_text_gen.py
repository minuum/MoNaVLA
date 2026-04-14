#!/usr/bin/env python3
"""
세 VLM 텍스트 생성 능력 비교 테스트

목적: 왜 fine-tuned 모델에서 "Ring Ring Ring..." 출력이 나오는지 확인.
     동일 이미지 + 동일 프롬프트를 세 모델에 입력하고 생성 결과를 나란히 비교.

모델 3종:
  1. Pure HF Kosmos-2        : microsoft/kosmos-2-patch14-224 원본 HF 가중치
  2. Google-robot pretrained : kosmos_ph_google-robot-post-train.pt (navigation pre-train)
  3. V4 LoRA fine-tuned      : mobile_vla_v4_regression_v2 (action prediction 학습)

Usage:
  python3 scripts/test_three_vlm_text_gen.py
  python3 scripts/test_three_vlm_text_gen.py --episode <h5_path>  # 특정 에피소드 사용
"""

import sys
import argparse
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "third_party" / "RoboVLMs"))

import torch
import numpy as np
from PIL import Image
from transformers import AutoProcessor, AutoModelForVision2Seq

# ─── 경로 설정 ────────────────────────────────────────────────────────────────

HF_KOSMOS_PATH = ROOT / ".vlms" / "kosmos-2-patch14-224"
GOOGLE_ROBOT_PT = ROOT / ".vlms" / "google_robot_pretrain" / "kosmos_ph_google-robot-post-train.pt"
V4_CKPT = ROOT / "runs" / "v4_nav" / "kosmos" / "mobile_vla_v4_regression_v2" / "2026-03-26" / "v4-regression-v2-weighted-v2" / "last.ckpt"

# 테스트용 프롬프트들
PROMPTS = [
    "<grounding>The gray basket is at",
    "<grounding>An image of a robot. Where is the gray basket? Answer:",
    "<grounding>Navigate toward the gray basket until it gets closer",
    "What do you see in this image?",
]

MAX_NEW_TOKENS = 64

# ─── 이미지 로드 ──────────────────────────────────────────────────────────────

def load_test_image(episode_path: str = None) -> tuple[np.ndarray, str]:
    """테스트 이미지 로드. episode_path가 없으면 v5 데이터셋에서 자동 선택."""
    import h5py

    if episode_path:
        h5_path = Path(episode_path)
    else:
        # v5 데이터셋에서 left_path 에피소드 자동 선택
        v5_dir = ROOT / "ROS_action" / "v5_data_bak" / "mobile_vla_dataset_v5"
        candidates = sorted(v5_dir.glob("episode_*left_path*.h5"))
        if not candidates:
            candidates = sorted(v5_dir.glob("episode_*.h5"))
        if not candidates:
            raise FileNotFoundError(f"V5 데이터셋 없음: {v5_dir}")
        h5_path = candidates[0]

    with h5py.File(h5_path, "r") as f:
        if "observations" in f:
            images = f["observations"]["images"][:]
        else:
            images = f["images"][:]
        mid = len(images) // 2
        img = images[mid]

    print(f"  이미지 소스: {h5_path.name}")
    print(f"  프레임 인덱스: {mid} / {len(images)}")
    return img, str(h5_path)


def np_to_pil(img_array: np.ndarray) -> Image.Image:
    return Image.fromarray(img_array.astype(np.uint8)).convert("RGB")


# ─── 공통 생성 함수 ───────────────────────────────────────────────────────────

def run_generate(model, processor, pil_img: Image.Image, prompt: str) -> dict:
    """
    model: AutoModelForVision2Seq
    processor: AutoProcessor
    pil_img: PIL Image
    prompt: str

    반환: {
        "input_ids_len": int,
        "generated_text": str,
        "generated_ids_raw": list[int],
        "error": str | None
    }
    """
    try:
        inputs = processor(text=prompt, images=pil_img, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        input_len = inputs["input_ids"].shape[-1]

        with torch.no_grad():
            generated_ids = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
            )

        # 입력 토큰 제외, 새로 생성된 부분만
        new_ids = generated_ids[0, input_len:]
        generated_text = processor.tokenizer.decode(new_ids, skip_special_tokens=False)

        return {
            "input_ids_len": input_len,
            "generated_text": generated_text,
            "generated_ids_raw": new_ids.tolist()[:30],  # 앞 30개 토큰 ID
            "error": None,
        }
    except Exception as e:
        return {
            "input_ids_len": -1,
            "generated_text": "",
            "generated_ids_raw": [],
            "error": str(e),
        }


# ─── Model 1: Pure HF Kosmos-2 ────────────────────────────────────────────────

def test_pure_hf(pil_img: Image.Image, prompts: list[str]) -> dict:
    print("\n" + "="*60)
    print("🔵 Model 1: Pure HF Kosmos-2 (microsoft/kosmos-2-patch14-224)")
    print("="*60)

    if not HF_KOSMOS_PATH.exists():
        print(f"  ❌ 경로 없음: {HF_KOSMOS_PATH}")
        return {"name": "pure_hf", "status": "path_missing", "results": {}}

    print(f"  로드 중: {HF_KOSMOS_PATH}")
    processor = AutoProcessor.from_pretrained(str(HF_KOSMOS_PATH))
    model = AutoModelForVision2Seq.from_pretrained(
        str(HF_KOSMOS_PATH),
        torch_dtype=torch.float16,
    ).cuda().eval()
    print(f"  ✅ 로드 완료 (dtype: {next(model.parameters()).dtype})")

    results = {}
    for prompt in prompts:
        r = run_generate(model, processor, pil_img, prompt)
        results[prompt] = r
        status = "✅" if not r["error"] else "❌"
        text_preview = r["generated_text"][:80].replace("\n", " ")
        print(f"\n  프롬프트: {prompt[:60]}")
        print(f"  {status} 생성: '{text_preview}'")
        if r["error"]:
            print(f"     오류: {r['error']}")

    del model
    torch.cuda.empty_cache()
    return {"name": "pure_hf", "status": "ok", "results": results}


# ─── Model 2: Google-robot pretrained ────────────────────────────────────────

def test_google_robot(pil_img: Image.Image, prompts: list[str]) -> dict:
    print("\n" + "="*60)
    print("🟡 Model 2: Google-robot pretrained (kosmos_ph_google-robot-post-train.pt)")
    print("="*60)

    if not GOOGLE_ROBOT_PT.exists():
        print(f"  ❌ 경로 없음: {GOOGLE_ROBOT_PT}")
        return {"name": "google_robot", "status": "path_missing", "results": {}}

    if not HF_KOSMOS_PATH.exists():
        print(f"  ❌ HF 베이스 경로 없음: {HF_KOSMOS_PATH}")
        return {"name": "google_robot", "status": "path_missing", "results": {}}

    print(f"  베이스 아키텍처: {HF_KOSMOS_PATH}")
    print(f"  가중치: {GOOGLE_ROBOT_PT.name}")

    # 아키텍처는 HF Kosmos-2와 동일, 가중치만 교체
    processor = AutoProcessor.from_pretrained(str(HF_KOSMOS_PATH))
    model = AutoModelForVision2Seq.from_pretrained(
        str(HF_KOSMOS_PATH),
        torch_dtype=torch.float16,
    ).cuda().eval()

    # Google-robot 가중치 로드
    print(f"  Google-robot 가중치 로딩...")
    ckpt = torch.load(str(GOOGLE_ROBOT_PT), map_location="cpu", weights_only=False)

    # Google-robot 체크포인트 키 구조 (DeepSpeed + Lightning 포맷):
    #   ckpt['state_dict']['model.backbone.text_model.model.embed_tokens.weight']
    #   ckpt['state_dict']['model.backbone.image_to_text_projection.dense.weight']
    #
    # HF Kosmos2ForConditionalGeneration state_dict 키:
    #   text_model.model.embed_tokens.weight
    #   image_to_text_projection.dense.weight
    #
    # → ckpt['state_dict']에서 "model.backbone." 접두사를 제거하면 매핑됨
    state_dict = ckpt["state_dict"]  # Lightning checkpoint

    sd_keys = list(state_dict.keys())
    print(f"  state_dict 키 수: {len(sd_keys)}, 첫 5개: {sd_keys[:5]}")

    prefix = "model.backbone."
    kosmos_sd = {}
    for k, v in state_dict.items():
        if not k.startswith(prefix):
            continue
        new_k = k[len(prefix):]
        if isinstance(v, torch.Tensor):
            kosmos_sd[new_k] = v.half()

    print(f"  매핑된 키 수: {len(kosmos_sd)}")
    if kosmos_sd:
        print(f"  매핑 예시: {list(kosmos_sd.keys())[:3]}")

    missing, unexpected = model.load_state_dict(kosmos_sd, strict=False)
    print(f"  로드 결과 — missing: {len(missing)}, unexpected: {len(unexpected)}")
    if missing[:3]:
        print(f"    missing 예시: {missing[:3]}")
    if unexpected[:3]:
        print(f"    unexpected 예시: {unexpected[:3]}")

    print(f"  ✅ 가중치 적용 완료")

    results = {}
    for prompt in prompts:
        r = run_generate(model, processor, pil_img, prompt)
        results[prompt] = r
        status = "✅" if not r["error"] else "❌"
        text_preview = r["generated_text"][:80].replace("\n", " ")
        print(f"\n  프롬프트: {prompt[:60]}")
        print(f"  {status} 생성: '{text_preview}'")
        if r["error"]:
            print(f"     오류: {r['error']}")

    del model
    torch.cuda.empty_cache()
    return {"name": "google_robot", "status": "ok", "results": results}


# ─── Model 3: V4 LoRA fine-tuned ─────────────────────────────────────────────

def test_v4_lora(pil_img: Image.Image, prompts: list[str]) -> dict:
    print("\n" + "="*60)
    print("🔴 Model 3: V4 LoRA fine-tuned (mobile_vla_v4_regression_v2)")
    print("="*60)

    if not V4_CKPT.exists():
        # 대안 경로 탐색
        alt = sorted((ROOT / "runs" / "v4_nav" / "kosmos").rglob("last.ckpt"))
        if alt:
            v4_path = alt[-1]
            print(f"  대안 체크포인트 사용: {v4_path}")
        else:
            print(f"  ❌ V4 체크포인트 없음: {V4_CKPT}")
            return {"name": "v4_lora", "status": "path_missing", "results": {}}
    else:
        v4_path = V4_CKPT

    if not HF_KOSMOS_PATH.exists():
        print(f"  ❌ HF 베이스 경로 없음: {HF_KOSMOS_PATH}")
        return {"name": "v4_lora", "status": "path_missing", "results": {}}

    print(f"  체크포인트: {v4_path}")

    # 아키텍처는 HF Kosmos-2, V4 가중치 덮어씌우기
    processor = AutoProcessor.from_pretrained(str(HF_KOSMOS_PATH))
    model = AutoModelForVision2Seq.from_pretrained(
        str(HF_KOSMOS_PATH),
        torch_dtype=torch.float16,
    ).cuda().eval()

    print(f"  V4 LoRA 체크포인트 로딩...")
    ckpt = torch.load(str(v4_path), map_location="cpu", weights_only=False)

    if isinstance(ckpt, dict):
        keys = list(ckpt.keys())[:5]
        print(f"  체크포인트 최상위 키: {keys}")
        state_dict = ckpt.get("state_dict", ckpt.get("model_state_dict", ckpt))
    else:
        state_dict = ckpt

    sd_keys = list(state_dict.keys())
    print(f"  state_dict 키 수: {len(sd_keys)}, 첫 5개: {sd_keys[:5]}")

    # V4 체크포인트 키 구조:
    #   model.backbone.base_model.model.text_model.model.layers.0.self_attn.k_proj.base_layer.weight
    #   model.backbone.base_model.model.image_to_text_projection.dense.base_layer.weight
    #   model.backbone.base_model.model.image_to_text_projection.latent_query
    #
    # HF AutoModelForVision2Seq의 model 키 구조:
    #   text_model.model.layers.0.self_attn.k_proj.weight
    #   image_to_text_projection.dense.weight
    #
    # → "model.backbone.base_model.model." 접두사를 제거하고,
    #   LoRA base_layer (실제 가중치) 만 추출, lora_A/lora_B는 건너뜀
    kosmos_sd = {}
    prefix = "model.backbone.base_model.model."
    for k, v in state_dict.items():
        if not k.startswith(prefix):
            continue
        new_k = k[len(prefix):]
        # LoRA 구조: k_proj.base_layer.weight → k_proj.weight 로 변환
        # lora_A, lora_B는 스킵 (HF 원본에 없음)
        if ".lora_A." in new_k or ".lora_B." in new_k:
            continue
        new_k = new_k.replace(".base_layer.", ".")
        kosmos_sd[new_k] = v

    print(f"  매핑된 키 수: {len(kosmos_sd)}")
    if kosmos_sd:
        print(f"  매핑 예시: {list(kosmos_sd.keys())[:3]}")

    missing, unexpected = model.load_state_dict(kosmos_sd, strict=False)
    print(f"  로드 결과 — missing: {len(missing)}, unexpected: {len(unexpected)}")
    if missing[:3]:
        print(f"    missing 예시: {missing[:3]}")
    if unexpected[:3]:
        print(f"    unexpected 예시: {unexpected[:3]}")
    print(f"  ✅ 가중치 적용 완료")

    results = {}
    for prompt in prompts:
        r = run_generate(model, processor, pil_img, prompt)
        results[prompt] = r
        status = "✅" if not r["error"] else "❌"
        text_preview = r["generated_text"][:80].replace("\n", " ")
        print(f"\n  프롬프트: {prompt[:60]}")
        print(f"  {status} 생성: '{text_preview}'")
        if r["error"]:
            print(f"     오류: {r['error']}")

    del model
    torch.cuda.empty_cache()
    return {"name": "v4_lora", "status": "ok", "results": results}


# ─── 결과 요약 출력 ───────────────────────────────────────────────────────────

def print_summary(all_results: list[dict], prompts: list[str]):
    print("\n" + "="*70)
    print("📋 결과 요약 — 동일 프롬프트에 대한 세 모델 생성 비교")
    print("="*70)

    model_names = {"pure_hf": "Pure HF", "google_robot": "Google-robot", "v4_lora": "V4 LoRA"}

    for prompt in prompts:
        print(f"\n▶ 프롬프트: '{prompt[:70]}'")
        print(f"  {'-'*65}")
        for r in all_results:
            name = model_names.get(r["name"], r["name"])
            if r["status"] != "ok":
                print(f"  [{name:14s}]  ❌ 로드 실패")
                continue
            res = r["results"].get(prompt, {})
            if res.get("error"):
                print(f"  [{name:14s}]  ❌ 오류: {res['error'][:60]}")
            else:
                text = res.get("generated_text", "")
                # Ring/반복 패턴 감지
                words = text.split()
                is_repetitive = len(words) > 4 and len(set(words[:10])) <= 3
                tag = " ⚠️ REPETITIVE" if is_repetitive else ""
                print(f"  [{name:14s}]  '{text[:70]}'{tag}")


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", type=str, default=None,
                        help="특정 H5 에피소드 경로 (없으면 자동 선택)")
    parser.add_argument("--skip-google", action="store_true",
                        help="Google-robot 모델 스킵")
    parser.add_argument("--skip-v4", action="store_true",
                        help="V4 LoRA 모델 스킵")
    parser.add_argument("--skip-hf", action="store_true",
                        help="Pure HF 모델 스킵")
    parser.add_argument("--output", type=str, default="/tmp/three_vlm_text_gen_result.json",
                        help="결과 저장 경로")
    args = parser.parse_args()

    print("="*60)
    print("🔬 세 VLM 텍스트 생성 능력 비교 테스트")
    print("="*60)

    # 이미지 로드
    print("\n📸 테스트 이미지 로드 중...")
    img_array, src_path = load_test_image(args.episode)
    pil_img = np_to_pil(img_array)
    pil_img.save("/tmp/test_vlm_image.jpg")
    print(f"  이미지 저장: /tmp/test_vlm_image.jpg")

    all_results = []

    if not args.skip_hf:
        r1 = test_pure_hf(pil_img, PROMPTS)
        all_results.append(r1)

    if not args.skip_google:
        r2 = test_google_robot(pil_img, PROMPTS)
        all_results.append(r2)

    if not args.skip_v4:
        r3 = test_v4_lora(pil_img, PROMPTS)
        all_results.append(r3)

    print_summary(all_results, PROMPTS)

    # JSON 저장
    output_path = Path(args.output)
    output_path.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\n💾 전체 결과 저장: {output_path}")


if __name__ == "__main__":
    main()

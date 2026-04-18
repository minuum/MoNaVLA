#!/usr/bin/env python3
"""
Pure HF Kosmos-2 (학습 안 한 백본)로 V5 9개 path_type 에피소드의 첫 프레임을
추론하고 이미지 + 생성 텍스트를 HTML로 비교.

목적: 학습 전 모델이 이미지에서 좌/우/직진 방향을 텍스트로 구별할 수
있는지 확인. 우리 학습 이전에 이미 구별 능력이 없다면 → foundation 한계.
학습 전에는 구별됐는데 학습 후 안 되면 → 우리 학습이 망친 것.

Usage:
  python3 scripts/compare_pure_kosmos_9paths.py
"""

import sys
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch
import numpy as np
from PIL import Image
from transformers import AutoProcessor, AutoModelForVision2Seq
import h5py

HF_KOSMOS_PATH = ROOT / ".vlms" / "kosmos-2-patch14-224"
DATA_DIR = ROOT / "ROS_action" / "mobile_vla_dataset_v5"
OUT_DIR = ROOT / "docs" / "v5" / "pure_backbone_9paths"
OUT_DIR.mkdir(parents=True, exist_ok=True)
IMG_DIR = OUT_DIR / "images"
IMG_DIR.mkdir(exist_ok=True)

PATH_TYPES = [
    "center_straight", "center_left", "center_right",
    "left_straight",   "left_left",   "left_right",
    "right_straight",  "right_left",  "right_right",
]

PROMPTS = [
    ("grounding", "<grounding>The gray basket is at"),
    ("side", "<grounding>The basket is on the"),
    ("intent", "<grounding>To reach the basket, the robot should"),
]

MAX_NEW_TOKENS = 40


def pick_episode(path_type: str) -> Path | None:
    candidates = sorted(DATA_DIR.glob(f"episode_*target_{path_type}_path*.h5"))
    return candidates[0] if candidates else None


def load_first_frame(h5_path: Path) -> np.ndarray:
    with h5py.File(h5_path, "r") as f:
        if "observations" in f and "images" in f["observations"]:
            return f["observations"]["images"][0]
        return f["images"][0]


def run_generate(model, processor, pil_img: Image.Image, prompt: str) -> str:
    inputs = processor(text=prompt, images=pil_img, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    input_len = inputs["input_ids"].shape[-1]
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
        )
    new_ids = generated_ids[0, input_len:]
    text = processor.tokenizer.decode(new_ids, skip_special_tokens=True)
    return text.strip()


def main():
    print(f"Loading pure HF Kosmos-2 from {HF_KOSMOS_PATH}")
    processor = AutoProcessor.from_pretrained(str(HF_KOSMOS_PATH))
    model = AutoModelForVision2Seq.from_pretrained(
        str(HF_KOSMOS_PATH), torch_dtype=torch.float16,
    ).cuda().eval()
    print(f"Loaded (dtype={next(model.parameters()).dtype})")

    results = []
    for pt in PATH_TYPES:
        ep = pick_episode(pt)
        if ep is None:
            print(f"[SKIP] {pt}: no episode")
            continue
        print(f"\n=== {pt} ===")
        print(f"  episode: {ep.name}")
        frame = load_first_frame(ep)
        pil = Image.fromarray(frame.astype(np.uint8)).convert("RGB")
        img_file = IMG_DIR / f"{pt}.jpg"
        pil.resize((640, 360)).save(img_file, quality=85)

        prompt_results = {}
        for tag, prompt in PROMPTS:
            text = run_generate(model, processor, pil, prompt)
            prompt_results[tag] = {"prompt": prompt, "generated": text}
            print(f"  [{tag}] {prompt}")
            print(f"    → {text[:100]}")

        results.append({
            "path_type": pt,
            "episode": ep.name,
            "image": f"images/{pt}.jpg",
            "prompts": prompt_results,
        })

    (OUT_DIR / "results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False)
    )

    build_html(results)
    print(f"\n✅ Done. Output: {OUT_DIR / 'index.html'}")


def build_html(results):
    rows = []
    for r in results:
        pt = r["path_type"]
        img = r["image"]
        cells = []
        for tag, _prompt in PROMPTS:
            entry = r["prompts"].get(tag, {})
            gen = entry.get("generated", "")
            cells.append(f"""
              <div class="prompt-cell">
                <div class="tag-label">{tag}</div>
                <div class="prompt-text">{entry.get('prompt','')}</div>
                <div class="generated-text">{gen if gen else '<em>(empty)</em>'}</div>
              </div>""")
        rows.append(f"""
          <div class="path-row">
            <div class="path-header"><strong>{pt}</strong> <span class="ep">({r['episode']})</span></div>
            <div class="path-body">
              <div class="img-wrap"><img src="{img}" alt="{pt}"></div>
              <div class="prompts-wrap">{''.join(cells)}</div>
            </div>
          </div>""")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Pure Kosmos-2 on 9 Path Types</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 24px; background: #f8fafc; color: #1e293b; }}
  h1 {{ font-size: 1.8rem; margin-bottom: 8px; }}
  .subtitle {{ color: #64748b; margin-bottom: 24px; max-width: 800px; line-height: 1.6; }}
  .back-link {{ display: inline-block; margin-bottom: 16px; color: #3b82f6; text-decoration: none; }}
  .back-link:hover {{ text-decoration: underline; }}
  .path-row {{ background: white; border: 1px solid #e2e8f0; border-radius: 12px; margin-bottom: 20px; overflow: hidden; }}
  .path-header {{ padding: 12px 16px; background: #1e293b; color: white; font-size: 1.05rem; }}
  .path-header .ep {{ color: #94a3b8; font-size: 0.8rem; margin-left: 8px; }}
  .path-body {{ display: grid; grid-template-columns: 320px 1fr; gap: 16px; padding: 16px; }}
  .img-wrap img {{ width: 100%; border-radius: 8px; }}
  .prompts-wrap {{ display: flex; flex-direction: column; gap: 10px; }}
  .prompt-cell {{ border-left: 3px solid #3b82f6; padding: 8px 12px; background: #f1f5f9; border-radius: 4px; }}
  .tag-label {{ font-size: 0.7rem; text-transform: uppercase; color: #64748b; font-weight: 600; letter-spacing: 0.5px; }}
  .prompt-text {{ font-family: monospace; font-size: 0.85rem; color: #0f172a; margin: 4px 0; }}
  .generated-text {{ font-size: 0.95rem; color: #059669; font-weight: 500; }}
  @media (max-width: 768px) {{ .path-body {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
  <a class="back-link" href="../../index.html">← Back to main</a>
  <h1>Pure HF Kosmos-2 on V5 9 Path Types</h1>
  <p class="subtitle">
    학습 전 Kosmos-2 백본이 9가지 경로 유형 에피소드의 첫 프레임을 어떻게 인식하는지 비교.
    모든 path_type에서 응답이 비슷하면 → foundation 자체가 좌/우 구별 능력 부족.
    path_type에 따라 응답이 달라지면 → 학습 과정이 구별 능력을 망침.
  </p>
  {''.join(rows)}
</body>
</html>"""
    (OUT_DIR / "index.html").write_text(html)


if __name__ == "__main__":
    main()

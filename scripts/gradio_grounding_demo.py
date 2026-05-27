#!/usr/bin/env python3
"""
Object Recognition Demo — Kosmos-2 그라운딩 인터랙티브 테스트
웹캠 / 이미지 업로드 → bbox 오버레이 + alias 비교 + VLA 추론 연동

Port: 7863

Usage:
  python3 scripts/gradio_grounding_demo.py
  python3 scripts/gradio_grounding_demo.py --adapter exp56
  python3 scripts/gradio_grounding_demo.py --preload
"""
import argparse
import base64
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import gradio as gr
import numpy as np
import requests
import torch
from PIL import Image, ImageDraw

from scripts.run_grounding_realtime import (
    load_model,
    ground,
    draw_overlay,
    check_hit,
    DEFAULT_VLM,
    DEFAULT_ADAPTERS,
)

# ─── 모델 싱글톤 ───────────────────────────────────────────────────────────────

_state: dict = {"model": None, "processor": None, "adapter": None}
_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

ADAPTER_OPTIONS = {
    "Pure Kosmos-2": None,
    "Exp56 LoRA":    DEFAULT_ADAPTERS.get("exp56"),
}

PRESET_ALIASES = {
    "🧺 basket": "gray basket\ngray box\ncontainer\nbin\nlaundry basket",
    "🔴 ball":   "red ball\norange ball\nball\nsphere",
    "🚪 door":   "door\nexit\nentrance",
    "🏛 wall":   "white wall\ncorridor wall\nwall",
    "🛣 corridor": "corridor\nhallway\npassage",
}

GOAL_NAV_PRESETS = [
    "the gray basket on right",
    "the gray basket on left",
    "the gray basket",
    "the door",
    "the corridor on the left",
    "the corridor on the right",
]

ACTION_COLORS = {
    "FORWARD":   "#2ecc71",
    "LEFT":      "#3498db",
    "RIGHT":     "#e67e22",
    "FWD+LEFT":  "#1abc9c",
    "FWD+RIGHT": "#f39c12",
    "ROT_L":     "#9b59b6",
    "ROT_R":     "#e74c3c",
    "STOP":      "#95a5a6",
}

API_URL = "http://localhost:8001"


def _ensure_model(adapter_label: str):
    if _state["model"] is None or _state["adapter"] != adapter_label:
        adapter_path = ADAPTER_OPTIONS.get(adapter_label)
        print(f"[LOAD] {adapter_label} ...")
        model, processor = load_model(DEFAULT_VLM, adapter_path, _DEVICE)
        _state.update(model=model, processor=processor, adapter=adapter_label)
    return _state["model"], _state["processor"]


def _to_numpy(image) -> np.ndarray:
    if image is None:
        return None
    if isinstance(image, np.ndarray):
        return image
    return np.array(image.convert("RGB"))


def _img_to_b64(img_np: np.ndarray) -> str:
    pil = Image.fromarray(img_np)
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


def _draw_api_bbox(img_np: np.ndarray, bbox: dict | None, label: str) -> Image.Image:
    pil = Image.fromarray(img_np).convert("RGB")
    if not bbox:
        return pil
    draw = ImageDraw.Draw(pil)
    h, w = img_np.shape[:2]
    color = ACTION_COLORS.get(label, "#ffffff")

    if "x1" in bbox:
        x1, y1, x2, y2 = (
            int(bbox["x1"] * w), int(bbox["y1"] * h),
            int(bbox["x2"] * w), int(bbox["y2"] * h),
        )
    else:
        cx, cy = bbox.get("cx", 0.5), bbox.get("cy", 0.5)
        side = bbox.get("area", 0.1) ** 0.5
        x1, y1 = int((cx - side / 2) * w), int((cy - side / 2) * h)
        x2, y2 = int((cx + side / 2) * w), int((cy + side / 2) * h)

    draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
    draw.rectangle([x1, y1 - 20, x1 + len(label) * 9 + 8, y1], fill=color)
    draw.text((x1 + 4, y1 - 18), f"▶ {label}", fill="#000000")
    return pil


# ─── Grounding 탭 ─────────────────────────────────────────────────────────────

def run_grounding(image, phrase: str, adapter_label: str):
    if image is None:
        return None, "⚠️ 이미지를 입력해주세요", ""
    phrase = phrase.strip()
    if not phrase:
        return None, "⚠️ Phrase를 입력해주세요", ""

    model, proc = _ensure_model(adapter_label)
    img_np = _to_numpy(image)
    result = ground(model, proc, img_np, phrase, _DEVICE)
    overlay = draw_overlay(img_np, phrase, result)
    hit = check_hit(result, phrase)

    entity_lines = []
    for ent_name, ent_boxes, _ in result.get("entities", []):
        for box in ent_boxes:
            x1, y1, x2, y2 = box
            entity_lines.append(
                f"  [{ent_name}]  cx={((x1+x2)/2):.2f}  cy={((y1+y2)/2):.2f}"
                f"  area={((x2-x1)*(y2-y1)):.3f}"
            )

    status = f"{'HIT' if hit else 'MISS'}   {result.get('caption', '')}"
    return overlay, status, "\n".join(entity_lines) or "  (감지 없음)"


# ─── Alias Test 탭 ────────────────────────────────────────────────────────────

def run_alias_test(image, alias_text: str, adapter_label: str):
    if image is None:
        return None, "⚠️ 이미지를 입력해주세요"
    phrases = [p.strip() for p in alias_text.splitlines() if p.strip()]
    if not phrases:
        return None, "⚠️ Phrase를 한 줄씩 입력해주세요"

    model, proc = _ensure_model(adapter_label)
    img_np = _to_numpy(image)

    rows, overlays = [], []
    for phrase in phrases:
        r = ground(model, proc, img_np, phrase, _DEVICE)
        hit = check_hit(r, phrase)
        entities = [e for e, _, _ in r.get("entities", [])]
        rows.append((phrase, hit, entities, r.get("caption", "")[:50]))
        overlays.append(draw_overlay(img_np, phrase, r))

    cols = min(len(overlays), 3)
    n_rows = (len(overlays) + cols - 1) // cols
    W, H = overlays[0].size
    LABEL_H = 22
    grid = Image.new("RGB", (W * cols, (H + LABEL_H) * n_rows), (30, 30, 30))

    for i, (ov, (phrase, hit, _, _)) in enumerate(zip(overlays, rows)):
        r, c = divmod(i, cols)
        cell = Image.new("RGB", (W, H + LABEL_H), (30, 30, 30))
        d = ImageDraw.Draw(cell)
        label_color = (80, 200, 120) if hit else (220, 80, 80)
        d.rectangle([0, 0, W, LABEL_H], fill=(20, 20, 20))
        d.text((6, 4), f"{'HIT' if hit else 'MISS'}  {phrase}", fill=label_color)
        cell.paste(ov, (0, LABEL_H))
        grid.paste(cell, (c * W, r * (H + LABEL_H)))

    hit_count = sum(1 for _, hit, _, _ in rows if hit)
    lines = [f"Hit: {hit_count} / {len(phrases)}\n"]
    for phrase, hit, entities, caption in rows:
        ent_str = ", ".join(entities) if entities else "—"
        lines.append(f"{'HIT' if hit else 'MISS'}  {phrase:<25}  [{ent_str}]")

    return grid, "\n".join(lines)


# ─── VLA Inference 탭 ─────────────────────────────────────────────────────────

def run_vla_predict(image, instruction: str):
    if image is None:
        return None, "⚠️ 이미지를 입력해주세요", ""
    instruction = instruction.strip()
    if not instruction:
        return None, "⚠️ Instruction을 입력해주세요", ""

    img_np = _to_numpy(image)
    try:
        b64 = _img_to_b64(img_np)
        r = requests.post(
            f"{API_URL}/predict",
            json={"image": b64, "instruction": instruction},
            timeout=30,
        )
        r.raise_for_status()
        d = r.json()
    except Exception as e:
        return None, f"❌ API 오류: {e}", ""

    label = d.get("predicted_label", "?")
    out_img = _draw_api_bbox(img_np, d.get("bbox"), label)

    status = (
        f"▶  {label}\n"
        f"latency: {d['latency_ms']:.1f}ms  |  grounding: {d.get('grounding_latency_ms', 0):.1f}ms\n"
        f"goal_near: {d.get('goal_near_proxy', '?')}\n"
        f"caption: {d.get('grounding_caption', '')}"
    )

    bbox = d.get("bbox") or {}
    if "cx" in bbox:
        bbox_info = (
            f"entity: {bbox.get('entity', '?')}\n"
            f"cx={bbox['cx']:.3f}  cy={bbox['cy']:.3f}  area={bbox.get('area', 0):.3f}"
        )
    elif "x1" in bbox:
        bbox_info = (
            f"entity: {bbox.get('entity', '?')}\n"
            f"x1={bbox['x1']:.3f}  y1={bbox['y1']:.3f}  x2={bbox['x2']:.3f}  y2={bbox['y2']:.3f}"
        )
    else:
        bbox_info = "(bbox 없음)"

    return out_img, status, bbox_info


def run_vla_alias(image, alias_text: str, instruction_base: str):
    """여러 alias phrase를 instruction으로 각각 VLA predict → 액션 비교."""
    if image is None:
        return None, "⚠️ 이미지를 입력해주세요"
    phrases = [p.strip() for p in alias_text.splitlines() if p.strip()]
    if not phrases:
        return None, "⚠️ Phrase를 한 줄씩 입력해주세요"

    img_np = _to_numpy(image)

    results = []
    for phrase in phrases:
        try:
            b64 = _img_to_b64(img_np)
            r = requests.post(
                f"{API_URL}/predict",
                json={"image": b64, "instruction": phrase},
                timeout=30,
            )
            r.raise_for_status()
            d = r.json()
            label = d.get("predicted_label", "?")
            latency = d.get("latency_ms", 0)
            bbox = d.get("bbox") or {}
            cx = bbox.get("cx", "—")
            results.append((phrase, label, latency, cx))
        except Exception as e:
            results.append((phrase, f"ERR: {e}", 0, "—"))

    # 결과 그리드 이미지 (마지막 predict 결과의 bbox 오버레이)
    last_d = None
    try:
        b64 = _img_to_b64(img_np)
        r = requests.post(
            f"{API_URL}/predict",
            json={"image": b64, "instruction": phrases[-1]},
            timeout=30,
        )
        last_d = r.json()
    except Exception:
        pass

    out_img = _draw_api_bbox(img_np, (last_d or {}).get("bbox"), (last_d or {}).get("predicted_label", "?"))

    lines = ["Phrase → Action  (VLA Alias Test)\n"]
    action_counts: dict[str, int] = {}
    for phrase, label, latency, cx in results:
        action_counts[label] = action_counts.get(label, 0) + 1
        lines.append(f"{label:<12}  {phrase:<30}  cx={cx}  ({latency:.0f}ms)")

    lines.append("")
    lines.append("─── 액션 분포 ───")
    for action, cnt in sorted(action_counts.items(), key=lambda x: -x[1]):
        bar = "█" * cnt
        lines.append(f"{action:<12} {bar} {cnt}")

    return out_img, "\n".join(lines)


def reset_api_history():
    try:
        r = requests.post(f"{API_URL}/reset", timeout=5)
        return f"리셋 완료  ({r.json()})"
    except Exception as e:
        return f"오류: {e}"


# ─── UI 빌드 ──────────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Object Recognition Demo") as demo:
        gr.Markdown(
            "# Object Recognition Demo\n"
            "Kosmos-2 그라운딩 + VLA 추론 — 웹캠 / 이미지 직접 테스트"
        )

        adapter_dd = gr.Dropdown(
            choices=list(ADAPTER_OPTIONS.keys()),
            value="Pure Kosmos-2",
            label="Grounding 모델",
        )

        with gr.Tabs():

            # ── 탭 1: Grounding ──────────────────────────────────────────────
            with gr.TabItem("Grounding"):
                with gr.Row():
                    with gr.Column():
                        img_g = gr.Image(
                            sources=["webcam", "upload"],
                            type="numpy",
                            label="이미지 입력",
                        )
                        phrase_g = gr.Textbox(
                            value="gray basket",
                            label="Phrase",
                            placeholder="찾을 객체 이름 (예: gray basket, red ball)",
                        )
                        btn_g = gr.Button("Run", variant="primary")
                    with gr.Column():
                        out_img_g  = gr.Image(label="결과 (bbox 오버레이)")
                        out_status = gr.Textbox(label="Status / Caption", lines=2)
                        out_ents   = gr.Textbox(label="감지된 Entity (cx, cy, area)", lines=6)

                btn_g.click(
                    run_grounding,
                    inputs=[img_g, phrase_g, adapter_dd],
                    outputs=[out_img_g, out_status, out_ents],
                )

            # ── 탭 2: Alias Test ─────────────────────────────────────────────
            with gr.TabItem("Alias Test"):
                gr.Markdown(
                    "같은 물체를 다양한 이름으로 불렀을 때 어떤 phrase가 인식되는지 한 번에 확인"
                )
                with gr.Row():
                    with gr.Column():
                        img_a = gr.Image(
                            sources=["webcam", "upload"],
                            type="numpy",
                            label="이미지 입력",
                        )
                        gr.Markdown("**프리셋**")
                        with gr.Row():
                            preset_btns = [
                                gr.Button(label, size="sm")
                                for label in PRESET_ALIASES
                            ]
                        alias_txt = gr.Textbox(
                            value=list(PRESET_ALIASES.values())[0],
                            label="Alias 목록 (한 줄 = 1 phrase)",
                            lines=8,
                            placeholder="gray basket\ngray box\ncontainer\n...",
                        )
                        btn_a = gr.Button("Run All", variant="primary")
                    with gr.Column():
                        out_img_a   = gr.Image(label="결과 그리드")
                        out_summary = gr.Textbox(label="Hit / Miss 요약", lines=12)

                for btn, text in zip(preset_btns, PRESET_ALIASES.values()):
                    btn.click(fn=lambda t=text: t, outputs=alias_txt)

                btn_a.click(
                    run_alias_test,
                    inputs=[img_a, alias_txt, adapter_dd],
                    outputs=[out_img_a, out_summary],
                )

            # ── 탭 3: VLA Inference ──────────────────────────────────────────
            with gr.TabItem("VLA Inference"):
                gr.Markdown(
                    "이미지 → GoalNav API (`localhost:8001`) → 액션 예측\n\n"
                    "그라운딩은 서버 측(Kosmos-2)에서 자동 실행됩니다."
                )
                with gr.Row():
                    with gr.Column():
                        img_v = gr.Image(
                            sources=["webcam", "upload"],
                            type="numpy",
                            label="이미지 입력",
                        )
                        instr_dd = gr.Dropdown(
                            choices=GOAL_NAV_PRESETS,
                            value=GOAL_NAV_PRESETS[0],
                            label="Instruction 프리셋",
                            allow_custom_value=True,
                        )
                        instr_txt = gr.Textbox(
                            value=GOAL_NAV_PRESETS[0],
                            label="Instruction (직접 입력)",
                            placeholder="the gray basket on right",
                        )
                        instr_dd.change(fn=lambda x: x, inputs=instr_dd, outputs=instr_txt)

                        with gr.Row():
                            btn_v     = gr.Button("Run VLA", variant="primary", scale=3)
                            reset_btn = gr.Button("↺ Reset History", scale=1)

                    with gr.Column():
                        out_img_v    = gr.Image(label="결과 (bbox 오버레이)")
                        out_status_v = gr.Textbox(label="Action / Status", lines=5)
                        out_bbox_v   = gr.Textbox(label="Bbox 정보", lines=3)

                reset_out = gr.Textbox(label="리셋 결과", lines=1, visible=False)
                reset_btn.click(reset_api_history, outputs=reset_out)
                btn_v.click(
                    run_vla_predict,
                    inputs=[img_v, instr_txt],
                    outputs=[out_img_v, out_status_v, out_bbox_v],
                )

            # ── 탭 4: VLA Alias Test ─────────────────────────────────────────
            with gr.TabItem("VLA Alias Test"):
                gr.Markdown(
                    "여러 instruction phrase를 VLA API에 각각 던져서 **어떤 말이 어떤 액션**을 내는지 비교"
                )
                with gr.Row():
                    with gr.Column():
                        img_va = gr.Image(
                            sources=["webcam", "upload"],
                            type="numpy",
                            label="이미지 입력",
                        )
                        gr.Markdown("**프리셋**")
                        with gr.Row():
                            vpreset_btns = [
                                gr.Button(label, size="sm")
                                for label in PRESET_ALIASES
                            ]
                        alias_txt_v = gr.Textbox(
                            value=list(PRESET_ALIASES.values())[0],
                            label="Instruction 목록 (한 줄 = 1개)",
                            lines=8,
                        )
                        btn_va = gr.Button("Run All VLA", variant="primary")
                    with gr.Column():
                        out_img_va  = gr.Image(label="마지막 Bbox 오버레이")
                        out_sum_va  = gr.Textbox(label="Phrase → Action 매핑", lines=16)

                for btn, text in zip(vpreset_btns, PRESET_ALIASES.values()):
                    btn.click(fn=lambda t=text: t, outputs=alias_txt_v)

                btn_va.click(
                    run_vla_alias,
                    inputs=[img_va, alias_txt_v, alias_txt_v],
                    outputs=[out_img_va, out_sum_va],
                )

    return demo


# ─── 진입점 ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Object Recognition Grounding Demo")
    parser.add_argument("--adapter", default="",
                        help="exp56 → Exp56 LoRA 로드. 비워두면 Pure Kosmos-2")
    parser.add_argument("--port", type=int, default=7863)
    parser.add_argument("--share", action="store_true", help="Gradio public link")
    parser.add_argument("--preload", action="store_true",
                        help="시작 시 모델 즉시 로드 (첫 요청 지연 방지)")
    args = parser.parse_args()

    if args.preload or args.adapter:
        adapter_key = "Exp56 LoRA" if args.adapter == "exp56" else "Pure Kosmos-2"
        print(f"[PRE-LOAD] {adapter_key}")
        _ensure_model(adapter_key)

    demo = build_ui()
    print(f"[START] http://0.0.0.0:{args.port}")
    demo.launch(
        server_name="0.0.0.0",
        server_port=args.port,
        share=args.share,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()

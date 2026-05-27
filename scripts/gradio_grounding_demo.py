#!/usr/bin/env python3
"""
Object Recognition Demo — Kosmos-2 그라운딩 인터랙티브 테스트
웹캠 / 이미지 업로드 → bbox 오버레이 + alias 비교

Port: 7863

Usage:
  python3 scripts/gradio_grounding_demo.py
  python3 scripts/gradio_grounding_demo.py --adapter exp56
  python3 scripts/gradio_grounding_demo.py --preload
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import gradio as gr
import numpy as np
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

    # 그리드 (최대 3열)
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


# ─── UI 빌드 ──────────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Object Recognition Demo") as demo:
        gr.Markdown(
            "# Object Recognition Demo\n"
            "Kosmos-2 그라운딩 — 웹캠 / 이미지 업로드 직접 테스트"
        )

        adapter_dd = gr.Dropdown(
            choices=list(ADAPTER_OPTIONS.keys()),
            value="Pure Kosmos-2",
            label="Model",
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

                # 프리셋 버튼 연결 (closure 버그 방지 — default arg 활용)
                for btn, text in zip(preset_btns, PRESET_ALIASES.values()):
                    btn.click(fn=lambda t=text: t, outputs=alias_txt)

                btn_a.click(
                    run_alias_test,
                    inputs=[img_a, alias_txt, adapter_dd],
                    outputs=[out_img_a, out_summary],
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

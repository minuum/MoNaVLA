#!/usr/bin/env python3
"""
Run pure Kosmos-2 grounding on the fixed 18-frame initial review slice and
emit a self-contained visual report without touching shared grounding caches.

Outputs under docs/v5/grounding_initial18_debug/:
  - summary.json
  - index.html
  - overlays/*.png
"""

from __future__ import annotations

import argparse
import html
import json
import time
from pathlib import Path
from typing import Any, Optional

import torch
from PIL import Image, ImageDraw
from transformers import AutoModelForVision2Seq, AutoProcessor

ROOT = Path(__file__).resolve().parent.parent.parent
TRUTH_PATH = ROOT / "docs" / "v5" / "bbox_truth_initial18.json"
MODEL_PATH = ROOT / ".vlms" / "kosmos-2-patch14-224"
OUT_DIR = ROOT / "docs" / "v5" / "grounding_initial18_debug"
OVERLAY_DIR = OUT_DIR / "overlays"
GROUNDING_PROMPT = "<grounding>The gray basket is at"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth", default=str(TRUTH_PATH))
    parser.add_argument("--model", default=str(MODEL_PATH))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def coarse_from_cx(cx: Optional[float]) -> str:
    if cx is None:
        return "not_visible"
    if cx < 1.0 / 3.0:
        return "left"
    if cx > 2.0 / 3.0:
        return "right"
    return "center"


def normalize_box(box: list[float]) -> list[float]:
    x1, y1, x2, y2 = [float(v) for v in box]
    if max(x1, y1, x2, y2) > 1.5:
        x1, y1, x2, y2 = x1 / 1000.0, y1 / 1000.0, x2 / 1000.0, y2 / 1000.0
    return [max(0.0, min(1.0, v)) for v in (x1, y1, x2, y2)]


def parse_basket_bbox(caption: str, entities: list[Any]) -> tuple[Optional[dict[str, Any]], str]:
    keywords = ("basket", "gray box", "box", "container", "gray")
    candidates = []
    for entity_name, _span, boxes in entities:
        for box in boxes:
            x1, y1, x2, y2 = normalize_box(box)
            area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
            if area > 0.85:
                continue
            candidates.append(
                {
                    "entity": str(entity_name),
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "cx": (x1 + x2) / 2.0,
                    "cy": (y1 + y2) / 2.0,
                    "area": area,
                    "is_basket": any(k in str(entity_name).lower() for k in keywords),
                }
            )

    matched = [b for b in candidates if b["is_basket"]]
    if matched:
        return matched[0], "entity_match"

    caption_lower = caption.lower()
    if "far left" in caption_lower:
        return {"entity": "caption:far_left", "x1": 0.0, "y1": 0.4, "x2": 0.2, "y2": 0.6, "cx": 0.1, "cy": 0.5, "area": 0.04}, "caption"
    if "far right" in caption_lower:
        return {"entity": "caption:far_right", "x1": 0.8, "y1": 0.4, "x2": 1.0, "y2": 0.6, "cx": 0.9, "cy": 0.5, "area": 0.04}, "caption"
    if "left" in caption_lower and "right" not in caption_lower:
        return {"entity": "caption:left", "x1": 0.15, "y1": 0.4, "x2": 0.35, "y2": 0.6, "cx": 0.25, "cy": 0.5, "area": 0.04}, "caption"
    if "right" in caption_lower and "left" not in caption_lower:
        return {"entity": "caption:right", "x1": 0.65, "y1": 0.4, "x2": 0.85, "y2": 0.6, "cx": 0.75, "cy": 0.5, "area": 0.04}, "caption"
    if "center" in caption_lower:
        return {"entity": "caption:center", "x1": 0.4, "y1": 0.4, "x2": 0.6, "y2": 0.6, "cx": 0.5, "cy": 0.5, "area": 0.04}, "caption"
    if candidates:
        return candidates[0], "fallback"
    return None, "none"


def box_to_list(box: Optional[dict[str, Any]]) -> Optional[list[float]]:
    if box is None:
        return None
    return [round(float(box[k]), 4) for k in ("x1", "y1", "x2", "y2")]


def draw_box(draw: ImageDraw.ImageDraw, box: list[float], size: tuple[int, int], color: str, width: int) -> None:
    w, h = size
    x1, y1, x2, y2 = box
    x1, x2 = sorted((x1, x2))
    y1, y2 = sorted((y1, y2))
    draw.rectangle([x1 * w, y1 * h, x2 * w, y2 * h], outline=color, width=width)


def render_overlay(image_path: Path, seed_box: Optional[list[float]], pred_box: Optional[list[float]], out_path: Path, title: str) -> None:
    img = Image.open(image_path).convert("RGB").resize((640, 360))
    draw = ImageDraw.Draw(img)
    if seed_box is not None:
        draw_box(draw, seed_box, img.size, "#3399ff", width=4)
    if pred_box is not None:
        draw_box(draw, pred_box, img.size, "#ff3333", width=4)
    draw.rectangle([0, 0, img.size[0], 28], fill=(15, 23, 42))
    draw.text((8, 6), title, fill=(255, 255, 255))
    img.save(out_path)


def build_html(rows: list[dict[str, Any]], summary: dict[str, Any], out_path: Path) -> None:
    cards = []
    for row in rows:
        cards.append(
            """
            <article class="card">
              <img src="{overlay}" alt="{episode} frame {frame_idx}">
              <div class="meta">
                <div><strong>{episode}</strong> / {path_type} / frame {frame_idx}</div>
                <div>pred: {pred_source} / coarse={pred_coarse} / entity={pred_entity}</div>
                <div>seed: coarse={seed_coarse} / has_bbox={seed_has_bbox}</div>
                <div class="caption">{caption}</div>
              </div>
            </article>
            """.format(
                overlay=html.escape(row["overlay_rel"]),
                episode=html.escape(row["episode"]),
                path_type=html.escape(row["path_type"]),
                frame_idx=row["frame_idx"],
                pred_source=html.escape(row["pred_source"]),
                pred_coarse=html.escape(row["pred_coarse_position"]),
                pred_entity=html.escape(str(row["pred_entity"])),
                seed_coarse=html.escape(str(row["seed_coarse_position"])),
                seed_has_bbox=str(bool(row["seed_has_bbox"])).lower(),
                caption=html.escape(row["caption"][:220]),
            )
        )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Initial 18 Grounding Debug</title>
  <style>
    body {{ font-family: sans-serif; margin: 24px; background: #f6f4ef; color: #1f2937; }}
    h1 {{ margin: 0 0 8px; }}
    .summary {{ margin: 0 0 20px; padding: 16px; background: #fff; border: 1px solid #d1d5db; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
    .card {{ background: #fff; border: 1px solid #d1d5db; }}
    img {{ width: 100%; display: block; }}
    .meta {{ padding: 12px; font-size: 14px; line-height: 1.4; }}
    .caption {{ margin-top: 8px; color: #4b5563; }}
    code {{ background: #eef2ff; padding: 2px 6px; }}
  </style>
</head>
<body>
  <h1>Initial 18 Grounding Debug</h1>
  <section class="summary">
    <div>frames: <code>{summary["n_frames"]}</code></div>
    <div>pred bbox frames: <code>{summary["n_pred_bbox"]}</code></div>
    <div>seed bbox frames: <code>{summary["n_seed_bbox"]}</code></div>
    <div>provisional coarse agreement vs seed: <code>{summary["seed_coarse_agreement"]}</code></div>
    <div>provisional detection agreement vs seed: <code>{summary["seed_detection_agreement"]}</code></div>
    <div>note: this report is provisional and compares raw Kosmos output against scaffold seed labels, not human-reviewed GT.</div>
  </section>
  <section class="grid">
    {"".join(cards)}
  </section>
</body>
</html>
"""
    out_path.write_text(html_text)


def main() -> None:
    args = parse_args()
    truth_path = Path(args.truth)
    model_path = Path(args.model)
    out_dir = Path(args.out_dir)
    overlay_dir = out_dir / "overlays"
    out_dir.mkdir(parents=True, exist_ok=True)
    overlay_dir.mkdir(parents=True, exist_ok=True)

    payload = load_json(truth_path)
    annotations = payload["annotations"] if isinstance(payload, dict) else payload

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.float16 if device.type == "cuda" else torch.float32
    processor = AutoProcessor.from_pretrained(str(model_path))
    model = AutoModelForVision2Seq.from_pretrained(str(model_path), torch_dtype=dtype).to(device).eval()

    rows = []
    coarse_match = 0
    coarse_total = 0
    detection_match = 0
    for ann in annotations:
        image_path = Path(ann["frame_path"])
        pil = Image.open(image_path).convert("RGB")
        inputs = processor(text=GROUNDING_PROMPT, images=pil, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        inputs["pixel_values"] = inputs["pixel_values"].to(dtype)

        start = time.time()
        with torch.no_grad():
            generated = model.generate(
                pixel_values=inputs["pixel_values"],
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                image_embeds=None,
                image_embeds_position_mask=inputs.get("image_embeds_position_mask"),
                use_cache=True,
                max_new_tokens=64,
            )
        latency_ms = round((time.time() - start) * 1000.0, 2)
        new_ids = generated[:, inputs["input_ids"].shape[1] :]
        raw = processor.batch_decode(new_ids, skip_special_tokens=False)[0]
        caption, entities = processor.post_process_generation(raw)
        pred_box, pred_source = parse_basket_bbox(caption, entities)
        pred_box_list = box_to_list(pred_box)
        pred_coarse = coarse_from_cx(None if pred_box is None else float(pred_box["cx"]))

        seed_has_bbox = bool(ann.get("seed_has_bbox"))
        seed_coarse = ann.get("seed_coarse_position")
        if seed_coarse in {"left", "center", "right"}:
            coarse_total += 1
            coarse_match += int(pred_coarse == seed_coarse)
        detection_match += int(bool(pred_box_list) == seed_has_bbox)

        stem = f'{ann["episode"]}_f{int(ann["frame_idx"]):04d}'
        overlay_path = overlay_dir / f"{stem}.png"
        title = f'{ann["episode"]} frame {int(ann["frame_idx"]):04d}'
        render_overlay(
            image_path=image_path,
            seed_box=ann.get("seed_bbox_xyxy_norm"),
            pred_box=pred_box_list,
            out_path=overlay_path,
            title=title,
        )

        rows.append(
            {
                "episode": ann["episode"],
                "path_type": ann["path_type"],
                "frame_idx": int(ann["frame_idx"]),
                "frame_path": str(image_path),
                "overlay_rel": str(overlay_path.relative_to(out_dir)),
                "latency_ms": latency_ms,
                "raw": raw,
                "caption": caption,
                "entities": entities,
                "pred_source": pred_source,
                "pred_entity": None if pred_box is None else pred_box.get("entity"),
                "pred_bbox_xyxy_norm": pred_box_list,
                "pred_coarse_position": pred_coarse,
                "seed_has_bbox": seed_has_bbox,
                "seed_bbox_xyxy_norm": ann.get("seed_bbox_xyxy_norm"),
                "seed_coarse_position": seed_coarse,
            }
        )

    summary = {
        "truth_path": str(truth_path),
        "model_path": str(model_path),
        "n_frames": len(rows),
        "n_pred_bbox": sum(1 for row in rows if row["pred_bbox_xyxy_norm"] is not None),
        "n_seed_bbox": sum(1 for row in rows if row["seed_has_bbox"]),
        "seed_coarse_agreement": round(coarse_match / coarse_total, 4) if coarse_total else None,
        "seed_detection_agreement": round(detection_match / len(rows), 4) if rows else None,
        "rows": rows,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    build_html(rows, summary, out_dir / "index.html")
    print(f"Wrote {len(rows)} rows to {out_dir}")


if __name__ == "__main__":
    main()

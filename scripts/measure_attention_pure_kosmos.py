#!/usr/bin/env python3
"""
Attention analysis on pure HuggingFace Kosmos-2 (no LoRA, no fine-tune).

Goal: show that foundation Kosmos-2 DOES attend to instruction text tokens,
and that NavRoboKosMos training kills this attention path. Provides the
"before / after" piece that Exp11/Exp13 measurements alone cannot establish.
"""
import json
from pathlib import Path

import h5py
import numpy as np
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForVision2Seq

ROOT = Path(__file__).resolve().parent.parent
VLM_PATH = ROOT / ".vlms" / "kosmos-2-patch14-224"
DATA_DIR = ROOT / "ROS_action" / "mobile_vla_dataset_v5"
OUT_DIR = ROOT / "docs" / "v5" / "attention_analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "pure_kosmos.json"

INSTRUCTIONS = {
    "left":    "Navigate to the left toward the gray basket",
    "right":   "Navigate to the right toward the gray basket",
    "forward": "Navigate straight forward to the gray basket",
}


def load_same_image(path_type="left_left"):
    eps = sorted(DATA_DIR.glob(f"episode_*{path_type}*.h5"))
    if not eps:
        raise RuntimeError(f"No episode for {path_type}")
    with h5py.File(eps[0], "r") as f:
        if "observations" in f and "images" in f["observations"]:
            imgs = f["observations"]["images"][:]
        else:
            imgs = f["images"][:]
    return Image.fromarray(imgs[0].astype(np.uint8))


def main():
    print(f"Loading processor + model from {VLM_PATH} ...")
    processor = AutoProcessor.from_pretrained(str(VLM_PATH))
    model = AutoModelForVision2Seq.from_pretrained(
        str(VLM_PATH), torch_dtype=torch.float16
    ).cuda().eval()
    img = load_same_image()

    results = {}
    for name, instr in INSTRUCTIONS.items():
        prompt = f"<grounding>{instr}"
        inputs = processor(text=prompt, images=img, return_tensors="pt")
        inputs_gpu = {k: v.cuda() for k, v in inputs.items() if v is not None}
        with torch.no_grad():
            out = model(**inputs_gpu, output_attentions=True)

        attns = out.attentions
        input_ids = inputs_gpu["input_ids"][0].cpu()
        att_mask = inputs_gpu["attention_mask"][0].cpu().bool()
        img_mask_t = inputs_gpu.get("image_embeds_position_mask", None)
        if img_mask_t is not None:
            img_mask = img_mask_t[0].cpu().bool()
        else:
            img_mask = torch.zeros_like(att_mask, dtype=torch.bool)

        seq_len = attns[-1].shape[-1]

        def pad_to(t, L):
            if t.shape[0] == L:
                return t
            if t.shape[0] < L:
                pad = torch.zeros(L - t.shape[0], dtype=t.dtype)
                return torch.cat([t, pad], dim=0)
            return t[:L]

        att_mask = pad_to(att_mask, seq_len)
        img_mask = pad_to(img_mask, seq_len)
        text_mask = att_mask & (~img_mask)

        last_real = int(att_mask.sum().item()) - 1
        if last_real < 0 or last_real >= seq_len:
            last_real = seq_len - 1

        # Per-layer analysis
        layers_data = []
        for li, a in enumerate(attns):
            layer_attn = a[0].float().cpu()
            row = layer_attn[:, last_real, :]
            row_excl = row.clone()
            row_excl[:, last_real] = 0.0
            total = row_excl.sum(dim=-1)
            img_sum = row_excl[:, img_mask].sum(dim=-1)
            text_sum = row_excl[:, text_mask].sum(dim=-1)
            layers_data.append({
                "layer": li,
                "image_ratio_mean": float((img_sum / (total + 1e-9)).mean().item()),
                "text_ratio_mean": float((text_sum / (total + 1e-9)).mean().item()),
                "image_per_head": [float(x) for x in img_sum.tolist()],
                "text_per_head": [float(x) for x in text_sum.tolist()],
            })

        last_attn = attns[-1][0].float().cpu()
        row = last_attn[:, last_real, :]
        self_val = row[:, last_real].clone()
        row_excl = row.clone()
        row_excl[:, last_real] = 0.0
        total = row_excl.sum(dim=-1)
        img_sum = row_excl[:, img_mask].sum(dim=-1)
        text_sum = row_excl[:, text_mask].sum(dim=-1)

        mean_over_heads = row.mean(dim=0)
        topk = torch.topk(mean_over_heads, k=min(10, seq_len))
        top_positions = [
            (int(p), float(v), bool(img_mask[int(p)].item()), bool(text_mask[int(p)].item()))
            for p, v in zip(topk.indices.tolist(), topk.values.tolist())
        ]

        decoded = processor.tokenizer.decode(input_ids.tolist()[: int(att_mask.sum().item())])

        res = {
            "instruction": instr,
            "seq_len": int(seq_len),
            "real_len": int(att_mask.sum().item()),
            "last_real_idx": last_real,
            "img_positions": int(img_mask.sum().item()),
            "text_positions": int(text_mask.sum().item()),
            "image_ratio_mean": float((img_sum / (total + 1e-9)).mean().item()),
            "text_ratio_mean": float((text_sum / (total + 1e-9)).mean().item()),
            "self_attn_mean": float(self_val.mean().item()),
            "top10": top_positions,
            "decoded_prompt_head": decoded[:200],
            "per_layer": layers_data,
        }
        results[name] = res
        print(f"  {name:8s} real_len={res['real_len']:3d} last={last_real:3d} "
               f"img_pos={res['img_positions']:3d} text_pos={res['text_positions']:3d}  "
               f"img={res['image_ratio_mean']:.3f} text={res['text_ratio_mean']:.3f} self={res['self_attn_mean']:.3f}")
        print(f"    top5: {top_positions[:5]}")
        print(f"    per-layer text_ratio: {[round(l['text_ratio_mean'], 3) for l in layers_data]}")

    OUT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nWrote: {OUT_FILE}")


if __name__ == "__main__":
    main()

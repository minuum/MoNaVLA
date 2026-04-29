#!/usr/bin/env python3
"""
Extract text embeddings from Kosmos-2 for Exp18 (BBox + Text + Image).

각 bbox sample의 path_type에 따른 instruction 임베딩 추출.
"""

import sys, json, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch
import numpy as np
from transformers import AutoProcessor, AutoTokenizer, AutoModel

HF_KOSMOS_PATH = ROOT / ".vlms" / "kosmos-2-patch14-224"
BBOX_DATASET = ROOT / "docs/v5/bbox_nav_step1/bbox_dataset.json"
OUT_FILE = ROOT / "docs/v5/bbox_nav_step1/text_embeddings.json"

# Path type → instruction 매핑
INSTRUCTION_MAP = {
    "center_straight": "Navigate toward the gray basket until it is centered in the frame",
    "center_left": "Move left to the obstacle",
    "center_right": "Move right to the obstacle",
    "left_straight": "Navigate toward the gray basket until it is centered in the frame",
    "left_left": "Navigate toward the gray basket on the left until it is in the center of your view",
    "left_right": "Navigate toward the gray basket on the right until it is in the center of your view",
    "right_straight": "Navigate toward the gray basket until it is centered in the frame",
    "right_left": "Navigate toward the gray basket on the left until it is in the center of your view",
    "right_right": "Navigate toward the gray basket on the right until it is in the center of your view",
}


def extract_text_embeddings():
    """Kosmos-2 text encoder로 각 instruction의 임베딩 추출."""

    print(f"Loading tokenizer from {HF_KOSMOS_PATH}...")
    tokenizer = AutoTokenizer.from_pretrained(HF_KOSMOS_PATH)

    # Kosmos-2 text encoder (language model part)
    print(f"Loading text encoder...")
    model = AutoModel.from_pretrained(HF_KOSMOS_PATH)
    model.eval()
    model.to("cuda" if torch.cuda.is_available() else "cpu")

    embeddings = {}

    with torch.no_grad():
        for path_type, instruction in INSTRUCTION_MAP.items():
            print(f"\n  {path_type}: {instruction[:50]}...")

            # Tokenize
            inputs = tokenizer(instruction, return_tensors="pt", padding=True, truncation=True)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

            # Get embeddings (mean pooling of last hidden state)
            outputs = model(**inputs, output_hidden_states=True)
            last_hidden = outputs.last_hidden_state  # [1, seq_len, hidden_size]

            # Mean pooling (attention mask 고려)
            mask = inputs.get("attention_mask", torch.ones_like(last_hidden[:, :, 0]))
            masked = last_hidden * mask.unsqueeze(-1)
            embedding = masked.sum(dim=1) / mask.sum(dim=1, keepdim=True)

            # Convert to numpy and save
            embedding_np = embedding.cpu().numpy().astype(np.float32)
            embeddings[path_type] = embedding_np.tolist()

            print(f"    ✓ Shape: {embedding.shape}, Norm: {embedding.norm():.3f}")

    # Save
    print(f"\nSaving to {OUT_FILE}...")
    with open(OUT_FILE, "w") as f:
        json.dump(embeddings, f, indent=2)

    print(f"✅ Done! {len(embeddings)} instruction embeddings saved.")


if __name__ == "__main__":
    extract_text_embeddings()

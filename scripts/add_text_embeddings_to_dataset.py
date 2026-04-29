#!/usr/bin/env python3
"""
Add text embeddings to all 150 V5 episodes (from filenames).
"""

import sys, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "ROS_action" / "mobile_vla_dataset_v5"
TEXT_EMBEDDINGS_FILE = ROOT / "docs" / "v5" / "bbox_nav_step1" / "text_embeddings.json"
OUT_FILE = ROOT / "docs" / "v5" / "v5_dataset_with_text_embeddings.json"

# Load text embeddings
with open(TEXT_EMBEDDINGS_FILE) as f:
    text_embeddings = json.load(f)

# Extract path_type from filename: episode_*_target_{path_type}_path__*
h5_files = sorted(DATA_DIR.glob("*.h5"))
print(f"Found {len(h5_files)} H5 files")

dataset = []
for h5_file in h5_files:
    # Extract path_type from filename
    match = re.search(r"target_([a-z_]+)_path__", h5_file.name)
    if not match:
        print(f"⚠️ Could not extract path_type from {h5_file.name}")
        continue

    path_type = match.group(1)

    # Get text embedding
    if path_type not in text_embeddings:
        print(f"⚠️ No text embedding for path_type={path_type} in {h5_file.name}")
        continue

    text_emb = text_embeddings[path_type]

    dataset.append({
        "episode": h5_file.stem,
        "path_type": path_type,
        "text_embedding": text_emb,
        "h5_path": str(h5_file)
    })

print(f"\n✓ Prepared {len(dataset)} episodes with text embeddings")

# Save
with open(OUT_FILE, "w") as f:
    json.dump(dataset, f, indent=2)

print(f"✅ Saved to {OUT_FILE}")

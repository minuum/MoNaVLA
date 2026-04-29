#!/usr/bin/env python3
"""
Exp18: BBox + Text + Image Fusion for Navigation

Decomposition approach with explicit text embedding:
  Input:  BBox history (3*4=12) + text embedding (1024) + image (16x16=256) = 1292
  MLP:    [512, 256, 128] → 8-class action
  Goal:   70%+ closed-loop success (vs Exp14 Step2: 66.7%)
"""

import sys, json, argparse, logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import h5py
from tqdm import tqdm
import matplotlib.pyplot as plt

# Setup logging
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"exp18_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DATA_DIR = ROOT / "ROS_action" / "mobile_vla_dataset_v5"
BBOX_DATASET_FILE = ROOT / "docs" / "v5" / "bbox_nav_step1" / "bbox_dataset_with_text.json"
OUT_DIR = ROOT / "docs" / "v5" / "bbox_nav_step3"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOW = 3
IMG_SIZE = 16
NUM_CLASSES = 8
EPOCHS = 300
BATCH_SIZE = 32
LR = 0.001


class MLPWithText(nn.Module):
    """BBox + Text + Image fusion MLP."""

    def __init__(self, input_dim=1292, hidden_dims=[512, 256, 128], output_dim=8):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for h_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.1))
            prev_dim = h_dim
        layers.append(nn.Linear(prev_dim, output_dim))
        self.model = nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)


def extract_image_feature(ep_path: Path, frame_idx: int, img_size: int = 16):
    """Extract and resize grayscale image feature."""
    with h5py.File(ep_path) as f:
        img_array = f["observations"]["images"][frame_idx]  # (H, W, 3)
        if len(img_array.shape) == 3:
            img_gray = np.mean(img_array, axis=2)  # to grayscale
        else:
            img_gray = img_array
        # Resize to 16x16
        from PIL import Image
        img_pil = Image.fromarray((img_gray * 255).astype(np.uint8))
        img_resized = img_pil.resize((img_size, img_size))
        img_feature = np.array(img_resized).astype(np.float32) / 255.0
        return img_feature.flatten()


def prepare_dataset():
    """Load bbox_dataset_with_text and prepare train/val split."""

    with open(BBOX_DATASET_FILE) as f:
        bbox_data = json.load(f)

    # Split by episode
    all_samples = []
    for sample in bbox_data:
        path_type = sample["path_type"]
        episode = sample["episode"]
        text_emb = np.array(sample["text_embedding"], dtype=np.float32)

        for frame_info in sample["frames"]:
            frame_idx = frame_info["frame_idx"]
            gt_class = frame_info["gt_class"]
            cx, cy, area = frame_info["cx"], frame_info["cy"], frame_info["area"]
            has_bbox = frame_info["has_bbox"]

            if not has_bbox:
                continue

            all_samples.append({
                "episode": episode,
                "frame_idx": frame_idx,
                "gt_class": gt_class,
                "bbox": np.array([cx, cy, area], dtype=np.float32),
                "text_embedding": text_emb,
            })

    # Train/val split
    np.random.seed(42)
    np.random.shuffle(all_samples)
    split_idx = int(0.8 * len(all_samples))
    train_samples = all_samples[:split_idx]
    val_samples = all_samples[split_idx:]

    logger.info(f"✓ Prepared {len(train_samples)} train + {len(val_samples)} val samples")

    return train_samples, val_samples


def train_mlp(train_samples, val_samples):
    """Train BBox+Text+Image MLP."""

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"🚀 Training Exp18 MLP on {device}")

    # Input dim: 3 (bbox) + 1024 (text) + 256 (image) = 1283
    model = MLPWithText(input_dim=1283).to(device)
    optimizer = optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.CrossEntropyLoss()

    train_losses = []
    val_losses = []
    best_val_acc = 0
    best_model_state = None

    for epoch in range(EPOCHS):
        # ── Training ────────────────────
        model.train()
        train_loss = 0
        train_correct = 0

        # Sample batch
        batch_idxs = np.random.choice(len(train_samples), min(BATCH_SIZE, len(train_samples)), replace=False)
        batch_samples = [train_samples[i] for i in batch_idxs]

        for sample in batch_samples:
            # Get image feature
            ep_path = DATA_DIR / f"{sample['episode']}.h5"
            img_feature = extract_image_feature(ep_path, sample["frame_idx"], IMG_SIZE)

            # Concat: bbox + text + image
            x = np.concatenate([
                sample["bbox"],
                sample["text_embedding"],
                img_feature
            ])

            x = torch.from_numpy(x).unsqueeze(0).to(device)
            y = torch.tensor([sample["gt_class"]], dtype=torch.long).to(device)

            # Forward
            logits = model(x)
            loss = loss_fn(logits, y)

            # Backward
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            train_correct += (logits.argmax(1) == y).sum().item()

        train_loss /= max(len(batch_samples), 1)
        train_acc = train_correct / max(len(batch_samples), 1)
        train_losses.append(train_loss)

        # ── Validation ──────────────────
        if epoch % 10 == 0:
            model.eval()
            val_loss = 0
            val_correct = 0

            with torch.no_grad():
                for sample in val_samples[:min(100, len(val_samples))]:  # subset for speed
                    ep_path = DATA_DIR / f"{sample['episode']}.h5"
                    img_feature = extract_image_feature(ep_path, sample["frame_idx"], IMG_SIZE)

                    x = np.concatenate([
                        sample["bbox"],
                        sample["text_embedding"],
                        img_feature
                    ])

                    x = torch.from_numpy(x).unsqueeze(0).to(device)
                    y = torch.tensor([sample["gt_class"]], dtype=torch.long).to(device)

                    logits = model(x)
                    loss = loss_fn(logits, y)

                    val_loss += loss.item()
                    val_correct += (logits.argmax(1) == y).sum().item()

            val_loss /= max(min(100, len(val_samples)), 1)
            val_acc = val_correct / max(min(100, len(val_samples)), 1)
            val_losses.append(val_loss)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()

            logger.info(f"Epoch {epoch:3d}: train_loss={train_loss:.3f} train_acc={train_acc:.1%} | "
                      f"val_loss={val_loss:.3f} val_acc={val_acc:.1%}")

    # Load best model
    if best_model_state:
        model.load_state_dict(best_model_state)

    # Save
    torch.save(model.state_dict(), OUT_DIR / "exp18_mlp.pth")
    logger.info(f"✅ Model saved to {OUT_DIR / 'exp18_mlp.pth'}")

    return model


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("Starting Exp18 BBox+Text+Image MLP Training")
    logger.info("=" * 80)
    train_samples, val_samples = prepare_dataset()
    model = train_mlp(train_samples, val_samples)
    logger.info("=" * 80)
    logger.info("🎯 Exp18 MLP training complete!")
    logger.info(f"   Log file: {LOG_FILE}")
    logger.info("   Next: Run closed-loop evaluation with exp18 model")
    logger.info("=" * 80)

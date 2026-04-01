
import sys
import os
import torch
import numpy as np
import h5py
import json
import random
from pathlib import Path
from PIL import Image
from tqdm import tqdm

# 1. Path & Injection
ROOT_DIR = Path("/home/billy/25-1kp/MoNaVLA")
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "third_party" / "RoboVLMs"))

import robovlms.data
import robovlms.model.policy_head
import robovlms.model.backbone
import robovlms.train
import robovlms.model.backbone.robokosmos as robokosmos_mod

# Custom components
from robovlm_nav.datasets.nav_dataset import NavDataset
from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset as NavH5DatasetImpl
from robovlm_nav.models.policy_head.nav_policy_impl import (
    MobileVLALSTMDecoder as NavLSTMDecoder,
    MobileVLAClassificationDecoder as NavClassificationDecoder,
)
from robovlm_nav.models.policy_head.hybrid_action_head import HybridActionHead
from robovlm_nav.trainer.nav_trainer import NavTrainer
from robovlms.model.backbone.robokosmos import RoboKosMos

# Inject
setattr(robovlms.data, "NavDataset", NavDataset)
setattr(robovlms.data, "MobileVLAH5Dataset", NavH5DatasetImpl)
setattr(robovlms.model.policy_head, "NavPolicy", NavClassificationDecoder)
setattr(robovlms.model.policy_head, "NavPolicyRegression", NavLSTMDecoder)
setattr(robovlms.model.policy_head, "MobileVLAClassificationDecoder", NavClassificationDecoder)
setattr(robovlms.model.policy_head, "MobileVLALSTMDecoder", NavLSTMDecoder)
setattr(robovlms.model.policy_head, "HybridActionHead", HybridActionHead)
setattr(robovlms.model.backbone, "RoboVLM-Nav", RoboKosMos)
import robovlms.train.base_trainer as base_trainer_mod
base_trainer_mod.BaseTrainer = NavTrainer
setattr(robovlms.train, "NavTrainer", NavTrainer)
setattr(robovlms.train, "BaseTrainer", NavTrainer)

from transformers import AutoProcessor

def get_direction_steering_6cls(label):
    # 0: STOP, 1: FORWARD, 2: LEFT, 3: RIGHT, 4: F-LEFT, 5: F-RIGHT
    if label in [2, 4]: # Left bias
        return "Left"
    elif label in [3, 5]: # Right bias
        return "Right"
    else: # Straight / Stop
        return "Straight"

def eval_robust():
    checkpoint_path = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_stage3_robust/2026-03-29/v4-stage3-robust-final/epoch_epoch=epoch=06-val_loss=val_loss=3.387.ckpt"
    config_path = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v4_stage3_robust.json"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Load config correctly with parent support
    from main import load_config
    config = load_config(config_path)
    
    # Dataset
    print("📦 Initializing Validation Dataset (V4-Robust)...")
    val_dataset = NavH5DatasetImpl(
        **config["val_dataset"],
        tokenizer_config=config.get("tokenizer", {})
    )
    
    # Model
    print("🔧 Loading Model from Checkpoint (epoch=06)...")
    trainer = NavTrainer.load_from_checkpoint(
        checkpoint_path,
        configs=config,
        map_location=device,
        strict=False
    )
    model = trainer.model.to(device)
    model.eval()
    
    processor = AutoProcessor.from_pretrained(config["vlm"]["pretrained_model_name_or_path"])
    
    # Metrics
    total_samples = min(len(val_dataset), 50) # Use 50 samples for quick PM/DM test
    pm_count = 0
    dm_count = 0
    
    print(f"📊 Running Evaluation on {total_samples} samples...")
    for i in tqdm(range(total_samples)):
        data = val_dataset[i]
        
        window_size = config["train_dataset"]["window_size"]
        rgb = data['rgb'][:window_size].unsqueeze(0).to(device)
        lang = data['lang']
        
        inputs = processor(text=lang, return_tensors="pt")
        input_ids = inputs['input_ids'].to(device)
        attention_mask = inputs['attention_mask'].to(device)
        
        with torch.no_grad():
            output = model.inference(
                rgb, input_ids, attention_mask,
                None, None, None, None, None
            )
        
        logits = output['action']
        if isinstance(logits, tuple): logits = logits[0]
        # (B, L, chunk, num_classes) = (1, 1, 1, 6)
        pred_logits = logits[0, -1, 0]
        pred_class = pred_logits.argmax(dim=-1).item()
        
        true_classes = data['action'].numpy()
        true_class = int(true_classes[-1])
        
        # Compare
        is_pm = (pred_class == true_class)
        pred_dir = get_direction_steering_6cls(pred_class)
        true_dir = get_direction_steering_6cls(true_class)
        is_dm = (pred_dir == true_dir)
        
        if is_pm:
            pm_count += 1
        if is_dm:
            dm_count += 1
            
    pm_rate = (pm_count / total_samples) * 100
    dm_rate = (dm_count / total_samples) * 100
    
    print("\n" + "="*50)
    print("📈 FINAL PM/DM TEST RESULTS")
    print("="*50)
    print(f"✅ Perfect Match (PM)     : {pm_rate:6.2f}%")
    print(f"✅ Directional Match (DM) : {dm_rate:6.2f}%")
    print(f"   (Total Evaluated: {total_samples})")
    print("="*50)

if __name__ == "__main__":
    eval_robust()

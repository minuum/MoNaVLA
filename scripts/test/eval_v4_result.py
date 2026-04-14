
import sys
import os
import torch
import numpy as np
from pathlib import Path
from tqdm import tqdm

# Path & Injection
ROOT_DIR = Path("/home/billy/25-1kp/MoNaVLA")
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "third_party" / "RoboVLMs"))

from main import load_config
import robovlms.data
import robovlms.model.policy_head
import robovlms.model.backbone
from robovlm_nav.datasets.nav_dataset import NavDataset
from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset as NavH5DatasetImpl
from robovlm_nav.models.policy_head.nav_policy_impl import (
    MobileVLALSTMDecoder as NavLSTMDecoder,
    MobileVLAClassificationDecoder as NavClassificationDecoder,
)
from robovlm_nav.models.policy_head.hybrid_action_head import HybridActionHead
from robovlm_nav.trainer.nav_trainer import NavTrainer
from robovlms.model.backbone.robokosmos import RoboKosMos

# Inject components
setattr(robovlms.data, "NavDataset", NavDataset)
setattr(robovlms.data, "MobileVLAH5Dataset", NavH5DatasetImpl)
setattr(robovlms.model.policy_head, "MobileVLAClassificationDecoder", NavClassificationDecoder)
setattr(robovlms.model.policy_head, "MobileVLALSTMDecoder", NavLSTMDecoder)
setattr(robovlms.model.policy_head, "HybridActionHead", HybridActionHead)
setattr(robovlms.model.backbone, "RoboVLM-Nav", RoboKosMos)

def get_direction_6cls(label):
    # 0: STOP, 1: FORWARD, 2: LEFT, 3: RIGHT, 4: F-LEFT, 5: F-RIGHT
    if label in [2, 4]: return "Left"
    if label in [3, 5]: return "Right"
    if label == 0: return "Stop"
    return "Straight"

def test_checkpoint(checkpoint_path, config_path, num_samples=100):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    config = load_config(config_path)
    
    print(f"\n🔍 Testing Checkpoint: {os.path.basename(checkpoint_path)}")
    
    # Dataset
    val_dataset = NavH5DatasetImpl(
        **config["val_dataset"],
        tokenizer_config=config.get("tokenizer", {})
    )
    
    # Model
    trainer = NavTrainer.load_from_checkpoint(checkpoint_path, configs=config, map_location=device, strict=False)
    model = trainer.model.to(device).eval()
    
    pm = 0
    dm = 0
    stop_correct = 0
    stop_total = 0
    
    indices = np.random.choice(len(val_dataset), min(num_samples, len(val_dataset)), replace=False)
    
    for idx in tqdm(indices, desc="Evaluating"):
        data = val_dataset[idx]
        rgb = data['rgb'][:config["train_dataset"]["window_size"]].unsqueeze(0).to(device)
        lang = data['lang']
        label = data['action_6cls'].item()
        
        with torch.no_grad():
            output = model(rgb, lang)
            pred_logits = output['logits'] # [1, 6]
            pred_label = torch.argmax(pred_logits, dim=-1).item()
        
        # Perfect Match
        if pred_label == label:
            pm += 1
            
        # Directional Match
        if get_direction_6cls(pred_label) == get_direction_6cls(label):
            dm += 1
            
        # Stop analysis
        if label == 0:
            stop_total += 1
            if pred_label == 0:
                stop_correct += 1
                
    print(f"✅ PM: {pm/len(indices)*100:.2f}%")
    print(f"✅ DM: {dm/len(indices)*100:.2f}%")
    if stop_total > 0:
        print(f"🛑 Stop Recall: {stop_correct/stop_total*100:.2f}% ({stop_correct}/{stop_total})")
    else:
        print("🛑 No Stop samples in this batch.")

if __name__ == "__main__":
    BEST_CKPT = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_steer/2026-03-31/v4-steer-sensitivity-v1/epoch_epoch=epoch=03-val_loss=val_loss=0.377.ckpt"
    CFG = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v4_steer_sensitivity.json"
    
    test_checkpoint(BEST_CKPT, CFG, num_samples=200)

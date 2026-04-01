import sys
import os
import torch
from pathlib import Path
from tqdm import tqdm
from transformers import AutoProcessor

# 1. Path & Injection 
ROOT_DIR = Path("/home/billy/25-1kp/MoNaVLA")
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "third_party" / "RoboVLMs"))

from robovlm_nav.models.policy_head.nav_policy_impl import (
    MobileVLAClassificationDecoder as NavClassificationDecoder,
)
from robovlm_nav.datasets.nav_dataset import NavDataset
from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset as NavH5DatasetImpl
from robovlm_nav.trainer.nav_trainer import NavTrainer

# Inject
import robovlms.model.policy_head as action_heads
setattr(action_heads, "MobileVLAClassificationDecoder", NavClassificationDecoder)

import robovlms.data
import robovlms.train
import robovlms.model.backbone
from robovlms.model.backbone.robokosmos import RoboKosMos

setattr(robovlms.data, "NavDataset", NavDataset)
setattr(robovlms.data, "MobileVLAH5Dataset", NavH5DatasetImpl)
setattr(robovlms.model.backbone, "RoboVLM-Nav", RoboKosMos)
import robovlms.train.base_trainer as base_trainer_mod
base_trainer_mod.BaseTrainer = NavTrainer
setattr(robovlms.train, "NavTrainer", NavTrainer)
setattr(robovlms.train, "BaseTrainer", NavTrainer)

def get_direction_steering(label):
    if label in [3, 5, 7]: return "Left"
    elif label in [4, 6, 8]: return "Right"
    else: return "Straight"

def eval_hybrid_final():
    # Use the best checkpoint from the latest run
    checkpoint_path = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_hybrid_eval/2026-03-29/v4-hybrid-final-v1/epoch_epoch=epoch=11-val_loss=val_loss=1.263.ckpt"
    config_path = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v4_hybrid_final.json"
    
    from main import load_config
    config = load_config(config_path)
    
    # Ensure validation dataset uses config
    val_dataset = NavH5DatasetImpl(
        **config["val_dataset"], 
        tokenizer_config=config.get("tokenizer", {}),
    )
    
    print(f"Loading checkpoint: {checkpoint_path}")
    trainer = NavTrainer.load_from_checkpoint(checkpoint_path, configs=config, map_location="cuda", strict=False)
    model = trainer.model.to("cuda").eval()
    processor = AutoProcessor.from_pretrained(config["vlm"]["pretrained_model_name_or_path"])
    
    total_samples = 100 
    pm_count = 0
    dm_count = 0
    
    print(f"📊 Running Evaluation for v4-hybrid-final...")
    for i in tqdm(range(min(total_samples, len(val_dataset)))):
        data = val_dataset[i]
        window_size = config["window_size"]
        rgb = data['rgb'][:window_size].unsqueeze(0).cuda()
        
        # Use simple fixed instruction
        lang = "Navigate toward the gray basket"
        
        inputs = processor(text=lang, return_tensors="pt")
        input_ids = inputs['input_ids'].cuda()
        attention_mask = inputs['attention_mask'].cuda()
        
        with torch.no_grad():
            output = model.inference(rgb, input_ids, attention_mask, None, None, None, None, None)
        
        logits = output['action']
        if isinstance(logits, tuple):
            logits = logits[0]
        
        # In discrete classification, take the last prediction from the sequence
        # logits shape: (B, L, chunk, num_classes) -> (1, 4, 1, 9)
        pred_class = logits[0, -1, 0].argmax(dim=-1).item()
        
        # Ground truth should be from action_chunck's last frame
        # action_chunck shape: (window_size, fwd_pred_next_n)
        # Use .item() on a scalar tensor
        true_label = data['action_chunck'][-1, 0].item()
        
        is_pm = (pred_class == true_label)
        if is_pm: pm_count += 1
        if get_direction_steering(pred_class) == get_direction_steering(true_label): dm_count += 1

    print(f"\n✅ Perfect Match (PM): {(pm_count/total_samples)*100:.2f}%")
    print(f"✅ Directional Match (DM): {(dm_count/total_samples)*100:.2f}%")

if __name__ == "__main__":
    eval_hybrid_final()

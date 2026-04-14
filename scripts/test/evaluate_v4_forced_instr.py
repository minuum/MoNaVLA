import sys
import os
import torch
import numpy as np
import h5py
import json
from pathlib import Path
from tqdm import tqdm

# 1. Path & Injection 
ROOT_DIR = Path("/home/billy/25-1kp/MoNaVLA")
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "third_party" / "RoboVLMs"))

from robovlm_nav.models.policy_head.nav_policy_impl import (
    MobileVLALSTMDecoder as NavLSTMDecoder,
    MobileVLAClassificationDecoder as NavClassificationDecoder,
)
from robovlm_nav.models.policy_head.hybrid_action_head import HybridActionHead
from robovlm_nav.datasets.nav_dataset import NavDataset
from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset as NavH5DatasetImpl
from robovlm_nav.trainer.nav_trainer import NavTrainer

# Inject - BEFORE any other robovlms imports if possible
import robovlms.model.policy_head as action_heads
setattr(action_heads, "NavPolicy", NavClassificationDecoder)
setattr(action_heads, "NavPolicyRegression", NavLSTMDecoder)
setattr(action_heads, "MobileVLAClassificationDecoder", NavClassificationDecoder)
setattr(action_heads, "MobileVLALSTMDecoder", NavLSTMDecoder)
setattr(action_heads, "HybridActionHead", HybridActionHead)

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
from transformers import AutoProcessor

def get_direction_steering(label):
    if label in [3, 5, 7]: return "Left"
    elif label in [4, 6, 8]: return "Right"
    else: return "Straight"

def get_action_aware_instruction(actions, window_size):
    # Dataset logic simplified
    target_act = actions[window_size - 1]
    tx, ty = target_act[0], target_act[1]
    
    curr_act_type = "forward" 
    if abs(tx) < 0.3 and abs(ty) < 0.3: curr_act_type = "stop"
    elif tx > 0.3 and abs(ty) < 0.3: curr_act_type = "forward"
    elif tx < -0.3 and abs(ty) < 0.3: curr_act_type = "backward"
    elif abs(tx) < 0.3 and ty > 0.3: curr_act_type = "left"
    elif abs(tx) < 0.3 and ty < -0.3: curr_act_type = "right"
    elif tx > 0.3 and ty > 0.3: curr_act_type = "diag_fl"
    elif tx > 0.3 and ty < -0.3: curr_act_type = "diag_fr"

    if curr_act_type == "stop": instr = "Stop in front of the gray basket"
    elif curr_act_type == "forward": instr = "Navigate straight to the gray basket"
    elif curr_act_type == "left": instr = "Steer left toward the gray basket"
    elif curr_act_type == "right": instr = "Steer right toward the gray basket"
    elif curr_act_type == "diag_fl": instr = "Navigate diagonally left toward the gray basket"
    elif curr_act_type == "diag_fr": instr = "Navigate diagonally right toward the gray basket"
    else: instr = "Navigate to the gray basket"
    return instr

def eval_v4():
    checkpoint_path = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_exp01/2026-03-15/v4-retrain-v4/epoch_epoch=epoch=04-val_loss=val/loss=1.851.ckpt"
    config_path = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v4_exp01.json"
    from main import load_config
    config = load_config(config_path)
    
    val_dataset = NavH5DatasetImpl(**config["val_dataset"], tokenizer_config=config.get("tokenizer", {}))
    
    trainer = NavTrainer.load_from_checkpoint(checkpoint_path, configs=config, map_location="cuda", strict=False)
    model = trainer.model.to("cuda").eval()
    processor = AutoProcessor.from_pretrained(config["vlm"]["pretrained_model_name_or_path"])
    
    total_samples = 50 
    pm_count = 0
    dm_count = 0
    
    print(f"📊 Running Evaluation with FORCED Action-Aware Instructions...")
    for i in tqdm(range(total_samples)):
        data = val_dataset[i]
        window_size = config["train_dataset"]["window_size"]
        rgb = data['rgb'][:window_size].unsqueeze(0).cuda()
        
        # Override Instruction with Action-Aware one
        actions_raw = data['actions'].numpy()
        # In __getitem__, actions is window+chunk
        # We need the action at window_size-1 to determine instruction
        # But wait, the dataset's actions list might be normalized or not. 
        # Actually, let's just use the ground truth label to craft the instruction
        true_label = int(actions_raw[window_size]) 
        # Label to instruction mapping reversal
        if true_label == 0: lang = "Stop in front of the gray basket"
        elif true_label == 1: lang = "Navigate straight to the gray basket"
        elif true_label == 3: lang = "Steer left toward the gray basket"
        elif true_label == 4: lang = "Steer right toward the gray basket"
        elif true_label == 5: lang = "Navigate diagonally left toward the gray basket"
        elif true_label == 6: lang = "Navigate diagonally right toward the gray basket"
        else: lang = "Navigate to the gray basket"

        inputs = processor(text=lang, return_tensors="pt")
        input_ids = inputs['input_ids'].cuda()
        attention_mask = inputs['attention_mask'].cuda()
        
        with torch.no_grad():
            output = model.inference(rgb, input_ids, attention_mask, None, None, None, None, None)
        
        logits = output['action']
        if isinstance(logits, tuple):
            logits = logits[0]
        
        pred_class = logits[0, -1, 0].argmax(dim=-1).item()
        true_class = true_label
        
        is_pm = (pred_class == true_class)
        if is_pm: pm_count += 1
        if get_direction_steering(pred_class) == get_direction_steering(true_class): dm_count += 1

    print(f"\n✅ Perfect Match (PM): {(pm_count/total_samples)*100:.2f}%")
    print(f"✅ Directional Match (DM): {(dm_count/total_samples)*100:.2f}%")

if __name__ == "__main__":
    eval_v4()

import sys
import os
import torch
import numpy as np
from pathlib import Path
from tqdm import tqdm
from transformers import AutoProcessor

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

# Inject
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

def diagnose():
    # Model: Weighted Regression (0.259 Best)
    checkpoint_path = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_regression_v2/2026-03-26/v4-regression-v2-weighted-v2/epoch_epoch=epoch=02-val_loss=val_loss=0.259.ckpt"
    config_path = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v4_regression_v2_weighted.json"
    
    from main import load_config
    config = load_config(config_path)
    
    # Defaults to avoid KeyErrors in BaseTrainer initialization
    if "use_hand_rgb" not in config: config["use_hand_rgb"] = False
    if "vlm" not in config: config["vlm"] = {"pretrained_model_name_or_path": "microsoft/kosmos-2-patch14-224"}
    if "train_setup" not in config: config["train_setup"] = {}
    
    val_dataset = NavH5DatasetImpl(**config["val_dataset"], tokenizer_config=config.get("tokenizer", {}))
    trainer = NavTrainer.load_from_checkpoint(checkpoint_path, configs=config, map_location="cuda", strict=False)
    model = trainer.model.to("cuda").eval()
    processor = AutoProcessor.from_pretrained(config["vlm"]["pretrained_model_name_or_path"])
    
    test_instructions = [
        "Navigate straight to the gray basket",
        "Steer left toward the gray basket",
        "Steer right toward the gray basket",
        "Stop in front of the gray basket"
    ]
    
    sample_indices = [0, 50, 100] # Representative frames
    
    print("\n🔍 --- SCENE MEMORIZATION DIAGNOSIS (COMMMAND VARIATION TEST) ---")
    for idx in sample_indices:
        data = val_dataset[idx]
        window_size = config["train_dataset"]["window_size"]
        rgb = data['rgb'][:window_size].unsqueeze(0).cuda()
        
        print(f"\n[Frame Index: {idx}] (GT Action was supposedly matching some instruction)")
        
        for lang in test_instructions:
            # [핵심 실험] 매 명령어 추론 전 LSTM hidden_state 강제 리셋
            # 이전 추론의 잔여 hidden이 현재 결과에 영향을 주는지 배제하기 위함
            if hasattr(model, 'act_head') and hasattr(model.act_head, 'reset'):
                model.act_head.reset()
            
            inputs = processor(text=lang, return_tensors="pt")
            input_ids = inputs['input_ids'].cuda()
            attention_mask = inputs['attention_mask'].cuda()
            
            with torch.no_grad():
                # mobile_vla_policy forward: inference uses policy_head outputs
                output = model.inference(rgb, input_ids, attention_mask, None, None, None, None, None)
            
            # For Regression: Output['action'] is [B, chunk, dim] or tuple
            raw_action = output['action'] 
            if isinstance(raw_action, tuple):
                raw_action = raw_action[1] if len(raw_action) > 1 and isinstance(raw_action[0], torch.Tensor) and raw_action[0].shape[-1] != 2 else raw_action[0]
            
            # Print shape for debugging
            # print(f"DEBUG: raw_action shape {raw_action.shape}")
            
            # (B, T, chunk, 2)
            if raw_action.dim() == 4:
                v_lin = raw_action[0, -1, 0, 0].item()
                v_ang = raw_action[0, -1, 0, 1].item()
            elif raw_action.dim() == 3:
                v_lin = raw_action[0, 0, 0].item()
                v_ang = raw_action[0, 0, 1].item()
            elif raw_action.dim() == 2:
                v_lin = raw_action[0, 0].item()
                v_ang = raw_action[0, 1].item()
            else:
                print(f"DEBUG: Unexpected shape {raw_action.shape}")
                continue
            
            print(f"  Command: \"{lang}\"")
            print(f"  -> Predicted: Lin_v={v_lin:.4f}, Ang_v={v_ang:.4f}")

if __name__ == "__main__":
    import json
    diagnose()

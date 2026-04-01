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

import robovlms.data
import robovlms.model.policy_head
import robovlms.model.backbone
import robovlms.train
from robovlm_nav.datasets.nav_dataset import NavDataset
from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset as NavH5DatasetImpl
from robovlm_nav.models.policy_head.nav_policy_impl import MobileVLALSTMDecoder as NavLSTMDecoder
from robovlm_nav.trainer.nav_trainer import NavTrainer
from robovlms.model.backbone.robokosmos import RoboKosMos

# Patch for loading
setattr(robovlms.data, "MobileVLAH5Dataset", NavH5DatasetImpl)
setattr(robovlms.model.policy_head, "NavPolicyRegression", NavLSTMDecoder)
setattr(robovlms.model.policy_head, "MobileVLALSTMDecoder", NavLSTMDecoder)
setattr(robovlms.model.backbone, "RoboVLM-Nav", RoboKosMos)

def evaluate():
    checkpoint_path = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_hard/2026-03-31/v4-hard-counterfactual-v1/epoch_epoch=epoch=05-val_loss=val_loss=0.981.ckpt"
    config_path = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v4_hard_counterfactual.json"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    from main import load_config
    config = load_config(config_path)
    
    # Dataset
    print("📦 Initializing Validation Dataset...")
    val_dataset_params = config["val_dataset"].copy()
    val_dataset_params["counterfactual_stop_prob"] = 0.0 # 평가는 원본 분포로
    val_dataset = NavH5DatasetImpl(
        **val_dataset_params,
        tokenizer_config=config.get("tokenizer", {})
    )
    
    # Model
    print(f"🔧 Loading Model: {Path(checkpoint_path).name}")
    trainer = NavTrainer.load_from_checkpoint(checkpoint_path, configs=config, map_location=device, strict=False)
    model = trainer.model.to(device)
    model.eval()
    
    processor = AutoProcessor.from_pretrained(config["vlm"]["pretrained_model_name_or_path"])
    
    # metrics
    total_l1_linear = 0
    total_l1_angular = 0
    dm_match = 0
    valid_dm_samples = 0
    text_sensitivity_count = 0 
    
    num_eval = min(100, len(val_dataset)) 
    print(f"📊 Running Evaluation on {num_eval} samples...")
    
    for i in tqdm(range(num_eval)):
        data = val_dataset[i]
        window_size = config["train_dataset"]["window_size"]
        rgb = data['rgb'][:window_size].unsqueeze(0).to(device)
        
        # 데이터셋 키 확인 결과 'action' (단수) 사용
        true_action = data['action'][window_size - 1].numpy() # [linear, angular]
        
        # 1. Original Inference (Navigate)
        lang_nav = data['lang']
        inputs_nav = processor(text=lang_nav, return_tensors="pt")
        with torch.no_grad():
            out_nav = model.inference(rgb, inputs_nav['input_ids'].to(device), inputs_nav['attention_mask'].to(device), None, None, None, None, None)
        pred_nav = out_nav['action'][0][0, -1, :2].cpu().numpy() # [linear, angular]
        
        # 2. Counterfactual Inference (Force "Stop")
        lang_stop = "Stop" 
        inputs_stop = processor(text=lang_stop, return_tensors="pt")
        with torch.no_grad():
            out_stop = model.inference(rgb, inputs_stop['input_ids'].to(device), inputs_stop['attention_mask'].to(device), None, None, None, None, None)
        pred_stop = out_stop['action'][0][0, -1, :2].cpu().numpy() # [linear, angular]
        
        p_nav_lin = pred_nav.flatten()[0]
        p_stop_lin = pred_stop.flatten()[0]
        p_nav_ang = pred_nav.flatten()[1]

        if i < 5:
            print(f"\n[Sample {i}] Lang: {lang_nav}")
            print(f"  - Pred Shape: {pred_nav.shape}")
            print(f"  - Nav Pred (Lin): {p_nav_lin:.4f}")
            print(f"  - Stop Pred (Lin): {p_stop_lin:.4f}")
            ratio = (p_stop_lin / p_nav_lin) if abs(p_nav_lin) > 1e-6 else 1.0
            print(f"  - Ratio    : {ratio:.4f}")
        
        # Metrics
        total_l1_linear += np.abs(p_nav_lin - true_action[0])
        total_l1_angular += np.abs(p_nav_ang - true_action[1])
        
        if abs(true_action[1]) > 0.05:
            valid_dm_samples += 1
            if np.sign(p_nav_ang) == np.sign(true_action[1]):
                dm_match += 1
                
        # Text Sensitivity
        # Stop일 때 선속도(Index 0)가 40% 이상 감소하면 민감하게 반응했다고 판단
        if np.abs(p_stop_lin) < np.abs(p_nav_lin) * 0.6:
            text_sensitivity_count += 1

    avg_l1_lin = total_l1_linear / num_eval
    avg_l1_ang = total_l1_angular / num_eval
    dm_rate = (dm_match / valid_dm_samples * 100) if valid_dm_samples > 0 else 0
    sensitivity_rate = (text_sensitivity_count / num_eval) * 100
    
    print("\n" + "="*50)
    print("📈 V4 Counterfactual Training Evaluation Result")
    print("="*50)
    print(f"✅ Avg L1 Linear Error : {avg_l1_lin:.4f}")
    print(f"✅ Avg L1 Angular Error: {avg_l1_ang:.4f}")
    print(f"✅ Directional Match (DM): {dm_rate:.2f}%")
    print(f"✅ Text Sensitivity (Stop-Reasoning): {sensitivity_rate:.2f}%")
    print("-" * 50)
    print("Interpretation:")
    if sensitivity_rate > 50:
        print(">> SUCCESS: The model is now following language instructions.")
    else:
        print(">> WARNING: The model still relies heavily on scene memorization.")
    print("="*50)

if __name__ == "__main__":
    evaluate()

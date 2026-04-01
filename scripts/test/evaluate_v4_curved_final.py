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
    # 3/27 Curved Only + Stop 50% 학습의 최종 체크포인트
    checkpoint_path = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_curved_eval/2026-03-27/v4-curved-only-stop50-v1/last.ckpt"
    config_path = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v4_curved_stop50.json"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    from main import load_config
    config = load_config(config_path)
    
    # Dataset
    print("📦 Initializing Validation Dataset (All episodes for fair comparison)...")
    val_dataset_params = config["val_dataset"].copy()
    val_dataset_params["curvature_only"] = False # 평가는 모든 데이터(직진 포함)에 대해 수행
    val_dataset_params["counterfactual_stop_prob"] = 0.0 
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
        
        # 3-Omniwheel: [x_vel, y_vel]
        true_action = data['action'][window_size - 1].numpy() 
        
        # 1. Original Inference (Navigate)
        lang_nav = data['lang']
        inputs_nav = processor(text=lang_nav, return_tensors="pt")
        with torch.no_grad():
            out_nav = model.inference(rgb, inputs_nav['input_ids'].to(device), inputs_nav['attention_mask'].to(device), None, None, None, None, None)
        pred_nav = out_nav['action'][0][0, -1, :2].cpu().numpy() # [pred_x, pred_y]
        
        # 2. Counterfactual Inference (Force "Stop")
        lang_stop = "Stop the robot" 
        inputs_stop = processor(text=lang_stop, return_tensors="pt")
        with torch.no_grad():
            out_stop = model.inference(rgb, inputs_stop['input_ids'].to(device), inputs_stop['attention_mask'].to(device), None, None, None, None, None)
        pred_stop = out_stop['action'][0][0, -1, :2].cpu().numpy() 
        
        p_nav_x = pred_nav.flatten()[0]
        p_nav_y = pred_nav.flatten()[1]
        p_stop_x = pred_stop.flatten()[0]

        if i < 5:
            print(f"\n[Sample {i}] Lang: {lang_nav}")
            print(f"  - Nav Pred (X): {p_nav_x:.4f}, (Y): {p_nav_y:.4f}")
            print(f"  - Stop Pred (X): {p_stop_x:.4f}")
            ratio = (p_stop_x / p_nav_x) if abs(p_nav_x) > 1e-6 else 1.0
            print(f"  - Ratio(Stop/Nav) : {ratio:.4f}")
        
        # Metrics
        total_l1_linear += np.abs(p_nav_x - true_action[0])
        total_l1_angular += np.abs(p_nav_y - true_action[1])
        
        # Omni-Movement DM: y(횡방향)의 부호 일치 여부 (조향 능력)
        if abs(true_action[1]) > 0.05:
            valid_dm_samples += 1
            if np.sign(p_nav_y) == np.sign(true_action[1]):
                dm_match += 1
                
        # Text Sensitivity (Stop-Reasoning)
        # Stop 명령 시 전속도(X)가 50% 이상 감소하면 민감하다고 판단
        if np.abs(p_stop_x) < np.abs(p_nav_x) * 0.5:
            text_sensitivity_count += 1

    avg_l1_x = total_l1_linear / num_eval
    avg_l1_y = total_l1_angular / num_eval
    dm_rate = (dm_match / valid_dm_samples * 100) if valid_dm_samples > 0 else 0
    sensitivity_rate = (text_sensitivity_count / num_eval) * 100
    
    print("\n" + "="*50)
    print("📈 V4 Curved-Only + Stop 50% Result")
    print("="*50)
    print(f"✅ Avg L1 X (Forward) Error : {avg_l1_x:.4f}")
    print(f"✅ Avg L1 Y (Lateral) Error : {avg_l1_y:.4f}")
    print(f"✅ Directional Match (Lateral): {dm_rate:.2f}%")
    print(f"✅ Text Sensitivity (Stop-Reasoning): {sensitivity_rate:.2f}%")
    print("-" * 50)
    print("Analysis:")
    if sensitivity_rate > 50:
        print(">> IMPROVEMENT: Model starts following 'Stop' commands!")
    else:
        print(">> FAILURE: Model still ignores text commands.")
    print("="*50)

if __name__ == "__main__":
    evaluate()

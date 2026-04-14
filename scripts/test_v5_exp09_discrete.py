import os
import sys
import json
import torch
import random
from pathlib import Path

# Add project roots to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "third_party" / "RoboVLMs"))

# Register custom components (same as train.py)
import robovlms.data
import robovlms.model.policy_head
import robovlms.model.backbone
import robovlms.train

from robovlm_nav.datasets.nav_dataset import NavDataset
from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset as NavH5DatasetImpl
from robovlm_nav.models.policy_head.nav_policy_impl import MobileVLAClassificationDecoder as NavClassificationDecoder
from robovlm_nav.models.policy_head.nav_policy_impl import MobileVLALSTMDecoder as NavLSTMDecoder
from robovlm_nav.models.policy_head.hybrid_action_head import HybridActionHead
from robovlm_nav.trainer.nav_trainer import NavTrainer
from robovlms.model.backbone.robokosmos import RoboKosMos

setattr(robovlms.data, "NavDataset", NavDataset)
setattr(robovlms.data, "MobileVLAH5Dataset", NavH5DatasetImpl)
setattr(robovlms.model.policy_head, "NavPolicy", NavClassificationDecoder)
setattr(robovlms.model.policy_head, "MobileVLAClassificationDecoder", NavClassificationDecoder)
setattr(robovlms.model.backbone, "RoboVLM-Nav", RoboKosMos)

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--cpu", action="store_true", help="Run on CPU")
args = parser.parse_args()

device = 'cpu' if args.cpu else 'cuda'
print(f"Using device: {device}")

# Configs
ckpt = "/home/billy/25-1kp/MoNaVLA/runs/v5_nav/kosmos/mobile_vla_v5_8cls/2026-04-14/v5-exp09-8cls-balanced/last-v1.ckpt"
cfg_path = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp09_8cls.json"

from main import load_config
config = load_config(cfg_path)

print(f"Loading checkpoint from: {ckpt}")
trainer = NavTrainer.from_checkpoint(ckpt, variant=config)
model = trainer.model.to(device)
model.eval()

# Dataset loader
dataset_cfg = config['val_dataset']
dataset_cfg['is_validation'] = True
dataset_cfg['train_split'] = 0.0 # Use all files in data_dir for testing

# Add tokenizer from model to dataset config
dataset_cfg['tokenizer'] = trainer.model.tokenizer if hasattr(trainer.model, "tokenizer") else None
dataset_cfg['tokenizer_config'] = config.get('tokenizer', None)

ds = NavDataset(**dataset_cfg)
dataloader = torch.utils.data.DataLoader(ds, batch_size=1, shuffle=True, num_workers=0, collate_fn=ds.collater)

print("\n" + "="*50)
print("V5 EXP09 DISCRETE INFERENCE TEST (8-CLASSES)")
print("="*50)

LABEL_MAP = {
    0: "Stop",
    1: "Forward",
    2: "Left (lx>0, ly>0)", 
    3: "Right (lx>0, ly<0)",
    4: "Diag-FL",
    5: "Diag-FR",
    6: "Turn-Left (az>0)",
    7: "Turn-Right (az<0)"
}

test_count = 10
success = 0
stats = {k: {"total": 0, "correct": 0} for k in LABEL_MAP.values()}

with torch.no_grad():
    # Use autocast only on CUDA
    autocast_context = torch.cuda.amp.autocast(dtype=torch.float16) if device == 'cuda' else torch.enable_grad() # Dummmy grad on for CPU if needed, or just null context
    
    for i, batch in enumerate(dataloader):
        if i >= test_count: break
        
        if device == 'cuda': torch.cuda.empty_cache()
        gpu_batch = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
    
        # Inference
        with (torch.cuda.amp.autocast(dtype=torch.float16) if device == 'cuda' else torch.no_grad()):
            prediction = model.inference(
                gpu_batch['rgb'],
                gpu_batch['text'],
                attention_mask=gpu_batch['text_mask'],
                vision_gripper=gpu_batch['hand_rgb'],
                raw_text=gpu_batch['raw_text'],
                data_source=gpu_batch['data_source']
            )
            
            logits = prediction['action']
            if isinstance(logits, tuple): logits = logits[0]
            
            final_logits = logits[0, -1, 0] 
            pred_class = final_logits.argmax().item()
            gt_class = int(gpu_batch['action_chunck'][0, -1, 0].item())
            
            gt_label = LABEL_MAP.get(gt_class, 'Unknown')
            pred_label = LABEL_MAP.get(pred_class, 'Unknown')
            
            is_correct = (pred_class == gt_class)
            if is_correct: success += 1
            
            # Update stats
            if gt_label not in stats: stats[gt_label] = {"total": 0, "correct": 0}
            stats[gt_label]["total"] += 1
            if is_correct: stats[gt_label]["correct"] += 1
            
            print(f"[{i+1}/{test_count}] GT: {gt_label:15} | PRED: {pred_label:15} | {'✅' if is_correct else '❌'}")
            
            # Print top probs for variety check
            probs = torch.softmax(final_logits, dim=-1)
            top3 = {LABEL_MAP[k.item()]: round(v.item(), 3) for v, k in zip(*probs.topk(3))}
            print(f"      Probs: {top3}")

print("\n" + "="*50)
print("CLASS-WISE PERFORMANCE (BIAS ANALYSIS)")
print("="*50)
for label, data in stats.items():
    if data["total"] > 0:
        acc = (data["correct"] / data["total"]) * 100
        print(f"{label:20}: {data['correct']}/{data['total']} ({acc:.1f}%)")

print(f"\nFinal Overall Accuracy: {success}/{test_count} ({success/test_count*100}%)")

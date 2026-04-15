#!/usr/bin/env python3
"""
V5 Exp10 Grounding Performance Evaluation Script
Calculates IoU between predicted BBox and Ground Truth (Heuristic-based)
"""
import os
import sys
import re

os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["USE_FLASH_ATTENTION"] = "0"

sys.path.insert(1, "/home/billy/25-1kp/MoNaVLA")
sys.path.insert(0, "/home/billy/25-1kp/MoNaVLA/third_party/RoboVLMs")

import torch
import numpy as np
from tqdm import tqdm
import cv2

log_file = open("/home/billy/25-1kp/MoNaVLA/v5_exp10_bbox_eval.log", "w")
def debug_print(*args, **kwargs):
    print(*args, **kwargs)
    print(*args, **kwargs, file=log_file, flush=True)

from robovlms.train.mobile_vla_trainer import MobileVLATrainer
from robovlms.model.backbone.robokosmos import RoboKosMos
import robovlms.model.backbone as backbone
setattr(backbone, "RoboVLM-Nav", RoboKosMos)

# Config & Checkpoint Settings
CONFIG_PATH = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp10_bbox.json"
# Default to the Exp09 last.ckpt as starting point for 0-epoch test, 
# but user should replace CKPT_PATH later.
CKPT_PATH = "/home/billy/25-1kp/MoNaVLA/runs/v5_nav/kosmos/v5-exp10-track2-bbox/last.ckpt"
if not os.path.exists(CKPT_PATH):
    # Fallback to model_load_path from config
    CKPT_PATH = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_regression_v2/2026-03-26/v4-regression-v2-weighted-v2/last.ckpt"

def calculate_iou(box1, box2):
    """
    box: [x1, y1, x2, y2]
    """
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    union_area = box1_area + box2_area - inter_area
    if union_area == 0: return 0
    return inter_area / union_area

def parse_bbox_tokens(text):
    """
    Extracts bbox from text like <box_2d><patch_index_XXXX><patch_index_YYYY></box_2d>
    Returns: [xmin, ymin, xmax, ymax] in normalized (0~1) or patch space
    Note: Kosmos-2 uses patch index to define corners.
    """
    pattern = r"<patch_index_(\d{4})><patch_index_(\d{4})>"
    matches = re.findall(pattern, text)
    if not matches:
        return None
    
    p1 = int(matches[0][0])
    p2 = int(matches[0][1])
    
    # 32x32 grid
    y1, x1 = divmod(p1, 32)
    y2, x2 = divmod(p2, 32)
    
    return [x1 / 31.0, y1 / 31.0, x2 / 31.0, y2 / 31.0]

def evaluate():
    from robovlms.model.backbone.base_backbone import load_config
    configs = load_config(CONFIG_PATH)
    trainer = MobileVLATrainer(configs)
    
    if os.path.exists(CKPT_PATH):
        debug_print(f"Loading checkpoint: {os.path.basename(CKPT_PATH)}")
        checkpoint = torch.load(CKPT_PATH, map_location="cpu")
        state_dict = checkpoint.get("state_dict", checkpoint)
        if any(k.startswith("model.") for k in state_dict.keys()):
            state_dict = {k[6:] if k.startswith("model.") else k: v for k, v in state_dict.items()}
        trainer.model.load_state_dict(state_dict, strict=True)
    
    model = trainer.model.to('cuda:0')
    model.eval()

    from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset
    ds = MobileVLAH5Dataset(
        data_dir=configs["train_dataset"]["data_dir"],
        episode_pattern="episode_*.h5",
        model_name="kosmos",
        window_size=1,
        use_bbox_target=True,
        is_validation=True,
        instruction_preset="action_aware_train"
    )

    total_count = 0
    iou_sum = 0
    success_at_05 = 0
    
    debug_print("Starting V5 Exp10 Grounding Evaluation...")
    with torch.no_grad():
        for i in tqdm(range(len(ds))):
            if i >= 100: break # Evaluation subset
            try:
                sample = ds[i]
                # Dataset provides 'lang' which contains the GT bbox text
                gt_instr = sample['lang']
                gt_box = parse_bbox_tokens(gt_instr)
                if gt_box is None:
                    continue

                # Prepare model input
                batch = ds.collater([sample])
                gpu_batch = {k: v.cuda() if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
                
                # Inference using forward to get logits
                outputs = model.model(
                    pixel_values=gpu_batch['rgb'],
                    input_ids=gpu_batch['text'],
                )
                logits = outputs.logits # [1, seq_len, vocab_size]
                
                # Use generate for text prediction
                output_ids = model.model.generate(
                    pixel_values=gpu_batch['rgb'],
                    input_ids=gpu_batch['text'],
                    max_new_tokens=20,
                    return_dict_in_generate=True,
                    output_scores=True
                )
                
                pred_text = model.model.tokenizer.decode(output_ids.sequences[0], skip_special_tokens=False)
                pred_box = parse_bbox_tokens(pred_text)
                
                # Calculate Action Probability (Confidence)
                # We look at the scores for the generated patch tokens
                patch_scores = []
                for score in output_ids.scores: # list of tensors [1, vocab_size]
                    probs = torch.softmax(score[0], dim=-1)
                    max_prob, max_idx = torch.max(probs, dim=-1)
                    token = model.model.tokenizer.decode([max_idx.item()])
                    if "patch_index" in token:
                        patch_scores.append(max_prob.item())

                mean_conf = np.mean(patch_scores) if patch_scores else 0
                
                if pred_box is None:
                    iou = 0
                else:
                    iou = calculate_iou(gt_box, pred_box)
                
                iou_sum += iou
                if iou >= 0.5:
                    success_at_05 += 1
                total_count += 1
                
                if i % 5 == 0:
                    debug_print(f"Frame {i:03} | IoU: {iou:.3f} | Action Conf (Avg Prob): {mean_conf:.4%}")
                    debug_print(f"  > Pred Text: {pred_text[:60]}...")
                
                if i % 10 == 0:
                    debug_print(f"Frame {i} | IoU: {iou:.3f} | Action Conf: {mean_conf:.4f} | Text: {pred_text[:50]}...")

            except Exception as e:
                debug_print(f"Error at frame {i}: {e}")
                continue

            except Exception as e:
                continue

    debug_print("\n" + "="*50)
    debug_print("📊 GROUNDING EVALUATION (V5 Exp10)")
    debug_print(f"Total processed: {total_count}")
    if total_count > 0:
        debug_print(f"Mean IoU: {iou_sum/total_count:.4f}")
        debug_print(f"Success Rate @ IoU 0.5: {success_at_05/total_count:.4f}")
    debug_print("="*50)

if __name__ == "__main__":
    evaluate()

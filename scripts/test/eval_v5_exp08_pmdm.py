#!/usr/bin/env python3
"""
V5 Exp08 PM/DM 성능 평가 스크립트
"""
import os
import sys

os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["USE_FLASH_ATTENTION"] = "0"
os.environ["TRANSFORMERS_SKIP_VERSION_CHECK"] = "1"

sys.path = [p for p in sys.path if ".local" not in p and "ros" not in p.lower()]
sys.path.insert(1, "/home/billy/25-1kp/MoNaVLA")
sys.path.insert(0, "/home/billy/25-1kp/MoNaVLA/third_party/RoboVLMs")

import torch
import numpy as np
from tqdm import tqdm

log_file = open("/home/billy/25-1kp/MoNaVLA/v5_exp08_pmdm_eval.log", "w")
def debug_print(*args, **kwargs):
    print(*args, **kwargs)
    print(*args, **kwargs, file=log_file, flush=True)

from robovlms.train.mobile_vla_trainer import MobileVLATrainer
import robovlms.model.backbone as backbone
from robovlms.model.backbone.robokosmos import RoboKosMos
setattr(backbone, "RoboVLM-Nav", RoboKosMos)

import robovlms.model.policy_head as policy_head
from robovlm_nav.models.policy_head.nav_policy_impl import MobileVLAClassificationDecoder, MobileVLALSTMDecoder
setattr(policy_head, "NavPolicy", MobileVLAClassificationDecoder)
setattr(policy_head, "NavPolicyRegression", MobileVLALSTMDecoder)

import robovlms.utils.model_utils as model_utils
orig_dtc = model_utils.default_tokenizer_config
def patched_dtc(tokenizer):
    if tokenizer == 'kosmos':
        return {'type': 'AutoProcessor', 'pretrained_model_name_or_path': 'microsoft/kosmos-2-patch14-224', 'tokenizer_type': 'kosmos'}
    return orig_dtc(tokenizer)
model_utils.default_tokenizer_config = patched_dtc

# 설정
CKPT_PATH = "/home/billy/25-1kp/MoNaVLA/runs/v5_nav/kosmos/mobile_vla_v5_exp08/2026-04-13/v5-exp08-instruction-follow/epoch_epoch=epoch=05-val_loss=val_loss=3.748.ckpt"
CONFIG_PATH = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp08_instruction_follow.json"
DATASET_PATH = "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v3"

ACTION_CLASSES = {0: "Stop", 1: "Forward", 2: "Left", 3: "Right", 4: "FL", 5: "FR"}

def parse_action_logits(outputs):
    if outputs is None:
        return None
    if isinstance(outputs, (tuple, list)):
        outputs = outputs[0]
    if not isinstance(outputs, torch.Tensor):
        return None
    pred_np = outputs.detach().cpu().float().numpy()
    ndim = pred_np.ndim
    if ndim == 4:
        class_logits = pred_np[0, -1, 0, :]
    elif ndim == 3:
        class_logits = pred_np[0, -1, :]
    elif ndim == 2:
        class_logits = pred_np[0, :]
    elif ndim == 1:
        class_logits = pred_np
    else:
        return None
    return int(np.argmax(class_logits)), class_logits

def parse_gt_label(gpu_batch):
    if 'action_chunck' in gpu_batch:
        ac = gpu_batch['action_chunck'].detach().cpu().numpy()
        return int(ac[0, -1, 0])
    return None

def evaluate():
    from robovlms.model.backbone.base_backbone import load_config
    configs = load_config(CONFIG_PATH)
    configs["model_path"] = "microsoft/kosmos-2-patch14-224"
    if "tokenizer" not in configs: configs["tokenizer"] = {}
    configs["tokenizer"]["pretrained_model_name_or_path"] = "microsoft/kosmos-2-patch14-224"
    if "vlm" not in configs: configs["vlm"] = {}
    configs["vlm"]["pretrained_model_name_or_path"] = "microsoft/kosmos-2-patch14-224"

    trainer = MobileVLATrainer(configs)
    
    checkpoint = torch.load(CKPT_PATH, map_location="cpu")
    state_dict = checkpoint.get("state_dict", checkpoint)
    if any(k.startswith("model.") for k in state_dict.keys()):
        state_dict = {k[6:] if k.startswith("model.") else k: v for k, v in state_dict.items()}
        
    trainer.model.load_state_dict(state_dict, strict=True)
    model = trainer.model.to('cuda:0')
    model.eval()

    from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset
    ds = MobileVLAH5Dataset(
        data_dir=DATASET_PATH,
        episode_pattern="episode_*.h5",
        model_name="kosmos",
        window_size=10,
        discrete_action=True,
        is_validation=True,
        num_classes=6,
        instruction_preset="action_aware_train"
    )

    total_count = 0
    correct_count = 0
    pred_counts = {action_id: 0 for action_id in ACTION_CLASSES}
    gt_counts = {action_id: 0 for action_id in ACTION_CLASSES}
    correct_counts = {action_id: 0 for action_id in ACTION_CLASSES}
    confusion = np.zeros((6, 6), dtype=int)

    with torch.no_grad():
        for i in tqdm(range(200)): # Test first 200 items for speed
            try:
                sample = ds[i]
                batch = ds.collater([sample])
                gpu_batch = {k: v.cuda() if isinstance(v, torch.Tensor) else v for k, v in batch.items()}

                gt_id = parse_gt_label(gpu_batch)
                if gt_id is None: continue
                gt_id = min(gt_id, 5)

                outputs = model.forward_action(
                    vision_x=gpu_batch['rgb'],
                    lang_x=gpu_batch['text'],
                    attention_mask=gpu_batch['text_mask'].bool(),
                    vision_gripper=gpu_batch['hand_rgb'],
                    instr_and_action_ids=gpu_batch.get('instr_and_action_ids'),
                    instr_and_action_labels=gpu_batch.get('instr_and_action_labels'),
                    instr_and_action_mask=gpu_batch.get('instr_and_action_mask'),
                    mode="test",
                )

                result = parse_action_logits(outputs)
                if result is None: continue

                pred_id, _ = result
                pred_id = min(pred_id, 5)

                total_count += 1
                pred_counts[pred_id] += 1
                gt_counts[gt_id] += 1
                confusion[gt_id, pred_id] += 1
                if pred_id == gt_id:
                    correct_count += 1
                    correct_counts[gt_id] += 1

            except Exception:
                continue

    debug_print("\n" + "="*50)
    debug_print("📊 FINAL EVALUATION RESULTS (V5 Exp08)")
    debug_print(f"Total processed (first 200 items): {total_count}")
    debug_print(f"Accuracy: {correct_count/total_count:.4f}" if total_count > 0 else "No data")
    
    for action_id, name in ACTION_CLASSES.items():
        if gt_counts[action_id] > 0:
            acc = correct_counts[action_id]/gt_counts[action_id]
            debug_print(f"  {name:7}: {acc:7.4f} ({correct_counts[action_id]:2}/{gt_counts[action_id]:2})")
    
    debug_print("\nConfusion Matrix:")
    debug_print("      " + " ".join([f"{name[:1]}" for name in ACTION_CLASSES.values()]))
    for idx, row in enumerate(confusion):
        debug_print(f"{list(ACTION_CLASSES.values())[idx]:5} {row}")

if __name__ == "__main__":
    evaluate()

#!/usr/bin/env python3
"""
V5 Exp09 PM/DM 성능 평가 스크립트 (8-Class 통합 시스템)
"""
import os
import sys

os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["USE_FLASH_ATTENTION"] = "0"
os.environ["TRANSFORMERS_SKIP_VERSION_CHECK"] = "1"

# sys.path = [p for p in sys.path if ".local" not in p and "ros" not in p.lower()]
sys.path.insert(1, "/home/billy/25-1kp/MoNaVLA")
sys.path.insert(0, "/home/billy/25-1kp/MoNaVLA/third_party/RoboVLMs")

import torch
import numpy as np
from tqdm import tqdm
from PIL import Image, ImageDraw, ImageFont
import os

log_file = open("/home/billy/25-1kp/MoNaVLA/v5_exp09_pmdm_eval.log", "w")
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

# 설정 (Exp 09 최종 체크포인트)
CKPT_PATH = "/home/billy/25-1kp/MoNaVLA/runs/v5_nav/kosmos/mobile_vla_v5_8cls/2026-04-15/v5-exp09-8cls-balanced/last.ckpt"
CONFIG_PATH = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp09_8cls.json"
DATASET_PATH = "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v5"

# 8-Class 정의
ACTION_CLASSES = {
    0: "Stop", 
    1: "Forward", 
    2: "Left", 
    3: "Right", 
    4: "FL", 
    5: "FR",
    6: "Turn-L",
    7: "Turn-R"
}

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
        data_dir=DATASET_PATH,
        episode_pattern="episode_*.h5",
        model_name="kosmos",
        window_size=8, # V5-Exp09 standard
        discrete_action=True,
        is_validation=True,
        num_classes=8,
        instruction_preset="action_aware_train"
    )

    total_count = 0
    correct_count = 0
    pred_counts = {action_id: 0 for action_id in ACTION_CLASSES}
    gt_counts = {action_id: 0 for action_id in ACTION_CLASSES}
    correct_counts = {action_id: 0 for action_id in ACTION_CLASSES}
    confusion = np.zeros((8, 8), dtype=int)

    debug_print("Starting evaluation...")
    viz_dir = "/home/billy/25-1kp/MoNaVLA/runs/eval_viz/exp09"
    os.makedirs(viz_dir, exist_ok=True)
    viz_count = 0

    with torch.no_grad():
        for i in tqdm(range(len(ds))): # 모든 검증 시퀀스 평가
            try:
                sample = ds[i]
                batch = ds.collater([sample])
                gpu_batch = {k: v.cuda() if isinstance(v, torch.Tensor) else v for k, v in batch.items()}

                gt_id = parse_gt_label(gpu_batch)
                if gt_id is None: continue
                
                # Check bounds
                if gt_id >= 8: continue

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
                if pred_id >= 8: continue

                total_count += 1
                pred_counts[pred_id] += 1
                gt_counts[gt_id] += 1
                confusion[gt_id, pred_id] += 1
                if pred_id == gt_id:
                    correct_count += 1
                    correct_counts[gt_id] += 1
                
                # 시각화 저장 (처음 20개 샘플)
                if viz_count < 20:
                    try:
                        # [C, H, W] -> [H, W, C] (0-1 range)
                        img_tensor = batch['rgb'][0, -1] # window의 마지막 프레임
                        img_np = img_tensor.permute(1, 2, 0).cpu().numpy()
                        # 보통 RoboVLM은 이미지를 Normalize한 상태로 처리하므로 간단한 역정규화 필요할 수 있음
                        # 여기서는 단순 렌더링용이므로 0-1 가정을 하고 clipped 0-255 변환
                        img_np = (np.clip(img_np, 0, 1) * 255).astype(np.uint8)
                        img = Image.fromarray(img_np)
                        draw = ImageDraw.Draw(img)
                        
                        text = f"GT: {ACTION_CLASSES[gt_id]} | PRED: {ACTION_CLASSES[pred_id]}"
                        color = (0, 255, 0) if pred_id == gt_id else (255, 0, 0)
                        draw.rectangle([5, 5, 250, 25], fill=(0, 0, 0))
                        draw.text((10, 10), text, fill=color)
                        
                        img.save(os.path.join(viz_dir, f"sample_{i:03d}_gt{gt_id}_p{pred_id}.jpg"))
                        viz_count += 1
                    except Exception as ve:
                        pass

            except Exception as e:
                # debug_print(f"Error at index {i}: {e}")
                continue

    debug_print("\n" + "="*50)
    debug_print("📊 FINAL EVALUATION RESULTS (V5 Exp09 - 8-Class)")
    debug_print(f"Total processed: {total_count}")
    debug_print(f"Accuracy: {correct_count/total_count:.4f}" if total_count > 0 else "No data")
    
    for action_id, name in ACTION_CLASSES.items():
        if gt_counts[action_id] > 0:
            acc = correct_counts[action_id]/gt_counts[action_id]
            debug_print(f"  {name:7}: {acc:7.4f} ({correct_counts[action_id]:2}/{gt_counts[action_id]:2})")
    
    debug_print("\nConfusion Matrix:")
    debug_print("      " + " ".join([f"{name[:2]}" for name in ACTION_CLASSES.values()]))
    for idx, row in enumerate(confusion):
        debug_print(f"{list(ACTION_CLASSES.values())[idx]:7} {row}")
    debug_print("="*50)

if __name__ == "__main__":
    evaluate()

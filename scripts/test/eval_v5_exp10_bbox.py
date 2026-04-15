#!/usr/bin/env python3
"""
V5 Exp10 BBox 모델 성능 평가 스크립트 (Visual Servoing 기반)
"""
import os
import sys
import re

os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["USE_FLASH_ATTENTION"] = "0"
os.environ["TRANSFORMERS_SKIP_VERSION_CHECK"] = "1"

sys.path.insert(1, "/home/billy/25-1kp/MoNaVLA")
sys.path.insert(0, "/home/billy/25-1kp/MoNaVLA/third_party/RoboVLMs")

import torch
import numpy as np
from tqdm import tqdm
from PIL import Image, ImageDraw

log_file = open("/home/billy/25-1kp/MoNaVLA/v5_exp10_bbox_eval.log", "w")
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

from transformers import AutoProcessor

# 설정 (Exp 10 최종 체크포인트 - 실제로는 존재하지 않을 수 있으나 가정)
CKPT_PATH = "/home/billy/25-1kp/MoNaVLA/runs/v5_nav/kosmos/mobile_vla_v5_bbox/2026-04-15/v5-exp10-track2-bbox/last.ckpt"
CONFIG_PATH = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp10_bbox.json"
DATASET_PATH = "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v5"

def parse_bbox_from_text(text):
    match = re.search(r"<box_2d>\s*<patch_index_(\d+)>\s*<patch_index_(\d+)>\s*</box_2d>", text)
    if match:
        p1 = int(match.group(1))
        p2 = int(match.group(2))
        return p1, p2
    return None, None

def calculate_p_control(p1, p2):
    x1, y1 = p1 % 32, p1 // 32
    x2, y2 = p2 % 32, p2 // 32
    
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    
    # 32x32 그리드, 중앙은 15.5
    err_x = cx - 15.5
    
    Kp_ang = -0.1
    angular_z = Kp_ang * err_x
    linear_x = 0.5
    
    return linear_x, angular_z, cx, cy

def evaluate():
    from robovlms.model.backbone.base_backbone import load_config
    configs = load_config(CONFIG_PATH)
    configs["model_path"] = "microsoft/kosmos-2-patch14-224"
    if "tokenizer" not in configs: configs["tokenizer"] = {}
    configs["tokenizer"]["pretrained_model_name_or_path"] = "microsoft/kosmos-2-patch14-224"
    if "vlm" not in configs: configs["vlm"] = {}
    configs["vlm"]["pretrained_model_name_or_path"] = "microsoft/kosmos-2-patch14-224"

    trainer = MobileVLATrainer(configs)
    
    if os.path.exists(CKPT_PATH):
        debug_print(f"Loading checkpoint: {os.path.basename(CKPT_PATH)}")
        checkpoint = torch.load(CKPT_PATH, map_location="cpu")
        state_dict = checkpoint.get("state_dict", checkpoint)
        if any(k.startswith("model.") for k in state_dict.keys()):
            state_dict = {k[6:] if k.startswith("model.") else k: v for k, v in state_dict.items()}
            
        load_result = trainer.model.load_state_dict(state_dict, strict=False)
        print(f"Loaded checkpoint from {CKPT_PATH}")
        
        # LoRA 가중치가 실제로 로드되었는지 확인
        for name, param in trainer.model.named_parameters():
            if "lora_A" in name:
                print(f"LoRA Weight Sample ({name}): mean={param.mean().item():.6f}, std={param.std().item():.6f}")
                break
        else:
            print("WARNING: No LoRA weights found in the model!")
    else:
        debug_print(f"Checkpoint not found at {CKPT_PATH}. Running with blank initialized weights for testing pipeline.")
        
    model = trainer.model.to('cuda:0')
    model.eval()
    
    processor = AutoProcessor.from_pretrained("microsoft/kosmos-2-patch14-224")

    from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset
    ds = MobileVLAH5Dataset(
        data_dir=DATASET_PATH,
        episode_pattern="episode_*.h5",
        model_name="kosmos",
        window_size=1, # Exp10 uses window size 1
        discrete_action=False,
        use_bbox_target=True,
        is_validation=True,
        instruction_preset="action_aware_train",
        tokenizer=processor.tokenizer
    )

    total_count = 0
    valid_format_count = 0
    error_sum = 0.0

    debug_print("Starting evaluation...")
    viz_dir = "/home/billy/25-1kp/MoNaVLA/runs/eval_viz/exp10"
    os.makedirs(viz_dir, exist_ok=True)
    viz_count = 0

    with torch.no_grad():
        for i in tqdm(range(len(ds))):
            try:
                sample = ds[i]
                batch = ds.collater([sample])
                gpu_batch = {k: v.cuda() if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
                
                # 정답(GT) 텍스트 가져오기
                gt_text_ids = sample['text']
                gt_text_ids = gt_text_ids[gt_text_ids != 0]
                gt_text_ids = gt_text_ids[gt_text_ids != 0]
                gt_text = processor.tokenizer.decode(gt_text_ids)
                
                gt_p1, gt_p2 = parse_bbox_from_text(gt_text)
                gt_bboxes = []
                if gt_p1 is not None and gt_p2 is not None:
                    # [ymin, xmin, ymax, xmax]
                    y1, x1 = (gt_p1 // 32) * 1000 // 32, (gt_p1 % 32) * 1000 // 32
                    y2, x2 = (gt_p2 // 32) * 1000 // 32, (gt_p2 % 32) * 1000 // 32
                    gt_bboxes.append([y1, x1, y2, x2])
                    gt_linear, gt_angular, gt_cx, gt_cy = calculate_p_control(gt_p1, gt_p2)
                else:
                    gt_linear, gt_angular, gt_cx, gt_cy = 0.0, 0.0, 500.0, 500.0

                # inference (Text generation!)
                # Prompt for BBox Grounding
                instruction = sample.get('raw_text', "Locate the gray basket.")
                
                # De-normalize image from [C, H, W] tensor (normalized) to PIL
                mean = torch.tensor([0.48145466, 0.4578275, 0.40821073]).view(3, 1, 1)
                std = torch.tensor([0.26862954, 0.26130258, 0.27577711]).view(3, 1, 1)
                img_tensor = (sample['rgb'][0].cpu() * std + mean).clamp(0, 1)
                from torchvision.transforms import ToPILImage
                image_input = ToPILImage()(img_tensor)
                
                input_text_prompt = f"Instruction: {instruction} Action: "
                inputs = processor(text=input_text_prompt, images=image_input, return_tensors="pt").to('cuda:0')
                
                outputs = model.model.generate(
                    pixel_values=inputs['pixel_values'],
                    input_ids=inputs['input_ids'],
                    attention_mask=inputs['attention_mask'],
                    image_embeds_position_mask=inputs.get('image_embeds_position_mask'),
                    max_new_tokens=32,
                    use_cache=True
                )
                
                # 예측 텍스트 파싱
                pred_ids = outputs[0]
                pred_text = processor.tokenizer.decode(pred_ids, skip_special_tokens=False)
                pred_p1, pred_p2 = parse_bbox_from_text(pred_text)
                pred_bboxes = []
                if pred_p1 is not None and pred_p2 is not None:
                    py1, px1 = (pred_p1 // 32) * 1000 // 32, (pred_p1 % 32) * 1000 // 32
                    py2, px2 = (pred_p2 // 32) * 1000 // 32, (pred_p2 % 32) * 1000 // 32
                    pred_bboxes.append([py1, px1, py2, px2])
                debug_print(f"Full Pred Text: {pred_text}")
                
                debug_print(f"Index {i:03d} | GT: {gt_text.split('.')[-1].strip()} | Pred: {pred_text.split('Action:')[-1].strip() if 'Action:' in pred_text else pred_text}")
                
                total_count += 1
                if pred_p1 is not None:
                    valid_format_count += 1
                    pred_linear, pred_angular, pred_cx, pred_cy = calculate_p_control(pred_p1, pred_p2)
                    debug_print(f"         └─> P-Control -> GT: [v={gt_linear:.2f}, w={gt_angular:.2f}] | PRED: [v={pred_linear:.2f}, w={pred_angular:.2f}]")
                    error_sum += abs(gt_cx - pred_cx) + abs(gt_cy - pred_cy)
                else:
                    debug_print(f"         └─> P-Control -> Invalid format, skipping action calculation")

            except Exception as e:
                import traceback
                traceback.print_exc()
                continue

    debug_print("\n" + "="*50)
    debug_print("📊 FINAL EVALUATION RESULTS (V5 Exp10 - BBox Visual Servoing)")
    debug_print(f"Total evaluated frames: {total_count}")
    debug_print(f"Valid format outputs: {valid_format_count} ({valid_format_count/total_count*100:.1f}%)" if total_count > 0 else "No Valid outputs")
    if valid_format_count > 0:
        debug_print(f"Average Pixel Grid Center Error (Manhattan in 32x32): {error_sum/valid_format_count:.2f}")
    debug_print("="*50)

if __name__ == "__main__":
    evaluate()

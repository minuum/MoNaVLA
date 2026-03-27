#!/usr/bin/env python3
"""
V4 PM/DM 성능 평가 스크립트 (v6 - action logit shape 올바르게 파싱)

핵심 수정:
  - act_head output: (B, window_size, fwd_pred_next_n, num_classes)
  - 추론 시: 마지막 window[-1], 마지막 chunk step[-1]의 num_classes 차원에서 argmax
  - GT 파싱: action_chunck[0, -1, -1] = 마지막 window의 마지막 타임스텝 label
"""
import os
import sys

os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["USE_FLASH_ATTENTION"] = "0"
os.environ["TRANSFORMERS_SKIP_VERSION_CHECK"] = "1"

sys.path = [p for p in sys.path if ".local" not in p and "ros" not in p.lower()]
sys.path.insert(0, "/home/billy/anaconda3/envs/openvla/lib/python3.10/site-packages")
sys.path.insert(1, "/home/billy/25-1kp/MoNaVLA")
sys.path.insert(0, "/home/billy/25-1kp/MoNaVLA/third_party/RoboVLMs")

import sys
import os
import torch
import numpy as np
from tqdm import tqdm
import json

# Log everything to a file as well
log_file = open("/home/billy/25-1kp/MoNaVLA/v4_eval_debug.log", "w")
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
CKPT_PATH = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_balanced_v1/2026-03-24/v4-balanced-v1/epoch_epoch=epoch=02-val_loss=val_loss=3.193.ckpt"
CONFIG_PATH = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v4_balanced_v1.json"
DATASET_PATH = "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v3"

ACTION_CLASSES = {0: "Stop", 1: "Forward", 2: "Left", 3: "Right", 4: "FL", 5: "FR"}

def parse_action_logits(outputs):
    """
    MobileVLAClassificationDecoder output 파싱

    _forward_action_head()가 action_logits, action_loss를 반환할 때,
    action_logits = act_head.forward()의 반환값 = (logits_tensor, None) 튜플!

    실제 logit tensor shape: (B, window_size, fwd_pred_next_n, num_classes)
    추론: 마지막 window[-1], 마지막 chunk step[-1]에서 argmax
    """
    if outputs is None:
        return None

    # tuple/list이면 첫 번째 원소가 실제 logit tensor
    if isinstance(outputs, (tuple, list)):
        outputs = outputs[0]

    if outputs is None:
        return None

    if not isinstance(outputs, torch.Tensor):
        return None

    pred_np = outputs.detach().cpu().float().numpy()

    ndim = pred_np.ndim
    if ndim == 4:
        # (B, seq_len, chunk_n, num_classes) -> 마지막 window, 마지막 chunk step
        class_logits = pred_np[0, -1, -1, :]  # (num_classes,)
    elif ndim == 3:
        # (B, chunk_n, num_classes)
        class_logits = pred_np[0, -1, :]  # (num_classes,)
    elif ndim == 2:
        # (B, num_classes)
        class_logits = pred_np[0, :]  # (num_classes,)
    elif ndim == 1:
        class_logits = pred_np
    else:
        return None

    return int(np.argmax(class_logits)), class_logits

def parse_gt_label(gpu_batch):
    """
    collater output에서 GT label 파싱

    action_chunck shape: (B, num_windows, chunk_size) [discrete]
    구조:
      action_chunck[:, 0] = [a0, a1, ..., a9] : 각 window의 첫 타임스텝 (실제 action)
      action_chunck[:, 1:] = 대부분 0 (패딩)

    GT: 마지막 window[-1]의 첫 번째 타임스텝[0]
    (모델이 window i를 보고 예측하는 다음 action = chunk_step[0])
    """
    if 'action_chunck' in gpu_batch:
        ac = gpu_batch['action_chunck']  # (B, num_windows, chunk_size)
        ac_np = ac.detach().cpu().numpy()
        # 마지막 window, 첫 번째 step = 실제 GT action (패딩 아님)
        gt = int(ac_np[0, -1, 0])
        return gt
    elif 'action' in gpu_batch:
        a = gpu_batch['action']
        a_np = a.detach().cpu().numpy()
        # window_size번째 index = 첫 번째 예측 대상
        gt = int(a_np[0, -1])
        return gt
    return None

def evaluate():
    print(f"🚀 V4 PM/DM Test v6 - correct logit shape parsing")
    print(f"   Checkpoint: {CKPT_PATH.split('/')[-1]}")

    # [수정] parent 설정을 재귀적으로 읽기 위해 load_config 사용
    from robovlms.model.backbone.base_backbone import load_config
    configs = load_config(CONFIG_PATH)
    
    # 로컬 경로 유실 대응: 부모 설정이 있더라도 HF ID로 강제 교체
    configs["model_path"] = "microsoft/kosmos-2-patch14-224"
    if "tokenizer" not in configs: configs["tokenizer"] = {}
    configs["tokenizer"]["pretrained_model_name_or_path"] = "microsoft/kosmos-2-patch14-224"
    if "vlm" not in configs: configs["vlm"] = {}
    configs["vlm"]["pretrained_model_name_or_path"] = "microsoft/kosmos-2-patch14-224"

    print(f"🔧 Overriding paths: using official microsoft/kosmos-2-patch14-224")
    
    trainer = MobileVLATrainer(configs)
    
    # 가중치 로드
    checkpoint = torch.load(CKPT_PATH, map_location="cpu")
    state_dict = checkpoint.get("state_dict", checkpoint)
    # lightning prefix 제거 (필요할 경우)
    if any(k.startswith("model.") for k in state_dict.keys()):
        state_dict = {k[6:] if k.startswith("model.") else k: v for k, v in state_dict.items()}
        
    trainer.model.load_state_dict(state_dict, strict=True)
    model = trainer.model.to('cuda:0')
    model.eval()

    fwd_pred_next_n = model.act_head_configs.get("fwd_pred_next_n", 5)
    num_classes = model.act_head_configs.get("num_classes", 9)
    action_space = model.act_head_configs.get("action_space", "continuous")
    print(f"\n📐 Model config: action_space={action_space}, fwd_pred_next_n={fwd_pred_next_n}, num_classes={num_classes}")

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

    print(f"📊 Dataset size: {len(ds)}")

    # Evaluate
    model.eval()
    
    # Initialize metrics
    total_count = 0
    correct_count = 0
    pred_counts = {action_id: 0 for action_id in ACTION_CLASSES}
    gt_counts = {action_id: 0 for action_id in ACTION_CLASSES}
    correct_counts = {action_id: 0 for action_id in ACTION_CLASSES}
    confusion = np.zeros((6, 6), dtype=int)

    with torch.no_grad():
        for i in tqdm(range(len(ds)), desc="V4 Eval v6"):
            try:
                sample = ds[i]
                batch = ds.collater([sample])
                gpu_batch = {k: v.cuda() if isinstance(v, torch.Tensor) else v for k, v in batch.items()}

                gt_id = parse_gt_label(gpu_batch)
                if gt_id is None:
                    continue
                gt_id = min(gt_id, 5)

                # Inference
                if i == 0:
                    print(f"\n🚨 [PROMPT CHECK]: {gpu_batch.get('raw_text', 'MISSING')}")

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
                if result is None:
                    continue

                pred_id, class_logits = result
                pred_id = min(pred_id, 5)

                # Update stats
                total_count += 1
                pred_counts[pred_id] += 1
                gt_counts[gt_id] += 1
                confusion[gt_id, pred_id] += 1
                
                if pred_id == gt_id:
                    correct_count += 1
                    correct_counts[gt_id] += 1

                if i % 5 == 0 or i < 10:
                    print(f"  [{i}] GT={gt_id}({ACTION_CLASSES.get(gt_id,'?')}) | PRED={pred_id}({ACTION_CLASSES.get(pred_id,'?')}) | Logits={np.round(class_logits, 2)} {'✅' if pred_id==gt_id else '❌'}")

            except Exception as e:
                if i < 5:
                    debug_print(f"  ❌ Error at {i}: {e}")

    debug_print("\n" + "="*50)
    debug_print("📊 FINAL EVALUATION RESULTS (Balanced Model)")
    debug_print("="*50)
    debug_print(f"Total processed: {total_count}")
    debug_print(f"Overall Accuracy (PM): {correct_count/total_count:.4f}" if total_count > 0 else "No data")
    
    debug_print("\nAction-wise Accuracy:")
    for action_id, name in ACTION_CLASSES.items():
        if gt_counts[action_id] > 0:
            acc = correct_counts[action_id]/gt_counts[action_id]
            debug_print(f"  {name:7}: {acc:7.4f} ({correct_counts[action_id]:2}/{gt_counts[action_id]:2})")
        
    debug_print("\nPrediction Distribution:")
    for action_id, name in ACTION_CLASSES.items():
        debug_print(f"  {name:7}: {pred_counts[action_id]:2}")

    debug_print("\nConfusion Matrix (Rows=GT, Cols=Pred):")
    debug_print("      " + " ".join([f"{name[:1]}" for name in ACTION_CLASSES.values()]))
    for idx, row in enumerate(confusion):
        name = list(ACTION_CLASSES.values())[idx]
        debug_print(f"{name:5} {row}")

if __name__ == "__main__":
    debug_print("🎬 Starting script execution...")
    try:
        evaluate()
    except Exception as e:
        debug_print(f"❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    debug_print("🏁 Script execution finished.")

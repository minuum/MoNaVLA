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

import json
import torch
import numpy as np
from tqdm import tqdm

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
CKPT_PATH = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_hybrid/2026-03-20/v4-hybrid-final/epoch_epoch=epoch=04-val_loss=val_loss=0.702.ckpt"
CONFIG_PATH = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v4_hybrid_final.json"
DATASET_PATH = "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v3"

ACTION_CLASSES = {0:"Stop",1:"Forward",2:"Backward",3:"Left",4:"Right",5:"FL",6:"FR",7:"BL",8:"BR"}

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

    trainer = MobileVLATrainer.load_from_checkpoint(CKPT_PATH, config_path=CONFIG_PATH, map_location="cuda")
    model = trainer.model.to('cuda')
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
        is_validation=True
    )

    print(f"📊 Dataset size: {len(ds)}")

    confusion = np.zeros((9, 9), dtype=int)
    pm_count = 0
    total = 0
    error_count = 0

    with torch.no_grad():
        for i in tqdm(range(len(ds)), desc="V4 Eval v6"):
            try:
                sample = ds[i]
                batch = ds.collater([sample])
                gpu_batch = {k: v.cuda() if isinstance(v, torch.Tensor) else v for k, v in batch.items()}

                gt_label = parse_gt_label(gpu_batch)
                if gt_label is None:
                    continue
                gt_label = min(gt_label, 8)

                # 추론
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
                    error_count += 1
                    continue

                pred_class, class_logits = result
                pred_class = min(pred_class, 8)

                confusion[gt_label, pred_class] += 1
                total += 1
                if pred_class == gt_label:
                    pm_count += 1

                if i < 10:
                    print(f"  [{i}] GT={gt_label}({ACTION_CLASSES.get(gt_label,'?')}) | PRED={pred_class}({ACTION_CLASSES.get(pred_class,'?')}) | logits={np.round(class_logits, 2)} {'✅' if pred_class==gt_label else '❌'}")

            except Exception as e:
                error_count += 1
                if i < 5:
                    print(f"  ❌ Error at {i}: {e}")

    print(f"\n{'='*70}")
    print(f"V4 Hybrid Model Evaluation (v6)")
    print(f"{'='*70}")
    print(f"Total Tested : {total} | Errors: {error_count}")
    if total == 0:
        print("❌ No successful samples!")
        return

    pm_rate = pm_count / total * 100
    print(f"Overall PM   : {pm_rate:.2f}% ({pm_count}/{total})")
    print(f"\n{'-'*70}")
    print(f"{'Class':<10} | {'GT_cnt':>6} | {'Correct':>7} | {'Accuracy':>10}")
    print(f"{'-'*70}")
    for c, name in ACTION_CLASSES.items():
        gt_total = int(np.sum(confusion[c, :]))
        correct = int(confusion[c, c])
        acc = correct / gt_total * 100 if gt_total > 0 else 0
        print(f"{name:<10} | {gt_total:>6} | {correct:>7} | {acc:>8.2f}%")

    print(f"\nConfusion Matrix (row=GT, col=PRED):")
    header = "GT\\PRED  " + "".join(f"{ACTION_CLASSES[c][:3]:>6}" for c in range(9))
    print(header)
    for r in range(9):
        row = f"{ACTION_CLASSES[r][:4]:<8} " + "".join(f"{confusion[r,c]:>6}" for c in range(9))
        print(row)

if __name__ == "__main__":
    evaluate()

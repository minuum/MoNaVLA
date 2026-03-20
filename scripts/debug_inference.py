#!/usr/bin/env python3
"""
V4 Hybrid 추론 파이프라인 단계별 디버깅
- action head 출력 shape/값 확인
- label vs pred 분포 비교
- _forward_action_head 반환값 추적
"""
import os, sys

os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["USE_FLASH_ATTENTION"] = "0"

sys.path = [p for p in sys.path if '.local' not in p and 'ros' not in p.lower()]
sys.path.insert(0, '/home/billy/anaconda3/envs/openvla/lib/python3.10/site-packages')
sys.path.insert(1, '/home/billy/25-1kp/MoNaVLA')
sys.path.insert(0, '/home/billy/25-1kp/MoNaVLA/third_party/RoboVLMs')

import json
import torch
import numpy as np

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

CKPT = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_hybrid/2026-03-20/v4-hybrid-final/epoch_epoch=epoch=04-val_loss=val_loss=0.702.ckpt"
CONFIG = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v4_hybrid_final.json"

print("=" * 70)
print("STEP 1: 모델 로드")
print("=" * 70)
trainer = MobileVLATrainer.load_from_checkpoint(CKPT, config_path=CONFIG, map_location="cuda")
model = trainer.model.to('cuda')
model.eval()

print(f"act_head_configs: {model.act_head_configs}")
print(f"act_head type: {type(model.act_head).__name__}")
print(f"action_space: {model.act_head_configs.get('action_space', 'N/A')}")

print("\n" + "=" * 70)
print("STEP 2: 데이터 로드 및 label 분포 확인")
print("=" * 70)

from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset

ds = MobileVLAH5Dataset(
    data_dir='/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v3',
    episode_pattern='episode_*.h5',
    model_name='kosmos',
    window_size=10,
    discrete_action=True,
    is_validation=True
)

# 전체 label 분포
all_labels = []
ACTION_NAMES = {0:"Stop",1:"Forward",2:"Backward",3:"Left",4:"Right",5:"FL",6:"FR",7:"BL",8:"BR"}
for i in range(len(ds)):
    s = ds[i]
    a = s['actions']  # shape (20,)
    last_label = int(a[-1])
    all_labels.append(last_label)

all_labels = np.array(all_labels)
print(f"총 {len(all_labels)}개 샘플 label 분포:")
for c, name in ACTION_NAMES.items():
    n = np.sum(all_labels == c)
    print(f"  {name:<10}: {n:3d} ({n/len(all_labels)*100:.1f}%)")

print("\n" + "=" * 70)
print("STEP 3: 추론 파이프라인 단계별 trace (첫 3개 샘플)")
print("=" * 70)

# _forward_action_head 패치로 내부 추적
original_fah = model._forward_action_head
call_count = [0]

def debug_forward_action_head(action_hs, action_labels=None, action_mask=None):
    call_count[0] += 1
    print(f"\n  [_forward_action_head call #{call_count[0]}]")
    print(f"    action_hs shape: {action_hs.shape}")
    print(f"    action_hs mean/std: {action_hs.float().mean().item():.4f} / {action_hs.float().std().item():.4f}")
    if action_labels is not None:
        print(f"    action_labels: {action_labels}")
    logits, loss = original_fah(action_hs, action_labels, action_mask)
    if logits is not None:
        print(f"    output logits shape: {logits.shape}")
        print(f"    logits values (last step): {logits[0, -1].detach().cpu().numpy()}")
        pred = int(torch.argmax(logits[0, -1]).item())
        print(f"    predicted class: {pred} ({ACTION_NAMES.get(pred, '?')})")
    return logits, loss

model._forward_action_head = debug_forward_action_head

with torch.no_grad():
    for i in range(3):
        sample = ds[i]
        batch = ds.collater([sample])
        gpu_batch = {k: v.cuda() if isinstance(v, torch.Tensor) else v for k, v in batch.items()}

        gt_label = int(gpu_batch['actions'][0, -1])
        print(f"\n--- Sample {i} | GT: {gt_label} ({ACTION_NAMES.get(gt_label,'?')}) ---")

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

        if outputs is not None and isinstance(outputs, torch.Tensor):
            out = outputs.detach().cpu().numpy()
            print(f"  forward_action output shape: {out.shape}")
            print(f"  forward_action output values: {out[0]}")
            if out.ndim == 3:
                pred_class = int(np.argmax(out[0, -1]))
            elif out.ndim == 2:
                pred_class = int(np.argmax(out[0]))
            else:
                pred_class = int(np.argmax(out))
            print(f"  FINAL PRED: {pred_class} ({ACTION_NAMES.get(pred_class,'?')}) | GT: {gt_label} ({ACTION_NAMES.get(gt_label,'?')}) {'✅' if pred_class==gt_label else '❌'}")
        else:
            print(f"  forward_action returned: {type(outputs)}")

print("\n" + "=" * 70)
print("STEP 4: train 모드로도 한번 실행 (loss가 제대로 나오는지)")
print("=" * 70)

sample = ds[0]
batch = ds.collater([sample])
gpu_batch = {k: v.cuda() if isinstance(v, torch.Tensor) else v for k, v in batch.items()}

# actions을 action_labels 형태로 변환
gt_label = int(gpu_batch['actions'][0, -1])
print(f"GT label: {gt_label} ({ACTION_NAMES.get(gt_label,'?')})")
print(f"actions batch shape: {gpu_batch['actions'].shape}")
print(f"actions values (last 5): {gpu_batch['actions'][0, -5:]}")

print("\nDone!")

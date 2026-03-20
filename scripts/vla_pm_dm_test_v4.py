#!/usr/bin/env python3
"""
V4 PM/DM 성능 평가 스크립트 (v5 - mode 파라미터 방식으로 정상화)

변경 이력:
  v1~v4: 멍키패치(monkey-patch) 방식으로 NoneType 에러 우회 시도
  v5: base_backbone.py의 forward_discrete/forward_action에 mode 파라미터 추가로 근본 해결
      - 멍키패치 전면 제거
      - model(**inputs, mode="test")로 추론 모드 직접 지정
"""
import os
import sys

# [중요] CUDA Symbol Error 방지를 위해 flash-attn 비활성화
os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["USE_FLASH_ATTENTION"] = "0"
os.environ["TRANSFORMERS_SKIP_VERSION_CHECK"] = "1"
os.environ["BITSANDBYTES_NOWELCOME"] = "1"

# [중요] Conda 환경의 site-packages와 프로젝트 루트를 최우선 순위로 설정
conda_site_packages = "/home/billy/anaconda3/envs/openvla/lib/python3.10/site-packages"
project_root = "/home/billy/25-1kp/MoNaVLA"

# .local 경로나 ROS 경로가 sys.path에 있으면 무조건 제거 (버전 충돌의 근원)
sys.path = [p for p in sys.path if ".local" not in p and "ros" not in p.lower()]

# 우리가 원하는 경로만 최상단에 배치
if conda_site_packages not in sys.path:
    sys.path.insert(0, conda_site_packages)
else:
    sys.path.remove(conda_site_packages)
    sys.path.insert(0, conda_site_packages)

if project_root not in sys.path:
    sys.path.insert(1, project_root)
else:
    sys.path.remove(project_root)
    sys.path.insert(1, project_root)

# RoboVLMs 경로 설정
sys.path.insert(0, os.path.abspath('third_party/RoboVLMs'))
# 커스텀 패키지 경로 (robovlm_nav)
sys.path.insert(0, os.path.abspath('.'))

import json
import torch
import numpy as np
from tqdm import tqdm
from pathlib import Path
import h5py
from PIL import Image

from robovlms.train.mobile_vla_trainer import MobileVLATrainer
from robovlms.utils.model_utils import build_tokenizer

# 모델 백본 주입
from robovlms.model.backbone.robokosmos import RoboKosMos
import robovlms.model.backbone as backbone
setattr(backbone, "RoboVLM-Nav", RoboKosMos)

# Policy Head 주입
import robovlms.model.policy_head as policy_head
from robovlm_nav.models.policy_head.nav_policy_impl import MobileVLAClassificationDecoder, MobileVLALSTMDecoder
setattr(policy_head, "NavPolicy", MobileVLAClassificationDecoder)
setattr(policy_head, "NavPolicyRegression", MobileVLALSTMDecoder)

# Tokenizer 패치
import robovlms.utils.model_utils as mode_utils
orig_dtc = mode_utils.default_tokenizer_config
def default_tokenizer_config_patch(tokenizer):
    if tokenizer == 'kosmos':
        return {'type': 'AutoProcessor', 'pretrained_model_name_or_path': 'microsoft/kosmos-2-patch14-224', 'tokenizer_type': 'kosmos'}
    return orig_dtc(tokenizer)
mode_utils.default_tokenizer_config = default_tokenizer_config_patch

# 설정
CKPT_PATH = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_hybrid/2026-03-20/v4-hybrid-final/epoch_epoch=epoch=04-val_loss=val_loss=0.702.ckpt"
CONFIG_PATH = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v4_hybrid_final.json"
DATASET_PATH = "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v3"
NUM_SAMPLES = 50

# 액션 매핑 (9-class)
ACTION_CLASSES = {
    0: "Stop",
    1: "Forward",
    2: "Backward",
    3: "Left",
    4: "Right",
    5: "FL",
    6: "FR",
    7: "BL",
    8: "BR"
}

def evaluate():
    print(f"🚀 V4 PM/DM Test Loading (v5 - mode-param approach)...")
    if not os.path.exists(CKPT_PATH):
        print(f"❌ Checkpoint not found: {CKPT_PATH}")
        return

    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

    # Trainer 로드
    trainer = MobileVLATrainer.load_from_checkpoint(CKPT_PATH, config_path=CONFIG_PATH, map_location="cuda")
    model = trainer.model.to('cuda')
    model.eval()

    # 데이터셋 설정
    from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset as NavH5DatasetImpl

    ds = NavH5DatasetImpl(
        data_dir=DATASET_PATH,
        episode_pattern="episode_*.h5",
        model_name="kosmos",
        window_size=10,
        discrete_action=True,
        is_validation=True
    )

    # 테스트 샘플 추출
    num_eval = min(NUM_SAMPLES, len(ds))
    indices = np.random.choice(len(ds), num_eval, replace=False)

    confusion_matrix = np.zeros((9, 9))
    print(f"📊 Testing {num_eval} samples with NUM_SAMPLES={NUM_SAMPLES}...")

    pm_count = 0
    success_count = 0
    none_count = 0

    with torch.no_grad():
        for i, idx in enumerate(tqdm(indices, desc="V4 PM/DM Eval")):
            sample = ds[idx]
            batch = ds.collater([sample])
            gpu_batch = {k: v.cuda() if isinstance(v, torch.Tensor) else v for k, v in batch.items()}

            # [핵심 수정] mode="test"를 data_source와 함께 전달
            # BaseRoboVLM.forward -> forward_action(mode="test") -> forward_discrete(mode="test")
            # forward_discrete에서 mode != "train"이면 action_logits 직접 반환
            forward_inputs = {
                'vision_x': gpu_batch['rgb'],
                'lang_x': gpu_batch['text'],
                'attention_mask': gpu_batch['text_mask'].bool(),
                'vision_gripper': gpu_batch['hand_rgb'],
                'data_source': ['action'],
            }

            # forward_action을 직접 호출하여 mode="test" 전달 (가장 안전한 경로)
            outputs = model.forward_action(
                vision_x=gpu_batch['rgb'],
                lang_x=gpu_batch['text'],
                attention_mask=gpu_batch['text_mask'].bool(),
                vision_gripper=gpu_batch['hand_rgb'],
                instr_and_action_ids=gpu_batch.get('instr_and_action_ids'),
                instr_and_action_labels=gpu_batch.get('instr_and_action_labels'),
                instr_and_action_mask=gpu_batch.get('instr_and_action_mask'),
                mode="test",  # [핵심] 추론 모드 직접 지정
            )

            # Output 파싱
            if outputs is None:
                none_count += 1
                print(f"⚠️ Sample {idx}: model returned None")
                continue

            if isinstance(outputs, dict):
                raw_pred = outputs.get('action_logits', outputs.get('logits'))
            elif isinstance(outputs, (list, tuple)):
                raw_pred = outputs[0] if len(outputs) > 0 else None
            elif isinstance(outputs, torch.Tensor):
                raw_pred = outputs
            else:
                none_count += 1
                print(f"⚠️ Sample {idx}: unexpected output type {type(outputs)}")
                continue

            if raw_pred is None:
                none_count += 1
                print(f"⚠️ Sample {idx}: raw_pred is None")
                continue

            pred_np = raw_pred.detach().cpu().numpy()
            # shape: (bs, 1, action_dim) 또는 (bs, action_dim) 처리
            if pred_np.ndim == 3:
                pred_class_id = int(np.argmax(pred_np[0, -1, :]))
            elif pred_np.ndim == 2:
                pred_class_id = int(np.argmax(pred_np[0, :]))
            else:
                pred_class_id = int(np.argmax(pred_np))

            # Ground Truth 파싱
            gt_np = gpu_batch['action_chunck'].detach().cpu().numpy()
            gt_val = gt_np[0, -1]  # 마지막 타임스텝의 action
            if hasattr(gt_val, '__len__') and len(gt_val) > 1:
                # continuous vector인 경우 첫 번째 값이 class index
                gt_class_id = int(gt_val[0])
            else:
                gt_class_id = int(gt_val)

            final_gt = min(gt_class_id, 8)  # 9-class 범위 클램핑
            final_pred = min(pred_class_id, 8)

            confusion_matrix[final_gt, final_pred] += 1
            success_count += 1

            if i < 20:  # 처음 20개만 상세 출력
                print(f"  Sample {idx}: GT={final_gt}({ACTION_CLASSES.get(final_gt,'?')}), PRED={final_pred}({ACTION_CLASSES.get(final_pred,'?')}) {'✅' if final_gt==final_pred else '❌'}")
            if final_pred == final_gt:
                pm_count += 1

    print(f"\n🏁 Tested: {success_count} samples (None skipped: {none_count})")
    if success_count == 0:
        print("❌ No successful samples. Check model/data configuration.")
        return

    print("\n" + "="*70)
    print(f"V4 Model Performance (Discrete PM)")
    print(f"Total Samples Tested : {success_count}")
    print(f"Overall PM Rate      : {pm_count/success_count*100:.2f}%")
    print("-" * 70)
    print(f"{'Class':<10} | {'GT':>5} | {'Pred':>5} | {'Accuracy':>10}")
    print("-" * 70)

    for c, name in ACTION_CLASSES.items():
        gt_total = np.sum(confusion_matrix[c, :])
        pred_total = np.sum(confusion_matrix[:, c])
        matches = confusion_matrix[c, c]
        acc = (matches / gt_total * 100) if gt_total > 0 else 0.0
        print(f"{name:<10} | {int(gt_total):>5} | {int(pred_total):>5} | {acc:>8.2f}%")

    print("="*70)

if __name__ == "__main__":
    evaluate()

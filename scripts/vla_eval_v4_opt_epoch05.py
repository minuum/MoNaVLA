#!/usr/bin/env python3
import os
import sys
import json
import torch
import numpy as np
from tqdm import tqdm

# 환경 설정
os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["USE_FLASH_ATTENTION"] = "0"
os.environ["TRANSFORMERS_SKIP_VERSION_CHECK"] = "1"

# sys.path 조작 제거 (환경 실행 시 PYTHONPATH로 대체)

from robovlms.train.mobile_vla_trainer import MobileVLATrainer
import robovlms.model.backbone as backbone
from robovlms.model.backbone.robokosmos import RoboKosMos
setattr(backbone, "RoboVLM-Nav", RoboKosMos)

import robovlms.model.policy_head as policy_head
from robovlm_nav.models.policy_head.nav_policy_impl import MobileVLAClassificationDecoder, MobileVLALSTMDecoder
setattr(policy_head, "NavPolicy", MobileVLAClassificationDecoder)
setattr(policy_head, "NavPolicyRegression", MobileVLALSTMDecoder)

# 설정 (최신 최고 성능 Epoch 10 체크포인트)
CKPT_PATH = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_hybrid_opt/2026-03-20/v4-hybrid-opt-6cls/epoch_epoch=epoch=13-val_loss=val_loss=0.943.ckpt"
# ... (parse_action_logits는 그대로 유지)
CONFIG_PATH = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v4_hybrid_opt.json"

# 6클래스 매핑
ACTION_CLASSES = {
    0: "Stop", 
    1: "Forward", 
    2: "Left", 
    3: "Right", 
    4: "Forward-Left", 
    5: "Forward-Right"
}

def parse_action_logits(outputs):
    if outputs is None: return None
    if isinstance(outputs, (tuple, list)): outputs = outputs[0]
    pred_np = outputs.detach().cpu().float().numpy()
    ndim = pred_np.ndim
    if ndim == 4: class_logits = pred_np[0, -1, -1, :]
    elif ndim == 3: class_logits = pred_np[0, -1, :]
    elif ndim == 2: class_logits = pred_np[0, :]
    else: return None
    return int(np.argmax(class_logits)), class_logits

def load_config(path):
    with open(path, "r") as f:
        cfg = json.load(f)
    if "parent" in cfg and cfg["parent"]:
        parent_path = os.path.join(os.path.dirname(path), os.path.basename(cfg["parent"]))
        if not os.path.exists(parent_path):
            parent_path = os.path.join("/home/billy/25-1kp/MoNaVLA", cfg["parent"])
        parent_cfg = load_config(parent_path)
        # 단순 머지 (자식이 우선)
        for k, v in cfg.items():
            if isinstance(v, dict) and k in parent_cfg:
                parent_cfg[k].update(v)
            else:
                parent_cfg[k] = v
        return parent_cfg
    return cfg

@torch.no_grad()
def evaluate():
    from robovlm_nav.datasets.nav_dataset import NavDataset
    from robovlms.utils.common import collate_with_none

    print(f"Loading config: {CONFIG_PATH}")
    config = load_config(CONFIG_PATH)
    
    # 필수 필드 보정
    if "use_hand_rgb" not in config: config["use_hand_rgb"] = False
    if "use_time_causal_mask" not in config: config["use_time_causal_mask"] = True
    
    trainer = MobileVLATrainer(config)
    print(f"Loading checkpoint: {CKPT_PATH}")
    
    state_dict = torch.load(CKPT_PATH, map_location="cpu")["state_dict"]
    new_state_dict = {}
    for k, v in state_dict.items():
        if k.startswith("model."):
            new_state_dict[k[6:]] = v
        else:
            new_state_dict[k] = v
    
    trainer.model.load_state_dict(new_state_dict, strict=True)
    trainer.model.cuda().eval()

    # 이미지 전처리기 설정
    image_preprocess = trainer.model.image_processor

    # Dataset & Loader 수동 생성
    val_cfg = config["val_dataset"]
    val_cfg["is_training"] = False
    val_cfg["train_split"] = 0.0  # 평가 시 전체 데이터 사용
    
    val_dataset = NavDataset(
        **val_cfg, 
        tokenizer=trainer.model.tokenizer,
        image_preprocess=image_preprocess
    )
    
    val_loader = torch.utils.data.DataLoader(
        val_dataset,
        batch_size=1,
        num_workers=config.get("num_workers", 4),
        shuffle=False,
        collate_fn=val_dataset.collater
    )
    
    total = 0
    correct_pm = 0
    correct_dm = 0
    
    results = []
    MAX_EVAL = 200  # 샘플 수 증가
    
    print(f"Starting Evaluation on {len(val_dataset)} total samples (Limit: {MAX_EVAL})...")
    for i, batch in enumerate(tqdm(val_loader)):
        if i >= MAX_EVAL:
            break
        # GPU 이동
        for k, v in batch.items():
            if isinstance(v, torch.Tensor):
                batch[k] = v.cuda()
        
        # BaseTrainer의 로직을 따라 배치 전처리 및 모델 호출
        processed_batch = trainer._process_batch(batch)
        (
            rgb, hand_rgb, attention_mask, language, text_mask,
            fwd_rgb_chunck, fwd_hand_rgb_chunck, arm_action, gripper_action,
            arm_action_chunck, gripper_action_chunck, chunck_mask, fwd_mask,
            instr_and_action_ids, instr_and_action_labels, instr_and_action_mask,
            raw_text, rel_state, data_source
        ) = processed_batch

        # 추론 모드(mode="val")로 호출하여 logits 획득
        logits = trainer.model.forward_action(
            vision_x=rgb,
            lang_x=language,
            attention_mask=text_mask,
            action_labels=(arm_action_chunck, gripper_action_chunck),
            action_mask=chunck_mask,
            vision_gripper=hand_rgb,
            fwd_rgb_labels=fwd_rgb_chunck,
            fwd_hand_rgb_labels=fwd_hand_rgb_chunck,
            fwd_mask=fwd_mask,
            instr_and_action_ids=instr_and_action_ids,
            instr_and_action_labels=instr_and_action_labels,
            instr_and_action_mask=instr_and_action_mask,
            raw_text=raw_text,
            data_source=data_source,
            rel_state=rel_state,
            mode="val"
        )
        
        # logits shape: (bs, 1, action_dim) -> argmax
        if isinstance(logits, (list, tuple)):
            logits = logits[0]
        pred_id = torch.argmax(logits, dim=-1).view(-1)[0].item()
        
        # GT (Ground Truth): arm_action_chunck의 첫 번째 스텝의 첫 번째 액션
        gt_id = int(arm_action_chunck[0, 0, 0].item())
        
        # PM (Perfect Match)
        is_pm = (pred_id == gt_id)
        if is_pm: correct_pm += 1
        
        # DM (Directional Match) - 6클래스 최적화에서는 현재 PM과 동일하게 평가
        is_dm = is_pm 
        if is_dm: correct_dm += 1
        
        total += 1
        
        if i % 10 == 0:
            import torch.nn.functional as F
            probs = F.softmax(logits[0, 0], dim=-1)
            topk_probs, topk_indices = torch.topk(probs, min(3, probs.size(-1)))
            tqdm.write(f"[{i}] Instr: {raw_text[0][:50]}...")
            tqdm.write(f"    Pred: {ACTION_CLASSES.get(pred_id, 'Unknown')} (GT: {ACTION_CLASSES.get(gt_id, 'Unknown')})")
            tqdm.write(f"    Top-K Indices: {topk_indices.cpu().tolist()}")
            tqdm.write(f"    Top-K Probs: {topk_probs.cpu().tolist()}")
            tqdm.write(f"    Logits: {logits[0, 0].cpu().tolist()}")

    pm_acc = (correct_pm / total) * 100
    dm_acc = (correct_dm / total) * 100
    
    print("\n" + "="*50)
    print(f"Evaluation Results (Epoch 13)")
    print(f"Total Samples: {total}")
    print(f"PM Accuracy: {pm_acc:.2f}%")
    print(f"DM Accuracy: {dm_acc:.2f}%")
    print("="*50)

if __name__ == "__main__":
    evaluate()

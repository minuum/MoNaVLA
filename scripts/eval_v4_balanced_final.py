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

# PYTHONPATH 설정 (필요 시 수정)
sys.path.append("/home/billy/25-1kp/MoNaVLA")
sys.path.append("/home/billy/25-1kp/MoNaVLA/third_party/RoboVLMs")

from robovlms.train.mobile_vla_trainer import MobileVLATrainer
import robovlms.model.backbone as backbone
from robovlms.model.backbone.robokosmos import RoboKosMos
setattr(backbone, "RoboVLM-Nav", RoboKosMos)

import robovlms.model.policy_head as policy_head
from robovlm_nav.models.policy_head.nav_policy_impl import MobileVLAClassificationDecoder, MobileVLALSTMDecoder
setattr(policy_head, "NavPolicy", MobileVLAClassificationDecoder)
setattr(policy_head, "NavPolicyRegression", MobileVLALSTMDecoder)

# 설정 (신규 학습 체크포인트)
CKPT_PATH = "/home/billy/25-1kp/MoNaVLA/runs/v4_nav/kosmos/mobile_vla_v4_balanced_v2/2026-03-25/v4-balanced-v2/epoch_epoch=epoch=04-val_loss=val_loss=3.182.ckpt"
CONFIG_PATH = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v4_balanced_v1.json"

# 6클래스 매핑
ACTION_CLASSES = {
    0: "Stop", 
    1: "Forward", 
    2: "Left", 
    3: "Right", 
    4: "Forward-Left", 
    5: "Forward-Right"
}

def load_config(path):
    with open(path, "r") as f:
        cfg = json.load(f)
    if "parent" in cfg and cfg["parent"]:
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
    
    print(f"Loading config: {CONFIG_PATH}")
    config = load_config(CONFIG_PATH)
    
    # 필수 필드 보정
    if "use_hand_rgb" not in config: config["use_hand_rgb"] = False
    if "use_time_causal_mask" not in config: config["use_time_causal_mask"] = True
    
    trainer = MobileVLATrainer(config)
    print(f"Loading checkpoint: {CKPT_PATH}")
    
    # State dict 로딩 (model. 접두어 제거 대응)
    sd_full = torch.load(CKPT_PATH, map_location="cpu")
    state_dict = sd_full.get("state_dict", sd_full)
    
    new_state_dict = {}
    for k, v in state_dict.items():
        if k.startswith("model."):
            new_state_dict[k[6:]] = v
        else:
            new_state_dict[k] = v
    
    trainer.model.load_state_dict(new_state_dict, strict=True)
    trainer.model.cuda().eval()

    # Dataset & Loader 수동 생성
    val_cfg = config["val_dataset"]
    val_cfg["is_training"] = False
    val_cfg["train_split"] = 0.0
    
    val_dataset = NavDataset(
        **val_cfg, 
        tokenizer=trainer.model.tokenizer,
        image_preprocess=trainer.model.image_processor
    )
    
    val_loader = torch.utils.data.DataLoader(
        val_dataset,
        batch_size=1,
        num_workers=4,
        shuffle=False,
        collate_fn=val_dataset.collater
    )
    
    total = 0
    correct_pm = 0
    pm_per_class = {c: [0, 0] for c in ACTION_CLASSES.keys()} # [correct, total]
    
    MAX_EVAL = 500
    print(f"Starting Evaluation (Limit: {MAX_EVAL})...")
    
    for i, batch in enumerate(tqdm(val_loader)):
        if i >= MAX_EVAL: break
        
        for k, v in batch.items():
            if isinstance(v, torch.Tensor): batch[k] = v.cuda()
        
        processed_batch = trainer._process_batch(batch)
        # MobileVLATrainer._process_batch returns (rgb, hand_rgb, attention_mask, language, text_mask, fwd_rgb_chunck, fwd_hand_rgb_chunck, velocity, gripper_action, velocity_chunck, gripper_action_chunck, chunck_mask, fwd_mask, instr_and_action_ids, instr_and_action_labels, instr_and_action_mask, raw_text, rel_state, data_source)
        # However, for discrete_action training, 'action' in batch is used.
        # Let's use the raw batch for GT to be safe and consistent with the dataset.
        
        rgb = processed_batch[0]
        language = processed_batch[3]
        text_mask = processed_batch[4]
        hand_rgb = processed_batch[1]
        fwd_rgb_chunck = processed_batch[5]
        fwd_hand_rgb_chunck = processed_batch[6]
        # In discrete mode, trainer._process_batch sets velocity = batch['action']
        velocity = processed_batch[7] 
        velocity_chunck = processed_batch[9]
        gripper_action = processed_batch[8]
        gripper_action_chunck = processed_batch[10]
        chunck_mask = processed_batch[11]
        fwd_mask = processed_batch[12]
        instr_and_action_ids = processed_batch[13]
        instr_and_action_labels = processed_batch[14]
        instr_and_action_mask = processed_batch[15]
        raw_text = processed_batch[16]
        rel_state = processed_batch[17]
        data_source = processed_batch[18]

        # Debugging: check if velocity_chunck is None
        if velocity_chunck is None:
            # If velocity_chunck is None, it means action_chunck was not in batch.
            # MobileVLAClassificationDecoder expects (B, T, n) where n=fwd_pred_next_n.
            gt_action = batch['action'] # (B, T)
            gt_id = int(gt_action[0, 0].item())
            
            # Replicate along the chunk dimension to match model's expected input
            # config['fwd_pred_next_n'] is the chunk size
            chunk_size = config.get("fwd_pred_next_n", 1)
            target_labels = gt_action.unsqueeze(-1).expand(-1, -1, chunk_size) # (B, T, chunk)
        else:
            gt_id = int(velocity_chunck[0, 0, 0].item())
            target_labels = velocity_chunck # Should already be (B, T, chunk) if present

        outputs = trainer.model.forward_action(
            vision_x=rgb,
            lang_x=language,
            attention_mask=text_mask,
            action_labels=(target_labels, gripper_action_chunck),
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
        
        if isinstance(outputs, (list, tuple)): outputs = outputs[0]
        # outputs shape: (bs, window_size, chunk, num_classes) 
        # We take the prediction for the current frame, first chunk
        pred_id = torch.argmax(outputs[0, 0, 0], dim=-1).item()
       
        pm_per_class[gt_id][1] += 1
        if pred_id == gt_id:
            correct_pm += 1
            pm_per_class[gt_id][0] += 1
        total += 1

    pm_acc = (correct_pm / total) * 100
    print("\n" + "="*50)
    print(f"Evaluation Results: PM Accuracy: {pm_acc:.2f}%")
    print("-" * 30)
    for cid, name in ACTION_CLASSES.items():
        corr, tot = pm_per_class[cid]
        acc = (corr / tot * 100) if tot > 0 else 0
        print(f"{name:15}: {acc:6.2f}% ({corr}/{tot})")
    print("="*50)

if __name__ == "__main__":
    evaluate()

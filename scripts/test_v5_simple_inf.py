import sys
import os
import torch
import h5py
import numpy as np
from PIL import Image
from pathlib import Path

# Add project roots
ROOT_DIR = Path("/home/billy/25-1kp/MoNaVLA")
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "third_party" / "RoboVLMs"))

# Force mock certain things if needed
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from main import load_config, update_configs
from robovlm_nav.trainer.nav_trainer import NavTrainer
from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset

# 1. Load config
config_path = ROOT_DIR / "configs/mobile_vla_v5_exp01_discrete.json"
configs = load_config(str(config_path))
configs["num_gpus"] = 1
configs["accelerator"] = "gpu"

# 2. Checkpoint path (Best from logs)
ckpt_path = "/home/billy/25-1kp/MoNaVLA/runs/v5_nav/kosmos/mobile_vla_v5_exp01/2026-04-10/v5-exp01-discrete/epoch_epoch=epoch=05-val_loss=val_loss=2.270.ckpt"

print(f"Loading model from {ckpt_path}...")
# Use the same trick as train.py to inject our components
import robovlms.model.policy_head
from robovlm_nav.models.policy_head.nav_policy_impl import MobileVLAClassificationDecoder
setattr(robovlms.model.policy_head, "MobileVLAClassificationDecoder", MobileVLAClassificationDecoder)

model = NavTrainer.load_from_checkpoint(ckpt_path, configs=configs)
model.to("cuda").eval()
print("Model loaded successfully.")

# 3. Load Sample Data (A Right Turn episode)
h5_path = "/home/billy/25-1kp/MoNaVLA/ROS_action/v5_data_bak/mobile_vla_dataset_v5/episode_260408_185014_target_center_right_path__core__fixed_center.h5"
with h5py.File(h5_path, "r") as f:
    images = f["observations"]["images"][:]
    # Take a frame midway where the turn should be happening
    frame_idx = int(len(images) * 0.7) # A bit later might be better for turn
    img_array = images[frame_idx]
    
print(f"Using frame {frame_idx} from {h5_path}")

# 4. Prepare Input
# Simple transform match nav_h5_dataset_impl
img = Image.fromarray(img_array.astype(np.uint8)).resize((224, 224), Image.BILINEAR)
img_tensor = torch.from_numpy(np.array(img)).float() / 255.0
img_tensor = img_tensor.permute(2, 0, 1)
mean = torch.tensor([0.48145466, 0.4578275, 0.40821073]).view(3, 1, 1)
std = torch.tensor([0.26862954, 0.26130258, 0.27577711]).view(3, 1, 1)
img_tensor = (img_tensor - mean) / std

# Window size is 6 in config, we'll repeat the same frame to simulate a window
input_rgb = img_tensor.unsqueeze(0).repeat(6, 1, 1, 1).unsqueeze(0).to("cuda") # (B=1, T=6, C, H, W)
instruction = "<grounding>An image of a robot Navigate to the gray basket"

# Tokenize
from transformers import AutoProcessor
processor = AutoProcessor.from_pretrained(configs["vlm"]["pretrained_model_name_or_path"])
tokenized = processor(text=instruction, return_tensors="pt")
input_ids = tokenized["input_ids"].to("cuda")
attention_mask = tokenized["attention_mask"].to("cuda")

# 5. Inference
with torch.no_grad():
    # NavTrainer.forward usually calls model.policy_forward
    # Let's peek at the model's internal structure or call the forward directly
    output = model.model(
        rgb=input_rgb,
        text=input_ids,
        text_mask=attention_mask,
        image_mask=torch.ones((1, 6)).to("cuda")
    )
    
# output usually contains 'action_logits' for classification
logits = output["action_logits"] # (B, T, num_classes)
# Taking the last frame's prediction in the window
last_logits = logits[0, -1, :] 
pred_class = torch.argmax(last_logits).item()

class_map = {0: "STOP", 1: "FORWARD", 2: "LEFT", 3: "RIGHT", 4: "FWD+LEFT", 5: "FWD+RIGHT"}
print(f"\n========================================")
print(f"Result for 'RIGHT' path frame:")
print(f"Predicted Class: {pred_class} ({class_map.get(pred_class, 'UNKNOWN')})")
print(f"Logits: {last_logits.cpu().numpy()}")
print(f"========================================\n")

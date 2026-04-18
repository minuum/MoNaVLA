#!/usr/bin/env python3
"""
V5 Exp10 대규모 에피소드 검증 스크립트 (20개 에피소드 전수 조사)
에피소드별 프레임 시퀀스 추론 및 통합 HTML 대시보드 생성
"""
import os
import sys
import torch
import numpy as np
import cv2
import base64
import random
import glob
from tqdm import tqdm
from PIL import Image
import h5py

os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["USE_FLASH_ATTENTION"] = "0"
sys.path.insert(1, "/home/billy/25-1kp/MoNaVLA")
sys.path.insert(0, "/home/billy/25-1kp/MoNaVLA/third_party/RoboVLMs")

from robovlms.model.backbone.base_backbone import load_config
from robovlms.train.mobile_vla_trainer import MobileVLATrainer
from transformers import AutoProcessor

# Config & Paths
CONFIG_PATH = "configs/mobile_vla_v5_exp10_bbox.json"
CKPT_PATH = "/home/billy/25-1kp/MoNaVLA/runs/v5_nav/kosmos/mobile_vla_v5_bbox/2026-04-15/v5-exp10-track2-bbox/last.ckpt"
DATASET_DIR = "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v5"
REPORT_DIR = "docs/v5/exp10/batch_analysis"
os.makedirs(REPORT_DIR, exist_ok=True)

def parse_bbox_from_text(text):
    import re
    match = re.search(r"<box_2d>\s*<patch_index_(\d+)>\s*<patch_index_(\d+)>\s*</box_2d>", text)
    if match: return int(match.group(1)), int(match.group(2))
    return None, None

def calculate_action(p1, p2):
    if p1 is None: return 0.0, 0.0
    cx = (p1 % 32 + p2 % 32) / 2.0
    err_x = cx - 15.5
    return 0.5, -0.12 * err_x

def run_batch_test():
    configs = load_config(CONFIG_PATH)
    trainer = MobileVLATrainer(configs)
    
    # Load Model
    if os.path.exists(CKPT_PATH):
        checkpoint = torch.load(CKPT_PATH, map_location="cpu")
        state_dict = checkpoint.get("state_dict", checkpoint)
        if any(k.startswith("model.") for k in state_dict.keys()):
            state_dict = {k[6:] if k.startswith("model.") else k: v for k, v in state_dict.items()}
        trainer.model.load_state_dict(state_dict, strict=False)
    
    model = trainer.model.to('cuda:0').eval()
    processor = AutoProcessor.from_pretrained("microsoft/kosmos-2-patch14-224")

    # Find Episodes
    all_episodes = glob.glob(os.path.join(DATASET_DIR, "*.h5"))
    selected_episodes = random.sample(all_episodes, min(20, len(all_episodes)))
    
    episode_results = []

    for ep_idx, ep_path in enumerate(selected_episodes):
        ep_name = os.path.basename(ep_path)
        print(f"[{ep_idx+1}/20] Analyzing {ep_name}...")
        
        frames_results = []
        with h5py.File(ep_path, 'r') as f:
            images = f['observations/images']
            actions = f['actions']
            instructions = f['language_instruction'][0].decode('utf-8') if isinstance(f['language_instruction'][0], bytes) else f['language_instruction'][0]
            
            # Step size to avoid massive HTML: Analyze ~10 key frames per episode
            step = max(1, len(images) // 10)
            for i in range(0, len(images), step):
                img_raw = images[i]
                image = Image.fromarray(img_raw)
                
                prompt = f"Instruction: {instructions} Action: "
                inputs = processor(text=prompt, images=image, return_tensors="pt").to('cuda:0')
                
                with torch.no_grad():
                    outputs = model.model.generate(
                        pixel_values=inputs['pixel_values'],
                        input_ids=inputs['input_ids'],
                        attention_mask=inputs['attention_mask'],
                        image_embeds_position_mask=inputs.get('image_embeds_position_mask'),
                        max_new_tokens=32
                    )
                
                pred_text = processor.tokenizer.decode(outputs[0], skip_special_tokens=False)
                p1, p2 = parse_bbox_from_text(pred_text)
                pred_v, pred_w = calculate_action(p1, p2)
                expert_v, expert_w = actions[i][0], actions[i][1]
                
                _, buffer = cv2.imencode('.jpg', cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR))
                b64 = base64.b64encode(buffer).decode('utf-8')
                
                frames_results.append({
                    'frame': i,
                    'b64': b64,
                    'expert': (expert_v, expert_w),
                    'pred': (pred_v, pred_w),
                    'text': pred_text.split('Action:')[-1].strip()
                })
        
        episode_results.append({
            'name': ep_name,
            'instruction': instructions,
            'frames': frames_results
        })

    # Generate Batch HTML Report
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>V5 Exp10 Batch Evaluation (20 Episodes)</title>
        <style>
            body { font-family: 'Inter', sans-serif; background: #0f172a; color: white; padding: 40px; }
            .episode-block { margin-bottom: 60px; border-bottom: 2px solid #334155; padding-bottom: 30px; }
            .frame-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; margin-top: 20px; }
            .card { background: #1e293b; border-radius: 10px; overflow: hidden; font-size: 0.75rem; border: 1px solid #334155; }
            .card img { width: 100%; aspect-ratio: 1/1; object-fit: cover; }
            .info { padding: 8px; }
            .expert { color: #94a3b8; }
            .pred { color: #38bdf8; font-weight: bold; }
            h2 { color: #fbbf24; margin-bottom: 5px; }
            .instr { color: #94a3b8; font-style: italic; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <h1>🚀 V5 Exp10 Batch Analysis Report</h1>
        <p>무작위 선택된 20개 에피소드에 대한 시각적 액션 매핑 결과입니다.</p>
    """
    
    for ep in episode_results:
        html_content += f"""
        <div class="episode-block">
            <h2>Episode: {ep['name']}</h2>
            <div class="instr">Instruction: {ep['instruction']}</div>
            <div class="frame-grid">
        """
        for f in ep['frames']:
            html_content += f"""
            <div class="card">
                <img src="data:image/jpeg;base64,{f['b64']}">
                <div class="info">
                    <strong>Frame {f['frame']}</strong><br>
                    <span class="expert">Exp: {f['expert'][0]:.2f}, {f['expert'][1]:.2f}</span><br>
                    <span class="pred">VLA: {f['pred'][0]:.2f}, {f['pred'][1]:.2f}</span>
                </div>
            </div>
            """
        html_content += "</div></div>"
        
    html_content += "</body></html>"
    
    with open(os.path.join(REPORT_DIR, "index.html"), "w") as f:
        f.write(html_content)
    print(f"Batch report generated: {os.path.join(REPORT_DIR, 'index.html')}")

if __name__ == "__main__":
    run_batch_test()

#!/usr/bin/env python3
"""
V5 Exp10 단일 에피소드 정밀 분석 스크립트 (PMDM 스타일)
프레임별 전문가 vs VLA 액션 예측값 시계열 매핑 및 HTML 리포트 생성 용도
"""
import os
import sys
import torch
import numpy as np
import cv2
import base64
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
EPISODE_PATH = "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v5/episode_260408_155049_target_center_straight_path__core__fixed_center.h5"
REPORT_DIR = "docs/v5/exp10/episode_analysis"
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
    return 0.5, -0.12 * err_x # Simple P-control for viz

def run_episode_test():
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

    results = []
    with h5py.File(EPISODE_PATH, 'r') as f:
        images = f['observations/images']
        actions = f['actions']
        instructions = f['language_instruction'][0].decode('utf-8') if isinstance(f['language_instruction'][0], bytes) else f['language_instruction'][0]
        
        # Test every 5th frame for speed/coverage
        for i in tqdm(range(0, len(images), 5)):
            img_raw = images[i]
            image = Image.fromarray(img_raw)
            
            # Action Prediction
            prompt = f"Instruction: {instructions} Action: "
            inputs = processor(text=prompt, images=image, return_tensors="pt").to('cuda:0')
            
            with torch.no_grad():
                outputs = model.model.generate(
                    pixel_values=inputs['pixel_values'],
                    input_ids=inputs['input_ids'],
                    attention_mask=inputs['attention_mask'],
                    image_embeds_position_mask=inputs.get('image_embeds_position_mask'),
                    max_new_tokens=32,
                    use_cache=True
                )
            
            pred_text = processor.tokenizer.decode(outputs[0], skip_special_tokens=False)
            p1, p2 = parse_bbox_from_text(pred_text)
            pred_v, pred_w = calculate_action(p1, p2)
            
            # Expert Data
            expert_v, expert_w = actions[i][0], actions[i][1]
            
            # Save for HTML
            _, buffer = cv2.imencode('.jpg', cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR))
            b64 = base64.b64encode(buffer).decode('utf-8')
            
            results.append({
                'frame': i,
                'b64': b64,
                'expert': (expert_v, expert_w),
                'pred': (pred_v, pred_w),
                'text': pred_text.split('Action:')[-1].strip()
            })

    # Generate HTML Report (PMDM Style)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>V5 Exp10 Episode Analysis</title>
        <style>
            body {{ font-family: sans-serif; background: #0f172a; color: white; padding: 20px; }}
            .frame-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }}
            .card {{ background: #1e293b; border-radius: 8px; overflow: hidden; border: 1px solid #334155; }}
            .card img {{ width: 100%; }}
            .info {{ padding: 10px; font-size: 0.8rem; }}
            .match-high {{ color: #4ade80; }}
            .match-low {{ color: #f87171; }}
        </style>
    </head>
    <body>
        <h1>Episode Analysis: {EPISODE_PATH.split('/')[-1]}</h1>
        <p>Instruction: {instructions}</p>
        <div class="frame-grid">
    """
    
    for res in results:
        diff = abs(res['expert'][1] - res['pred'][1])
        match_class = "match-high" if diff < 0.1 else "match-low"
        html_content += f"""
        <div class="card">
            <img src="data:image/jpeg;base64,{res['b64']}">
            <div class="info">
                <strong>Frame {res['frame']}</strong><br>
                Exp: v={res['expert'][0]:.2f} w={res['expert'][1]:.2f}<br>
                <span class="{match_class}">Pred: v={res['pred'][0]:.2f} w={res['pred'][1]:.2f}</span><br>
                Text: {res['text']}
            </div>
        </div>
        """
        
    html_content += "</div></body></html>"
    
    with open(os.path.join(REPORT_DIR, "index.html"), "w") as f:
        f.write(html_content)
    print(f"Report generated: {os.path.join(REPORT_DIR, 'index.html')}")

if __name__ == "__main__":
    run_episode_test()

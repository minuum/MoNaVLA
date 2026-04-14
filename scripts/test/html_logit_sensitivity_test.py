#!/usr/bin/env python3
"""
단일 정지 이미지 대상 텍스트-로짓 반응성(Sensitivity) 검증용 HTML 툴
지정된 프레임 이미지에 대해 각기 다른 방향 지시 프롬프트를 주입하고,
모델이 출력하는 로짓(Logit)과 확률 분포(Probability)를 가시적으로 비교합니다.
"""

import argparse
import base64
import io
import json
import os
import sys
from pathlib import Path

import h5py
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Assume third_party/RoboVLMs_upstream or similar is in path, or use local
sys.path.insert(0, str(PROJECT_ROOT / "third_party" / "RoboVLMs"))
from robovlms.train.mobile_vla_trainer import MobileVLATrainer

def pil_to_b64(pil_img):
    buffered = io.BytesIO()
    pil_img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to checkpoint .ckpt")
    parser.add_argument("--config", type=str, required=True, help="Path to config .json")
    parser.add_argument("--h5_file", type=str, required=True, help="Path to test h5 episode")
    parser.add_argument("--frame_idx", type=int, default=10, help="Frame index to test")
    parser.add_argument("--output_html", type=str, default="logit_sensitivity_report.html", help="Output HTML file path")
    args = parser.parse_args()

    print(f"Loading config from {args.config}")
    with open(args.config, 'r') as f:
        config = json.load(f)

    # 6-class mapping based on nav_h5_dataset_impl mapping 
    # 0:Stop, 1:F, 2:B(Stop), 3:L, 4:R, 5:FL, 6:FR
    # -> 0:Stop, 1:F, 2:L, 3:R, 4:FL, 5:FR
    cls_names = ["Stop", "Forward", "Left", "Right", "Diag-Left", "Diag-Right"]
    num_classes = config.get("act_head", {}).get("num_classes", 6)

    print(f"Loading MobileVLATrainer from {args.checkpoint}...")
    trainer = MobileVLATrainer.load_from_checkpoint(
        args.checkpoint,
        config_path=args.config,
        map_location="cuda" if torch.cuda.is_available() else "cpu"
    )
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    trainer.model.to(device)
    trainer.model.eval()

    print(f"Loading image from {args.h5_file} (frame {args.frame_idx})")
    with h5py.File(args.h5_file, 'r') as hf:
        images_src = hf['observations']['images'] if 'observations' in hf else hf['images']
        img_np = images_src[args.frame_idx]
        pil_img = Image.fromarray(img_np.astype(np.uint8))
        if 'actions' in hf:
            action = hf['actions'][args.frame_idx]
            print(f"Ground Truth Action at this frame: {action}")

    from transformers import AutoProcessor
    processor = AutoProcessor.from_pretrained('.vlms/kosmos-2-patch14-224')

    prompts = [
        "Navigate straight forward to the gray basket",
        "Navigate to the left toward the gray basket",
        "Navigate to the right toward the gray basket",
        "Stop in front of the gray basket"
    ]

    results = []

    print("Running inference...")
    for p_idx, prompt_text in enumerate(prompts):
        instruction = f"<grounding>An image of a robot {prompt_text}"
        inputs = processor(images=pil_img, text=instruction, return_tensors="pt")
        
        for k in inputs:
            if isinstance(inputs[k], torch.Tensor):
                inputs[k] = inputs[k].to(device)

        if inputs['pixel_values'].dim() == 4:
            inputs['pixel_values'] = inputs['pixel_values'].unsqueeze(1) # Add temporal dim (seq_len=1)
        
        with torch.no_grad():
            pred_output = trainer.model.inference(
                inputs['pixel_values'],
                inputs['input_ids'],
                inputs['attention_mask'],
                None, None, None, None, None
            )

        logits = pred_output['action']
        if isinstance(logits, tuple):
            logits = logits[0]
        
        # Expecting logits shape for classification to be (B=1, seq_len=1, next_n=1, num_classes=6)
        if logits.dim() == 4:
            logits = logits[0, 0, 0] # first batch, first timestep, first next_n
        elif logits.dim() == 3:
            logits = logits[0, 0]
        elif logits.dim() == 2:
            logits = logits[0]

        logits_np = logits.cpu().numpy()
        
        if len(logits_np) == num_classes:
            probs = F.softmax(logits, dim=0).cpu().numpy()
            results.append({
                "prompt": prompt_text,
                "logits": logits_np.tolist(),
                "probs": probs.tolist()
            })
        else:
            # Maybe continuous Model
            results.append({
                "prompt": prompt_text,
                "logits": logits_np.tolist(), # Treated as continuous output then
                "probs": []
            })
            cls_names = [f"Dim_{i}" for i in range(len(logits_np))]
    
    # Generate HTML
    b64_img = pil_to_b64(pil_img)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>VLM Logit Sensitivity Report</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem; }}
            .container {{ max-width: 1200px; margin: 0 auto; display: flex; gap: 2rem; }}
            .image-pane {{ flex: 1; }}
            .image-pane img {{ width: 100%; border-radius: 8px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }}
            .results-pane {{ flex: 2; display: flex; flex-direction: column; gap: 1rem; }}
            .card {{ background: #1e293b; padding: 1.5rem; border-radius: 8px; border: 1px solid #334155; }}
            h1 {{ margin-top: 0; color: #38bdf8; }}
            h3 {{ margin-top: 0; color: #bae6fd; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
            th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #334155; }}
            th {{ font-weight: 600; color: #94a3b8; }}
            .bar-bg {{ background: #334155; height: 8px; border-radius: 4px; width: 100%; overflow: hidden; margin-top: 4px; }}
            .bar-fill {{ background: #38bdf8; height: 100%; }}
        </style>
    </head>
    <body>
        <div style="max-width: 1200px; margin: 0 auto; margin-bottom: 2rem;">
            <h1>Logit Sensitivity Report (Track 1)</h1>
            <p><strong>Config:</strong> {args.config}</p>
            <p><strong>File:</strong> {args.h5_file} (Frame: {args.frame_idx})</p>
        </div>
        <div class="container">
            <div class="image-pane">
                <img src="data:image/jpeg;base64,{b64_img}" alt="Observation">
            </div>
            <div class="results-pane">
    """

    for res in results:
        html_content += f"""
                <div class="card">
                    <h3>Prompt: <code>"{res['prompt']}"</code></h3>
                    <table>
                        <tr>
                            <th>Action Class</th>
                            <th>Logit</th>
                            <th>Probability</th>
                            <th style="width: 40%;">Visual</th>
                        </tr>
        """
        for i, val in enumerate(res['probs'] if res['probs'] else res['logits']):
            label = cls_names[i]
            logit_v = res['logits'][i]
            prob_v = val if res['probs'] else 0.0
            
            bar_width = (prob_v * 100) if res['probs'] else (max(0, logit_v + 5) * 10)
            bar_width = min(100, max(0, bar_width))
            
            html_content += f"""
                        <tr>
                            <td>{label}</td>
                            <td>{logit_v:.4f}</td>
                            <td>{prob_v*100:.2f}%</td>
                            <td>
                                <div class="bar-bg"><div class="bar-fill" style="width: {bar_width}%;"></div></div>
                            </td>
                        </tr>
            """
        html_content += """
                    </table>
                </div>
        """

    html_content += """
            </div>
        </div>
    </body>
    </html>
    """

    with open(args.output_html, "w") as f:
        f.write(html_content)

    print(f"HTML Report generated at: {args.output_html}")
    print("Open it in a browser to see the prompt sensitivity.")

if __name__ == "__main__":
    main()

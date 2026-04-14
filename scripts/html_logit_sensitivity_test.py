#!/usr/bin/env python3
"""
단일 정지 이미지 대상 텍스트-로짓 반응성(Sensitivity) 검증용 HTML 툴
동일한 이미지에 대해 프롬프트만 변경했을 때 모델의 예측 로그 분포가 어떻게 바뀌는지 테스트합니다.
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

import torch
import numpy as np
import base64
from io import BytesIO
from PIL import Image

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

# CKPT & CONFIG
CKPT_PATH = "/home/billy/25-1kp/MoNaVLA/runs/v5_nav/kosmos/mobile_vla_v5_exp08/2026-04-13/v5-exp08-instruction-follow/epoch_epoch=05-val_loss=3.748.ckpt"
CONFIG_PATH = "/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp08_instruction_follow.json"
# if file above does not exist, use another one. I'll just adjust the path in code to existing one from eval scripts.
CKPT_PATH = "/home/billy/25-1kp/MoNaVLA/runs/v5_nav/kosmos/mobile_vla_v5_exp08/2026-04-13/v5-exp08-instruction-follow/epoch_epoch=epoch=05-val_loss=val_loss=3.748.ckpt"

from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset

def generate_html_report(image_path, results):
    # Base64 encode the image
    img = Image.open(image_path)
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    html = f"""
    <html>
    <head>
        <title>Text-Logit Sensitivity Report</title>
        <style>
            body {{ font-family: sans-serif; margin: 40px; background-color: #f5f5f5; }}
            h1 {{ color: #333; }}
            .container {{ display: flex; gap: 20px; }}
            .image-box {{ flex: 1; text-align: center; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .results-box {{ flex: 2; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
            th {{ background-color: #f8f9fa; }}
            .highlight {{ font-weight: bold; color: #d9534f; }}
            img {{ max-width: 100%; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <h1>Text-Logit Sensitivity Report</h1>
        <div class="container">
            <div class="image-box">
                <h2>Test Image</h2>
                <img src="data:image/jpeg;base64,{img_str}" />
            </div>
            <div class="results-box">
                <h2>Logit Distribution by Prompt</h2>
                <table>
                    <tr>
                        <th>Prompt</th>
                        <th>Predicted Action</th>
                        <th>Stop</th>
                        <th>Forward</th>
                        <th>Left</th>
                        <th>Right</th>
                        <th>FWD-L</th>
                        <th>FWD-R</th>
                    </tr>
    """
    
    action_map = {0: "Stop", 1: "Forward", 2: "Left", 3: "Right", 4: "FWD-L", 5: "FWD-R"}
    for prompt, (pred_idx, logits) in results.items():
        softmax_probs = np.exp(logits) / np.sum(np.exp(logits))
        html += f"<tr><td>{prompt}</td><td class='highlight'>{action_map[pred_idx]}</td>"
        for p in softmax_probs:
            html += f"<td>{p:.4f}</td>"
        html += "</tr>"

    html += """
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    with open("logit_sensitivity_report.html", "w") as f:
        f.write(html)
    print("Report generated: logit_sensitivity_report.html")

def main():
    print("Initializing model...")
    from robovlms.model.backbone.base_backbone import load_config
    configs = load_config(CONFIG_PATH)
    configs["model_path"] = "microsoft/kosmos-2-patch14-224"
    if "tokenizer" not in configs: configs["tokenizer"] = {}
    configs["tokenizer"]["pretrained_model_name_or_path"] = "microsoft/kosmos-2-patch14-224"
    if "vlm" not in configs: configs["vlm"] = {}
    configs["vlm"]["pretrained_model_name_or_path"] = "microsoft/kosmos-2-patch14-224"

    trainer = MobileVLATrainer(configs)
    
    checkpoint = torch.load(CKPT_PATH, map_location="cpu")
    state_dict = checkpoint.get("state_dict", checkpoint)
    if any(k.startswith("model.") for k in state_dict.keys()):
        state_dict = {k[6:] if k.startswith("model.") else k: v for k, v in state_dict.items()}
        
    trainer.model.load_state_dict(state_dict, strict=True)
    model = trainer.model.to('cuda:0')
    model.eval()

    print("Loading test image from dataset...")
    DATASET_PATH = "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v3"
    ds = MobileVLAH5Dataset(
        data_dir=DATASET_PATH,
        episode_pattern="episode_*.h5",
        model_name="kosmos",
        window_size=1, # single image mode
        discrete_action=True,
        is_validation=True,
        num_classes=6,
        instruction_preset="action_aware_train"
    )
    
    # Take the first image
    sample = ds[0]
    # Save the original image temporarily for the HTML
    from torchvision.transforms.functional import to_pil_image
    # Denormalize assuming standard ImageNet or simple [-1, 1]
    # Actually just get it from source if possible
    # We will just write out the tensor as image
    img_tensor = sample['rgb'][-1] # (C, H, W)
    if img_tensor.min() < 0:
        img_tensor = (img_tensor * 0.5) + 0.5
    img_pil = to_pil_image(img_tensor)
    img_pil.save("test_image_temp.jpg")

    prompts = [
        "Go forward to the basket.",
        "Go left.",
        "Go right.",
        "Stop here."
    ]
    
    results = {}
    from transformers import AutoProcessor
    processor = AutoProcessor.from_pretrained("microsoft/kosmos-2-patch14-224")

    print("Running inference...")
    with torch.no_grad():
        for prompt in prompts:
            # Process text input
            inputs = processor(text=prompt, return_tensors="pt")
            input_ids = inputs['input_ids'].cuda()
            attention_mask = inputs['attention_mask'].cuda()
            
            rgb = sample['rgb'].unsqueeze(0).cuda()
            
            outputs = model.inference(
                rgb, input_ids, attention_mask,
                None, None, None, None, None
            )

            # Extract logits using the correct parser
            logits_res = outputs['action']
            if isinstance(logits_res, tuple):
                logits_res = logits_res[0]
            
            # (1, 1, 1, 6) -> extract the last chunk step
            logits_np = logits_res.cpu().numpy()
            ndim = logits_np.ndim
            if ndim == 4:
                class_logits = logits_np[0, -1, 0, :]
            else:
                class_logits = logits_np[0, -1, :]

            pred_idx = int(np.argmax(class_logits))
            results[prompt] = (pred_idx, class_logits)

    generate_html_report("test_image_temp.jpg", results)

if __name__ == "__main__":
    main()

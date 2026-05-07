#!/usr/bin/env python3
import os
import sys
import torch
import numpy as np
import gradio as gr
from PIL import Image, ImageDraw
from pathlib import Path

# 프로젝트 루트 추가
ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from robovlms.train.mobile_vla_trainer import MobileVLATrainer
from robovlms.utils.config_utils import load_config

# --- 모델 로드 함수 ---
def load_vla_model():
    config_path = "configs/mobile_vla_v5_exp39_exp25_last4_lora.json"
    checkpoint_path = "/home/minum/26CS/MoNaVLA/runs/v5_nav/kosmos/mobile_vla_v5_exp39/2026-05-01/v5-exp39-exp25-last4-lora/epoch_epoch=epoch=14-val_loss=val_loss=8.229.ckpt"
    
    if not os.path.exists(config_path) or not os.path.exists(checkpoint_path):
        print("❌ Error: 모델 파일이나 설정을 찾을 수 없습니다.")
        return None

    configs = load_config(config_path)
    model = MobileVLATrainer(configs)
    
    # 가중치 로드
    ckpt = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
    state_dict = ckpt.get('state_dict', ckpt.get('model_state_dict', ckpt))
    model.load_state_dict(state_dict, strict=False)
    model.to("cuda").eval()
    print("✅ Exp39 Model Loaded Successfully")
    return model

# 전역 모델 객체
model = load_vla_model()

# --- 시각화 함수 ---
def draw_action_and_bbox(image, action, bbox=None):
    draw = ImageDraw.Draw(image)
    w, h = image.size
    cx, cy = w // 2, h - 50
    
    # 액션 시각화 (v: 선속도, w: 각속도)
    # v는 위쪽 화살표, w는 좌우 휘어짐으로 표현 (간소화)
    v, w = action[0], action[1]
    
    # 선속도 화살표
    draw.line([cx, cy, cx, cy - int(v * 200)], fill='cyan', width=10)
    # 각속도 화살표
    draw.line([cx, cy, cx + int(w * 200), cy], fill='yellow', width=10)
    
    # B-box가 있다면 그리기
    if bbox is not None:
        left, top, right, bottom = bbox[0]*w, bbox[1]*h, bbox[2]*w, bbox[3]*h
        draw.rectangle([left, top, right, bottom], outline='lime', width=5)
        draw.text((left, top-20), "Detected Target", fill='lime')
        
    return image

# --- Gradio 인터페이스 함수 ---
def predict(image, text):
    if model is None: return None, "Model not loaded"
    
    # 1. 전처리
    # PIL 이미지를 텐서로 (생략: Trainer 내부 로직 활용)
    processor = getattr(model.model, "processor", getattr(model.model, "image_processor", None))
    pixel_values = processor(images=image, return_tensors="pt")["pixel_values"].to("cuda")
    tokenizer = getattr(model.model, "tokenizer", getattr(model.model, "processor", None))
    t_input = tokenizer(text=text, return_tensors="pt", padding=True)

    # 2. 추론
    with torch.no_grad():
        out = model.inference_step({
            'rgb': pixel_values,
            'text': t_input["input_ids"].cuda(),
            'text_mask': t_input["attention_mask"].cuda()
        })
        while isinstance(out, tuple): out = out[0]
        act = out['action']
        while isinstance(act, tuple): act = act[0]
        action_vec = act.cpu().numpy().flatten()
    
    # 3. 시각화
    # 가상의 B-box (현재 VLA 모델은 액션 위주이므로 임시로 중앙 배치 또는 이전 실험 GT 활용 가능)
    res_img = draw_action_and_bbox(image.copy(), action_vec)
    
    status_text = f"Predicted Action (v, w): {np.round(action_vec[:2], 4)}\n"
    status_text += f"Instruction Received: \"{text}\""
    
    return res_img, status_text

# --- Launch Gradio ---
demo = gr.Interface(
    fn=predict,
    inputs=[gr.Image(type="pil", label="Robot View Image"), gr.Textbox(label="Instruction (e.g. 'Navigate around left')")],
    outputs=[gr.Image(label="Visualization"), gr.Textbox(label="Analysis")],
    title="MoNaVLA Exp39 Interactive Grounding Demo",
    description="이미지와 명령어를 입력하면 모델의 반응(Action)과 Grounding 상태를 시각화합니다."
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)

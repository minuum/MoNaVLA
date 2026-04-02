import torch
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os

# 1. 87% 사례 분석용 시각화 도구
def analyze_matching_details(episode_id, frames_data):
    \"\"\"
    가장 매칭률이 좋았던(87%) 특정 주행 에피소드를 시각화하여
    어떤 시점(Frame)에서 '대각선 이동'을 정확히 맞췄는지 보여줍니다.
    \"\"\"
    labels = ['STOP', 'FWD', 'BACK', 'LEFT', 'RIGHT', 'FL', 'FR']
    
    for i, frame in enumerate(frames_data):
        # frame: {image: ..., gt: ..., pred: ..., logits: ..., instr: ...}
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # RGB 이미지 로딩
        ax1.imshow(frame['image'])
        ax1.set_title(f"Episode {episode_id} - Frame {i}\n{frame['instr']}")
        ax1.axis('off')
        
        # 모델 예측 확률 분포 (87%의 실체)
        logits = torch.tensor(frame['logits'])
        probs = torch.softmax(logits, dim=-1).tolist()
        
        bar_colors = ['blue' if j == frame['gt'] else 'red' for j in range(len(labels))]
        ax2.bar(labels[:len(probs)], probs, color=bar_colors)
        ax2.set_ylim(0, 1.1)
        ax2.set_title(f"Confidence (Correct: {labels[frame['gt']]})")
        
        plt.savefig(f"/home/billy/25-1kp/MoNaVLA/artifacts/vla_matching_analysis/ep_{episode_id}_f_{i}.png")
        plt.close()

if __name__ == '__main__':
    os.makedirs("/home/billy/25-1kp/MoNaVLA/artifacts/vla_matching_analysis", exist_ok=True)
    print("VLA Matching Analysis Visualizer Ready!")

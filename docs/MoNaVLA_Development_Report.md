# MoNaVLA Development Analysis Report

**Date**: 2026-03-30  
**Project**: MoNaVLA (Mobile Navigation Vision-Language-Action)  
**Target**: Low-cost Mobile Robot Navigation using VLA Models  

---

## 1. Background
본 프로젝트는 **MoNaVLA** 모델을 활용하여 실내 환경에서의 로봇 내비게이션 성능을 최적화하는 것을 목표로 합니다. 기존의 VLA 모델들은 7D(Arm+Gripper) 액션에 특화되어 있으나, 내비게이션 작업에서는 2D 속도(linear_x, linear_y)의 정밀한 제어와 시공간적 일관성(Temporal Consistency)이 더욱 중요합니다.

---

## 2. Architecture Analysis
MoNaVLA는 **Llama-3-8B**를 언어 모델 백본으로, **SigLIP-L-14**를 비전 타워로 사용합니다. 효율적인 학습을 위해 **LoRA (Rank=32)**를 적용하며, 내비게이션 전용 정책 헤드(Nav Policy Head)를 설계하여 단계별로 고도화하였습니다.

### Key Components:
- **Vision Tower**: `google/siglip-so400m-patch14-384` (High-resolution feature extraction)
- **LLM Backbone**: `Llama-3-8B-Base` (Reasoning & instruction following)
- **Policy Head**: 
  - `MobileVLALSTMDecoder`: LSTM 기반의 연속값 회귀 (Regression)
  - `MobileVLAClassificationDecoder`: 액션 공간 이산화 (Classification/Binning)

---

## 3. Experimental Stages & Findings

| Stage | Name | Key Architecture / Feature | Loss Function | Goal |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1** | **Base Backbone** | 2D Regression Head (MLP) | Huber Loss | 기초적인 액션-비전 정렬 및 멀티태스크 성능 확보 |
| **Stage 2** | **Directional Awareness** | Weighted Action Loss (C) | Weighted Huber | 회전 및 측면 이동(Non-forward)에 대한 가중치 학습 강화 |
| **Stage 3** | **Robustness Enhancement** | **Action Discretization (256 bins)** | CrossEntropy | 아웃라이어에 강인하고 확률 밀도 추정이 가능한 정책 구현 |
| **Stage 4** | **Temporal Consistency** | **LSTM + Multi-step Prediction** | Sequence Huber | 0.4초 이상의 미래 경로(4-steps) 예측을 통한 부드러운 주행 |

### Stage-wise Detailed Configuration

#### Stage 2: Directional Awareness (`configs/mobile_vla_v2_stage2_nav.json`)
- **Main Rationale**: 로봇이 전진(Forward)만 하는 데이터가 압도적으로 많아 회전/후진 학습이 부족한 문제를 해결.
- **Implementation**: `action_weight_non_forward=2.5` 설정을 통해 회전 액션의 Gradient 가중치를 강화.

#### Stage 3: Robustness & Discrete Policy (`configs/mobile_vla_v3_stage3_robust.json`)
- **Main Rationale**: 회귀(Regression) 방식의 평균값 예측 한계를 극복하고, 멀티모달 액션 분포를 학습.
- **Implementation**: 256개의 bin으로 속도 범위를 나누어 분류 문제로 치환 (`n_bin=256`).

#### Stage 4: Temporal Consistency (`configs/mobile_vla_v4_stage4_temporal.json`)
- **Main Rationale**: 단일 시점(Single-step) 예측은 제어 주기에 따른 지연과 미세한 진동을 발생시킴.
- **Implementation**: 
  - `fwd_pred_next_n=4`: 현재 시점에서 미래 4프레임의 액션을 동시 예측.
  - `LSTM Hidden State`: 시각적 히스토리를 유지하여 급격한 액션 변화 방지.

---

## 4. Implementation Evidence (Code Snippets)

### [A] Directional Weighting Logic in `MobileVLALSTMDecoder`
```python
# nav_policy_impl.py
is_forward = (velocity_labels[..., 0] > 0.5) & (torch.abs(velocity_labels[..., 1]) < 0.2)
weights = torch.ones_like(loss_velocity)
weights[~is_forward] = self._action_weight_non_forward # Non-forward 가중치 적용
loss_velocity = (loss_velocity * weights).mean()
```

### [B] Multi-step Prediction Support in `get_labels`
```python
# 다중 스텝 레이블 자동 생성 로직
chunked = []
for t in range(L):
    chunk_t = arm_labels[:, t : t + n] # t 시점부터 n개의 미래 액션 추출
    chunked.append(chunk_t)
new_arm_labels = torch.stack(chunked, dim=1) # (B, L, n, 2)
```

---

## 5. Conclusion & Next Steps
1. **Convergence Check**: Stage 3(Discrete)와 Stage 4(Temporal Regression)의 Evaluation 결과를 비교하여, 최종 모델의 헤드 타입을 결정할 필요가 있음.
2. **Hyperparameter Tuning**: `action_weight_non_forward` 값(현재 2.5)에 따른 회전 성능 변화를 정량적으로 분석(Success Rate vs. Rotation Accuracy).
3. **Deployment**: 학습된 체크포인트를 ROS2 Client와 연동하여 실시간 추론 성능(Latency < 50ms) 검증 예정.

---
> **References**:
> - [1] RoboVLMs Implementation: `third_party/RoboVLMs`
> - [2] Navigation Head Architecture: `robovlm_nav/models/policy_head/nav_policy_impl.py`

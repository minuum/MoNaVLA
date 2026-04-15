# Mobile VLA 데이터 증강 전략 및 계획 (2025-12-09)

## 🎯 목표
제한된 데이터셋(500 에피소드)의 한계를 극복하고 모델의 일반화 성능 향상

---

## 🔬 최신 연구 트렌드 (2023-2025)

### 1. Generative Data Augmentation (가장 핫함)
- **ROSIE [Google, 2023]**: Text-to-Image Diffusion 모델을 사용하여 로봇 학습 데이터를 증강.
  - "Inpainting"을 통해 책상을 대리석으로 바꾸거나, 새로운 방해물(distractor) 추가.
  - Sim-to-Real gap을 줄이는 데 탁월한 효과.
- **Stable Diffusion 활용**: 동일한 장면의 조명, 배경, 텍스처를 다양하게 변형하여 "Visual Robustness" 확보.

### 2. Instruction Augmentation
- LLM(GPT-4 등)을 사용하여 하나의 로봇 동작에 대해 수십 가지의 다양한 언어 명령 생성.
- 예: "Go left" → "Navigate to the left", "Approach the object on the left side", "Left turn towards target".
- VLA 모델의 언어 이해 능력 과적합 방지.

### 3. Physics-based / Trajectory Augmentation
- 기존 궤적에 노이즈를 추가하거나, 시간 스케일을 조절(Time warping)하여 다양한 속도 패턴 학습.

---

## ✅ 적용된 증강 전략 (Implemented)

### 1. Mirroring Augmentation (Priority 1)
데이터셋 클래스(`mobile_vla_h5_dataset.py`)에 즉시 구현 및 적용 완료.

- **방법**: 
  - 50% 확률로 **이미지 좌우 반전** (`torch.flip`)
  - **Action 반전**: `linear_y` (회전/횡이동) 부호 반전
  - **언어 치환**: 텍스트 내 "left" ↔ "right" 단어 교체
- **효과**:
  - 데이터 규모 2배 증가 (500 → 1000 에피소드 효과)
  - Left/Right 데이터 불균형 완벽 해소
  - 모델이 시각적 대칭성을 학습하여 강건성 향상

---

## 📋 향후 적용 계획 (To-Do)

### Phase 1: Instruction Augmentation (LLM)
- GPT-4 API를 활용하여 기존 500개 에피소드의 언어 주석을 다양화.
- 현재의 단순한 "Navigate to..." 패턴을 벗어나 자연어 명령 학습.

### Phase 2: Generative Inpainting (GenAI)
- 배경 다양화를 위해 Stable Diffusion Inpainting 파이프라인 구축.
- 바닥(Floor) 텍스처 변경 (카펫, 나무, 타일)으로 시각적 일반화 테스트.

---

## 🧪 실험 계획
`augment=True` 옵션을 켠 상태로 `abs_action` 모델 추가 학습 진행.
- **Config**: `mobile_vla_kosmos2_aug_abs_20251209.json`
- **예상 결과**: 기존 `abs_action` 모델보다 더 낮은 Val Loss 및 더 높은 시각적 강건성 확보.

---

작성일: 2025-12-09

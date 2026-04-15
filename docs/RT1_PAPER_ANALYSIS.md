# 🔬 RT-1 (Robotics Transformer 1) 논문 분석 보고서

**날짜**: 2026-02-16  
**작성자**: Antigravity AI  
**주제**: RT-1: Robotics Transformer 1 - Real-World Robotics at Scale  

---

## 1. Background (배경)
RT-1(Robotics Transformer 1)은 Google Research에서 발표한 논문으로, 자연어 명령과 이미지 입력을 통해 로봇의 동작(Action)을 직접 출력하는 **End-to-End VLA(Vision-Language-Action) 모델**의 효시 중 하나입니다. 대규모 데이터셋과 Transformer 아키텍처를 로봇 제어에 도입하여, 실세계 태스크에서의 강력한 일반화(Generalization) 능력을 입증하는 것이 핵심 목표입니다.

- **핵심 철학**: "더 많은 데이터와 더 큰 모델이 NLP/CV에서 성공했듯이, 로봇공학에서도 통할 것인가?"
- **데이터 규모**: 13개 로봇을 동원해 17개월간 수집한 130,000개 이상의 에피소드.

---

## 2. Analysis (아키텍처 분석)

RT-1의 아키텍처는 효율적인 실시간 제어(3Hz)와 멀티모달 융합을 위해 다음과 같이 설계되었습니다.

### 2.1 주요 컴포넌트
1.  **Vision Encoder (EfficientNet-B3)**:
    - 입력 이미지(300x300)로부터 시각적 특징을 추출합니다.
    - **FiLM (Feature-wise Linear Modulation) Layer**: 텍스트 명령어 임베딩을 사용하여 시각 특징을 조건화(Conditioning)함으로써 태스크와 관련된 특징에 집중하게 합니다.
2.  **Token Learner**:
    - EfficientNet에서 추출된 다량의 토큰(81개)을 중요한 정보 위주로 **8개로 압축**합니다. 이는 Transformer의 연산량을 줄여 실시간 추론을 가능하게 합니다.
3.  **Transformer (Decoder-only)**:
    - 8개의 Self-attention 레이어와 약 1,900만 개의 파라미터를 가진 소규모 Transformer입니다.
    - 과거 6프레임의 히스토리를 입력을 받아 다음 액션을 예측합니다.
4.  **Action Tokenization**:
    - 액션을 연속적인 값이 아닌 **Discretized Tokens**로 처리합니다.
    - 총 11차원 액션: Arm (x, y, z, roll, pitch, yaw, gripper - 7D), Base (x, y, yaw - 3D), Mode (Termination - 1D).
    - 각 차원을 256개 빈(bin)으로 이산화하여 분류(Classification) 태스크로 풉니다.

### 2.2 하이퍼파라미터 및 주요 수치
| 항목 | 사양 (Specification) | 출처 섹션 |
| :--- | :--- | :--- |
| **Model Size** | 약 3,500만 파라미터 (Transformer 19M + Vision 16M) | Section 3.1 |
| **Input** | 이미지 시퀀스 (6 frames) + 자연어 명령어 | Section 3.2 |
| **Output Rate** | 3Hz (Real-time control) | Section 3.1 |
| **Discretization** | 256 bins per action dimension | Section 3.1 |

---

## 3. Findings (실험 결과 및 메트릭)

RT-1은 기존 베이스라인 모델(BC-Z, Gato) 대비 압도적인 성능과 일반화 성능을 보여주었습니다.

### 3.1 정량적 메트릭 (Success Rate)
- **Seen Tasks (700+ instructions)**: **97%** (BC-Z 72%, Gato 65% 대비 압도적)
- **Unseen Tasks**: **76%** (새로운 명령어에 대한 대응 능력)
- **Robustness (강건성)**:
    - Distractors (방해물): 83%
    - Backgrounds (배경 변화): 59%
- **Long-Horizon Tasks**: SayCan과 통합하여 50단계 이상의 복잡한 태스크 수행 가능.

### 3.2 모델 비교 분석 (Table)
RT-1 논문(Section 4)의 데이터를 기반으로 한 베이스라인 모델과의 비교입니다.

| 모델 (Model) | Architecture | 데이터셋 (Episodes) | Seen Task 성공률 | Unseen Task 성공률 |
| :--- | :--- | :--- | :--- | :--- |
| **BC-Z** | ResNet-18 + MLP | 130k | 72% | 52% |
| **Gato** | Transformer | 130k | 65% | 52% |
| **RT-1 (Ours)** | **EfficientNet + Transformer** | **130k** | **97%** | **76%** |

---

## 4. Conclusion (결론)

RT-1은 로봇 학습에서 **'데이터 스케일과 Transformer 아키텍처의 결합'**이 얼마나 강력한지를 보여준 이정표적인 논문입니다.

1.  **확장성 (Scalability)**: 데이터의 양과 태스크의 수에 따라 성능이 꾸준히 선형적으로 향상됨을 확인했습니다.
2.  **데이터 효율성**: 다양한 로봇과 태스크 데이터를 섞어 학습함으로써 단일 태스크 학습보다 더 나은 일반화 성능을 확보했습니다 (Multi-task learning synergy).
3.  **Legacy**: 이후 **RT-2 (Vision-Language-Action Models)**로 이어지며, LLM의 능력을 직접 로봇 제어링에 활용하는 기반 기술이 되었습니다.

---

## 🔍 코드 및 로컬 Evidence 확인
본 워크스페이스(`/home/billy/25-1kp/vla`)의 `simpler_env_repo` 내에는 RT-1을 평가하기 위한 유틸리티와 체크포인트 로딩 로직이 포함되어 있습니다.
- `simpler_env/policies/rt1`: RT-1 추론을 위한 TensorFlow 기반 구현체 확인.
- `docs/reports/vla_comparison_analysis.md`: 우리 모델(Mobile VLA, 500 에피소드)과 RT-1(130k 에피소드)의 데이터 규모 차이를 비교 분석한 자료가 이미 존재합니다.

---
**출처**: Brohan, A., et al. "RT-1: Robotics Transformer 1 - Real-World Robotics at Scale." arXiv (2022).

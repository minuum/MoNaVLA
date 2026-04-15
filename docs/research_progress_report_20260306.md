# Mobile VLA: 모바일 로봇 내비게이션을 위한 Vision-Language-Action 모델 연구 진행 보고서

> **작성일**: 2026-03-06  
> **연구 차수**: V1 → V2 → V3 (현재)  
> **현재 최고 모델**: v3-exp08 (epoch=07, val_loss=0.031, Offline PM=100%)

---

## 1. 연구 개요

### 문제 정의

모바일 로봇이 실내 환경에서 주어진 자연어 명령(Instruction)과 카메라 이미지만으로 장애물을 회피하고 목표물에 도달하는 **Navigation 태스크**를 수행하도록 학습시키는 것이 목표다.

**태스크 설정**
- 로봇: 2-wheel 모바일 플랫폼, 바닥 초저각 광각(Fisheye) 카메라
- 환경: 실내 교실 (흰색 벽, 콘크리트 바닥)
- 장애물: 갈색 플라스틱 컵형 화분
- 목표물: 직사각형 회색 세탁/수납 바구니
- 제어 출력: linear(전후진) + angular(좌우 회전) — 2-DOF

### VLA 연구 맥락

본 연구는 **Vision-Language-Action (VLA) 모델** 패러다임에 속한다. VLA는 사전 학습된 VLM(Vision-Language Model)의 풍부한 시각-언어 표현력을 그대로 활용하면서, 최소한의 파인튜닝만으로 로봇 액션 출력을 가능하게 하는 프레임워크다.

기존 로봇 학습과의 차별점:
- 기존: 도메인 특화 모델을 처음부터 학습 (대규모 데이터 필요)
- VLA: 사전 학습 VLM의 zero-shot 언어 이해·시각 추론 능력을 재사용 → 소규모 데이터로 특정 태스크 적응 가능

---

## 2. 시스템 아키텍처 파이프라인

```
[ 카메라 이미지 (720×1280, Fisheye) ]
         │  Image Encoder (Kosmos-2 ViT)
         ▼
[ 이미지 Patch Features ]
         │  Perceiver Resampler (64 latents)
         ▼
[ Compressed Visual Tokens ]──┐
                               │  concat
[ 텍스트 Instruction ]──────────┤
  (e.g., "Navigate to the    │
   gray basket while          │
   avoiding the brown bucket")│
         │  Language Encoder   │
         ▼                     │
[ Text Token Embeddings ]──────┘
         │
         ▼
[ Kosmos-2 Transformer (Frozen + LoRA Adapters) ]
   ─ window_size=8 (현재 + 이전 7프레임 히스토리 입력)
         │
         ▼
[ NavPolicy: MobileVLAClassificationDecoder ]
   ─ Hidden size: 1024
   ─ Num Layers: 4
   ─ Output: 9-class Logit vector
         │  Argmax
         ▼
[ 이산 액션 클래스 ]
  STOP | F | B | L | R | FL | FR | BL | BR
         │
         ▼
[ 로봇 제어 명령 (linear=0/1.15, angular=-1.15/0/1.15) ]
```

**핵심 설계 선택**

| 컴포넌트 | 선택 | 이유 |
|:---|:---|:---|
| 백본 | Kosmos-2 (Microsoft) | 이미지-텍스트 그라운딩에 특화. RoboVLMs 상류 코드와 호환 |
| Visual Compression | Perceiver Resampler (64 latents) | 이미지 토큰 수를 고정 크기로 압축 → 시퀀스 길이 제어 |
| 백본 학습 | LoRA (rank=32, α=64) | Full fine-tuning 대비 파라미터 효율적 |
| 액션 표현 | Discrete 9-class | 실제 액션 값이 on/off 이산 제어({0, 1.15}) → 분류 문제로 전환 |
| 히스토리 | Window=8, Chunk=1 | 직전 7프레임 이미지 맥락 활용, 1프레임씩 Reactive 제어 |

---

## 3. 모델 발전 역사

### Phase 1: V1 — Regression 기반 (2025년 12월 초·중순)

**시도**: VLM 백본 완전 Frozen + Action Head(LSTM) 만 학습. 연속 액션값(linear, angular) 직접 회귀(Regression).

| 실험 | Data | Chunk | Val Loss | 비고 |
|:---:|:---:|:---:|:---:|:---|
| chunk5_20251217 | L+R 500 | 5 | 0.067 | 방향 편향 문제 |
| chunk10_20251217 | L+R 500 | 10 | 0.284 | Overfitting |

**발견된 문제**
- 직진(F) 방향으로의 심각한 예측 편향: 대부분의 입력에 linear=1.15, angular=0 출력
- 이유: 데이터에서 F 클래스가 50% 비중 → 회귀가 평균에 수렴
- Chunk 크기가 클수록(k=10) Overfitting 심화 (Train-Val Gap: 0.290)

**얻은 교훈**: 연속값 회귀는 불균형 데이터에서 다수 클래스로 붕괴(collapse)하기 쉽다.

---

### Phase 2: V2 — Discrete Classification 도입 (2025년 12월 하순)

**시도**: 액션을 9-class 이산 분류(STOP, F, B, L, R, FL, FR, BL, BR)로 전환. 클래스 불균형을 Class Weights로 보정. VLM 여전히 Frozen.

| 실험 | Window | Chunk | Val Acc. | 특징 |
|:---:|:---:|:---:|:---:|:---|
| exp11_discrete | 8 | 1 | - | Classification 첫 시도 |
| exp16_win6_k1 | 6 | 1 | - | Window 축소 실험 |
| exp17_win8_k1 | **8** | **1** | **~94.72%** | 현재 최적 아키텍처 확정 |
| exp_v2_17 (basket) | 8 | 1 | **99.17%** | basket_dataset_v2 특화 |

**핵심 성과**
- Chunk=1(Reactive): 한 프레임씩 출력하는 반응형 정책이 짧은 Navigation 태스크에 최적임을 확인
- Window=8: CALVIN 벤치마크 50% 비율과 일치하는 최적 히스토리 길이 실험적 확인
- Discrete Classification: 방향 편향 문제 해소, 불균형 데이터에서도 안정적 수렴

**여전히 남은 문제**: VLM 백본이 Frozen → 데이터 도메인에 언어 그라운딩이 부족

---

### Phase 3: V3 — LoRA Fine-tuning (2026년 1월~현재)

**시도**: VLM 백본에 LoRA Adapter 삽입, 백본의 Attention 레이어를 경량으로 도메인 적응. Action Head도 함께 공동 학습.

#### V3 실험 계열 상세

| 실험 | LoRA (r/α) | LR | Class Weights | 데이터 필터 | Val Loss | PM/DM |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| exp01_aug | 16/32 | 5e-5 | 없음 | 전체 | - | - |
| exp02_baseline | 16/32 | 5e-5 | 없음 | 전체 | - | - |
| exp03_weighted | 16/32 | 5e-5 | F:0.1, L:5.0 | 전체 | - | - |
| **exp04_lora** | 16/32 | 5e-5 | F:0.2, L/R:5.0 | 전체 | 0.294 | 65.83% |
| **exp05_lora** | 16/32 | 5e-5 | F:0.1, L:10, R:2.0 | 전체 | 0.240 | **89.72%** |
| **exp06_lora** | 32/64 | 3e-5 | F:0.08, L:15 | **Left만** | 0.107 | **95.7%** |
| **exp07_lora** | **32/64** | **1e-5** | **실측 역수** | **L+R** | **0.053** | **97.9%** |
| **exp08 (현재)** | **32/64** | **1e-5** | **실측 역수** | **L+R** | **0.031** | **100%** |

#### EXP08의 핵심 변경사항

EXP07 대비 유일한 변경: **Instruction 재설계 (Goal-Centric 방식)**

```
EXP07 Instruction: "Navigate to the brown pot on the left"
                     ↑ 장애물이 목표물로 기술됨 (혼란)

EXP08 Instruction: "Navigate toward the gray basket until it is centered in the frame"
                     ↑ 목표물(gray basket)의 공간적 상태를 명시적으로 기술
```

**EXP08 평가 결과** (200 프레임 무작위 샘플)

| 방향 | 샘플 수 | PM | DM |
|:---:|:---:|:---:|:---:|
| Straight | 79 | 100% | 100% |
| Left | 49 | 100% | 100% |
| Right | 71 | 100% | 100% |
| Stop | 1 | 100% | 100% |
| **전체** | **200** | **100%** | **100%** |

---

## 4. 현재 상태와 발견된 한계

### 현재 상태 요약

- 오프라인(In-distribution) 성능: **PM/DM 100%** — 학습 도메인 내 예측 완벽
- 실제 추론(온라인) 성능: **반복적 직진 후 무질서한 조향** — 실환경 주행 실패

### 실환경 실패 원인 분석 (수치 기반)

#### 원인 1: 타이밍 암기 (Timing Memorization)

basket_dataset_v2 직접 파싱 결과:

| 검증 항목 | 측정값 |
|:---|:---:|
| Left 에피소드 유니크 Action 시퀀스 | **1개** (277/278 동일) |
| Right 에피소드 유니크 Action 시퀀스 | **1개** (250/250 동일) |
| 모든 프레임의 Action 결정성 | **100%** |
| 에피소드 간 Linear 표준편차 | **0.000** |
| 유니크 Linear 값 (전체 데이터셋) | `{0.0, 1.15}` (2가지) |

**고정 시퀀스** (Left 277개 에피소드 모두):
```
STOP | F F F F | L | FL FL FL | F F | FR FR FR | R | F F F
 F1    F2~F5   F6   F7~F9    F10~F11  F12~F14  F15  F16~F18
```

모든 에피소드가 동일한 Frame 번호에서 동일한 Action을 출력하므로, 모델이 이미지를 보지 않아도 **Frame 번호 → Action** 매핑 암기만으로 val_loss=0을 달성 가능했다.

#### 원인 2: FOV 이탈 (Field-of-View Loss)

실제 추론 이미지 분석:
- 로봇 카메라가 바닥 근접 초저각으로 장착되어 있어, 화분이 가까워질수록 카메라 수직 FOV 경계 아래로 사라짐
- 모델은 현재 프레임만 보는 Reactive Policy이므로, 화분이 화면에서 사라지는 순간 회피 근거가 없어지고 직진으로 복귀

#### 원인 3: Instruction과 실제 객체 불일치

```
학습 Instruction: "Navigate to the brown pot"  ← 장애물이 목표물로 기술
실제 목표:        gray basket
실제 장애물:      brown pot (화분)
```

VLM이 "가야 할 것"과 "피해야 할 것"을 혼동하여 학습했을 가능성.

---

## 5. 활용된 VLA 특성 및 설계 원칙

### 5.1 Pre-trained VLM의 시각-언어 그라운딩 재활용

Kosmos-2는 이미지 내 객체의 공간적 위치와 언어 명칭을 연결(Grounding)하는 사전 학습이 된 모델이다. "gray basket on the left"라는 표현이 이미지의 왼쪽에 있는 객체와 대응됨을 이미 학습한 상태에서 Navigation 태스크로 전이(Transfer)하는 전략을 채택했다.

### 5.2 Perceiver Resampler를 통한 시각 정보 압축

Raw 이미지는 720×1280 해상도로 너무 많은 토큰을 생성한다. 64개의 학습 가능한 Latent Query가 이미지 전체를 64개의 고정 크기 Visual Token으로 압축하여, Transformer의 시퀀스 길이를 일정하게 유지한다.

### 5.3 LoRA를 통한 경량 도메인 적응

Navigation 태스크는 사전 학습 데이터(인터넷 이미지)와 도메인 차이가 크다. LoRA(Low-Rank Adaptation)는 Attention 레이어의 Q, K, V, Out, FC1, FC2 행렬에 저차원 행렬(rank=32)을 추가하여, 파라미터의 0.1% 미만을 학습하면서 도메인 특화 표현을 획득한다.

### 5.4 Class Weights를 통한 불균형 처리

실제 데이터에서 F(직진) 클래스가 전체의 50%를 차지하는 반면, L(좌회전)은 2.9%에 불과하다. Cross-Entropy Loss에 실측 기반 역수 가중치를 적용하여 소수 클래스(L, R, STOP)의 학습 신호를 증폭시켰다.

| 클래스 | 비율 | 가중치 |
|:---:|:---:|:---:|
| STOP | 5.6% | 8.98 |
| F | 50.0% | 1.00 |
| L | 2.9% | 17.12 |
| R | 5.6% | 9.00 |
| FL | 16.7% | 3.00 |
| FR | 19.3% | 2.59 |

### 5.5 Window-based 히스토리 활용

단일 프레임만 보는 단순 Reactive Policy는 일시적 노이즈나 부분 가림(Occlusion)에 취약하다. 직전 7개 프레임을 함께 입력하여 "지금까지 무엇을 보았는가"에 기반한 의사결정을 가능하게 했다.

---

## 6. 현재 연구 위치

```
[기존 접근] 도메인 특화 모델을 처음부터 학습
      ↓ 발전
[V1 - 2025년 12월] VLM + 회귀 헤드 (Frozen Backbone)
      ↓ 문제: 직진 편향, 방향 구분 실패
[V2 - 2025년 12월 하순] Discrete 분류 전환, Chunk=1 확정
      ↓ 문제: 언어 그라운딩 부족 (Backbone Frozen)
[V3 - 2026년 1월~현재] LoRA 적용, Goal-Centric Instruction
      ↓ 현재 오프라인 100%, 실환경 실패
[Phase 2 — 계획] Dataset v3 다양성 확보 (Variant 에피소드 수집)
```

현재 프로젝트는 VLA 연구의 **"소규모 데이터로 특정 도메인 전이(Domain Transfer)"** 문제를 구체적으로 다루고 있으며, 발견된 **타이밍 암기(Timing Memorization)** 문제는 모방 학습(Imitation Learning) 분야에서 알려진 **Causal Confusion** 현상의 실제 사례이다.

> **Causal Confusion**: 모델이 언어-이미지 인과관계를 학습하는 것이 아니라, 데이터 내에 존재하는 비인과적 상관관계(에피소드 타이밍과 액션의 공분산)를 학습하는 현상.

---

## 7. 다음 단계 (Phase 2)

**목표**: 타이밍 암기가 수학적으로 불가능한 Dataset v3 구성

**핵심 원칙**: 같은 Frame 번호여도 이미지가 다르면 반드시 다른 액션이 대응되도록

| Variant | 수량 | 목적 |
|:---:|:---:|:---|
| Core (현행 유지, 100개) | 100 | 기준 성능 유지 |
| V1 Close (화분 50cm 앞) | 60 | Frame 1~2에서 즉시 회피 학습 |
| V2 Far (화분 3m 뒤) | 60 | Frame 8~10에서 늦은 회피 학습 |
| V3 Offset (화분 가장자리) | 40 | 소폭 조향 패턴 학습 |
| V4 No-obstacle | 40 | 장애물 없을 때 순수 직진 학습 |

---

*본 문서는 실제 코드·데이터·실험 로그에 기반하며 추측을 포함하지 않는다.*

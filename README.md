# MoNaVLA (Mobile Navigation Vision-Language-Action)
> 음료수 병을 향한 장애물 회피 주행을 위한 연구 및 구현

**최종 업데이트**: 2026-03-26  
**Status**: ✅ Phase 1.5 완료 (데이터 수집 고도화) | 🚀 Phase 2 진행중 (연속 제어 기반 정밀 주행 및 가중치 손실 도입)

---

## 📋 목차

- [프로젝트 개요](#-프로젝트-개요)
- [주요 성과 (V4-Regression)](#-주요-성과-v4-regression)
- [시스템 아키텍처](#-시스템-아키텍처)
- [VLA 모델 진화 역사 (V1~V4)](#-vla-모델-진화-역사-v1v4)
- [현재 한계점 및 Phase 2 계획](#-현재-한계점-및-phase-2-계획)
- [디렉토리 구조](#-디렉토리-구조)
- [문서](#-문서)
- [복구 문서](#-복구-문서)

---

## 🎯 프로젝트 개요

### 목표
모바일 로봇의 **명령 기반 장애물 회피 주행**을 위한 Vision-Language-Action (VLA) 모델 개발. "바스켓이 중앙에 올 때까지 향해라" 와 같은 자연어 지시를 이해하고 실제 조향 명령을 내립니다.

### 핵심 제원
- **Input**: RGB 이미지 (720x1280, Fisheye) + 자연어 명령(Instruction)
- **Output**: Continuous Regression (선속도/각속도의 2D 실수값 직접 예측)
- **VLM Backbone**: Kosmos-2 (`microsoft/kosmos-2-patch14-224`)
- **Optimization**: Weighted Huber Loss (Non-forward 가중치 5배 적용) + LoRA Fine-tuning

---

## 🏆 주요 성과 (V4-Regression)

현재 최신 모델인 **V4-Regression-v2**는 기존의 이산적(Discrete) 제어에서 벗어나 매끄러운 연속 제어를 실현하고, 불균형 데이터셋 문제를 손실 함수 가중치로 해결했습니다.

```text
Model: v4_regression_v2_weighted_v2
Checkpoint: runs/v4_nav/kosmos/mobile_vla_v4_regression_v2/.../last.ckpt
Strategy: Huber Loss + Non-forward Weight (5.0x) + ColorJitter/RandomCrop Aug
Impact: 기존 V1의 직진 편향(Forward Bias)을 완전히 극복하고 미세한 회전 조향 성공률 대폭 향상
```

---

## 🏗️ 시스템 아키텍처

### 1. VLA 모델 파이프라인 (Current: V4)

```mermaid
graph TD
    subgraph Input
        IMG[RGB Image <br> 720x1280] --> VE
        TXT[Text Instruction <br> 'Navigate toward...'] --> TE
    end

    subgraph "Frozen Kosmos-2 Backbone"
        VE[Vision Encoder] --> VX[Vision Features]
        TE[Text Encoder] --> TX[Text Features]
        VX --> CONCAT((Concat))
        TX --> CONCAT
    end

    subgraph "LoRA Fine-tuning"
        CONCAT --> LORA[Attention Layers + LoRA <br> rank=32, alpha=64]
    end

    subgraph "Continuous Policy Head"
        LORA --> RESAMPLE[Perceiver Resampler <br> 64 Latents]
        RESAMPLE --> LSTM[LSTM Decoder <br> Window Size = 8]
        LSTM --> REG[Regression Layer <br> Continuous 2D/10D Output]
    end

    REG --> OUT[Smooth Action <br> Linear_x, Linear_y]

    style LORA fill:#f9f,stroke:#333,stroke-width:2px
    style REG fill:#bbf,stroke:#333,stroke-width:2px
    style LSTM fill:#bbf,stroke:#333,stroke-width:2px
```

---

## 📈 VLA 모델 진화 역사 (V1~V4)

| 설계 | 접근 방식 | VLM 상태 | Action Head | 주요 발견 및 한계 |
|:---:|:---|:---:|:---|:---|
| **V1** | Continuous Regression | Frozen | Linear (Continuous 2D) | 직진(다수 클래스)으로 수렴하는 심각한 편향 발생 |
| **V2** | Discrete Classification | Frozen | Linear (9-Class) | 분류 문제로 변환하여 편향 극복. VLM Frozen으로 상호 이해 부족 |
| **V3** | Classification + LoRA | **LoRA** | LSTM + Linear (9-Class) | LoRA를 통한 Grounding 성공. 그러나 이산 제어로 인한 주행 불연속성 존재 |
| **V4** | **Weighted Regression** | **LoRA** | **LSTM + Continuous Head** | **Huber Loss + 가중치(5x)** 적용. 연속 제어의 부드러움과 회전 정밀도를 동시 확보 |

> 📌 **상세 실험 기록**: 모든 실험 메트릭과 히스토리는 [`docs/experiments_v1_to_v3_comprehensive.md`](docs/experiments_v1_to_v3_comprehensive.md)에서 확인할 수 있습니다.

---

## 🔍 현재 한계점 및 Phase 2 계획

### 한계점: "타이밍 암기(Timing Memorization)" 현상
V3-EXP08 모델 검증 결과, 오프라인 정확도 100%라는 수치가 **모델이 실제 시각적 객체(장애물, 목표)를 이해한 것이 아니라, 학습 데이터 에피소드의 '진행 시간(Frame 넘버)'과 액션을 단순 암기(Causal Confusion)한 결과**임이 밝혀졌습니다. (상세 분석: `docs/dataset_analysis_basket_v2_20260306.md`)

### Phase 2 해결 계획 (Dataset v3)
단순 프레임 암기를 파훼하기 위해, 동일 시간(Step)에 완전히 다른 시각적 맥락(장애물 유무, 늦은 등장 등)을 제공하는 **4가지 데이터 변형(Close, Far, Offset, No-obstacle)**을 신규 수집하기로 결정했습니다.
자세한 훈련 계획 및 검증 방안은 `docs/training_plan_dataset_v3_20260306.md` 문서에 정리되어 있습니다.

---

## 📁 디렉토리 구조

```
vla/
├── Mobile_VLA/              # 핵심 VLA 모델 구현부 (API, Configs)
├── RoboVLMs/                # VLM 백본 라이브러리 및 훈련 코어 (Kosmos-2 통합)
├── robovlm_nav/             # Customized Training Pipeline 및 Nav-Policy 구현
├── scripts/                 # 훈련 및 추론 실험용 유틸리티 스크립트 모음
├── docs/                    # 분석 보고서, 설계 문서, 가이드라인 (V1~V4 포함)
├── ROS_action/              # 로봇에서 수집된 실제 주행 데이터셋 경로
└── README.md                # 현재 개요 파일
```

---

## 📚 문서

프로젝트와 관련된 심도 있는 분석 및 계획은 `docs/` 내 다음 문서를 참고하세요:

- **[V1~V3 종합 실험 기록보관소](docs/experiments_v1_to_v3_comprehensive.md)**: 초창기 Regression부터 V3 LoRA Classification에 이르는 전체 하이퍼파라미터 및 손실/정확도 로깅
- **[Dataset v2 정량 분석 보고서](docs/dataset_analysis_basket_v2_20260306.md)**: "타이밍 암기" 문제에 대한 표준편차 및 Action Sequence 분석
- **[Dataset v3 훈련 계획서](docs/training_plan_dataset_v3_20260306.md)**: Causal Confusion을 깰 4가지 데이터 변형 및 Instruction 재설계
- **[연구 진행 리포트](docs/research_progress_report_20260306.md)**: 현재 연구 Phase 요약 및 아키텍처 개편 내역

# VLA Core Knowledge Base (핵심 기술 데이터베이스)

최근 Mobile VLA 프로젝트에서 정립된 핵심 기술 원리와 해결된 주요 이슈들을 정리한 문서입니다. 이 문서는 모델의 안정적인 학습과 성능 향상을 위한 "Core Database" 역할을 합니다.

---

## 1. 핵심 모델링 패러다임 (Core Paradigm)

### 1-1. Unified Regression (연속 액션 회귀)
*   **원리**: 기존의 이산적 토큰(Discrete Tokens) 분류 방식 대신, Huber Loss를 기반으로 한 **연속적인 속도(Velocity) 예측** 방식을 채택합니다.
*   **장점**: 제어의 해상도가 높아지며, 로봇 주행 시 발생하는 갑작스러운 불연속적 동작(Jerk)을 줄여 부드러운 주행이 가능합니다.
*   **구현**: `MobileVLALSTMDecoder`를 사용하여 시계열 정보를 반영한 속도 범위를 직접 회귀합니다.

### 1-2. Frozen VLM + Selective Training (고정형 VLM 전략)
*   **원리**: 대규모 VLM(Kosmos-2 1.6B)의 본체 가중치는 고정(Frozen)하고, 시각-언어 정보를 연결하는 **Projector와 Action Head**만을 학습합니다.
*   **이유**: LoRA Fine-tuning 시 발생하는 **언어 이해 능력 손상(Catastrophic Forgetting)**을 방지하고, 사전 학습된 강력한 공간 이해 능력을 그대로 유지하기 위함입니다. RT-2 및 RoboFlamingo와 같은 최신 연구의 추세를 따릅니다.

---

## 2. 주요 기술적 해결 사항 (Critical Fixes)

### 2-1. Gradient Flow 차단 문제 해결 (requires_grad)
*   **이슈**: 베이스 모델이 Frozen 상태일 때, 모델 입력부(`inputs_embeds`)에서 그래디언트 추적이 끊겨 역전파(Backpropagation)가 정상적으로 이루어지지 않는 `RuntimeError: No grad_fn` 발생.
*   **해결**: `base_backbone.py`의 forward pass에서 `multimodal_embeds.requires_grad_(True)`를 명시적으로 호출하여, 고정된 백본을 거치더라도 어댑터와 헤드로 그래디언트가 흐를 수 있도록 보장했습니다.

### 2-2. PEFT/LoRA 환경에서의 Gradient Checkpointing
*   **이슈**: 윈도우 크기를 12로 확장하면서 발생하는 메모리 부족(OOM)을 해결하기 위해 Checkpointing 시스템이 필요했습니다. 하지만 일반적인 방식은 PEFT 레이어와 충돌할 수 있습니다.
*   **해결**: `get_peft_model` 호출 직후 `self.backbone.gradient_checkpointing_enable()`을 호출하여 LoRA 어댑터와 백본 체크포인팅이 조화롭게 작동하도록 수정했습니다.

### 2-3. 손실 함수 키 정렬 (Loss Key Alignment)
*   **이슈**: Action Head가 반환하는 키(`loss_arm`)와 Trainer가 수집하는 키(`loss_arm_act`)가 일치하지 않아 학습 손실값이 비정상(0)으로 계산되던 문제.
*   **해결**: `mobile_vla_policy.py`의 반환 키를 베이스 시스템의 자동 접미사(`_act`) 생성 규칙에 맞춰 표준화했습니다.

---

## 3. 학습 설정 표준 (Training Standards)

### 3-1. Window Size & Data Horizon 매칭
*   **설정**: **Window Size 12**를 기본으로 사용하여 긴 과거 이력을 참조합니다.
*   **주의 사항**: 데이터셋의 에피소드 길이(예: 18프레임)를 고려하여, `Window Size` + `Prediction Horizon`이 총 길이를 초과하지 않도록 `fwd_pred_next_n`을 동적으로 조정해야 합니다 (최근 10 -> 6으로 조정하여 데이터 활용 극대화).

### 3-2. GPU 자원 최적화
*   **Adam Optimizer 메모리**: 1.6B 모델 학습 시 Optimizer 상태만으로도 메모리 점유가 큽니다.
*   **환경 관리**: 학습 시작 전 유휴 API 서버 등 GPU 메모리 점유 프로세스를 강제 종료(`kill`)하여 24GB 하드웨어 내에서 가용 메모리를 최대한 확보합니다.

---
**Last Updated**: 2026-02-05
**Status**: Unified Regression @ Win12 Fully Operational

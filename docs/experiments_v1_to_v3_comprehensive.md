# VLA V1~V3 실험 종합 기록보관소 (Comprehensive Experiment Registry)

본 문서는 Mobile VLA 프로젝트의 첫 실험부터 현재 최고 모델 도달까지의 모든 실험(Experiment) 설정을 빠짐없이 매핑한 공식 기록입니다.

**데이터 출처**: `MASTER_EXPERIMENT_TABLE.md`, `vla_mega_comparison_v1_v3.md`, `vla_v3_exp08_evaluation.md` 실측 수치

---

## 1. Phase 1: V1 (Regression) - 연속값 직접 추정

연속된 조향값(Linear, Angular)을 직접 회귀(Regression)하려던 초기 시도입니다. 직진 편향 현상이 심각했습니다.

| 실험명 (Config 기반) | 조향 방식 | 학습 방법 | Chunk Size | Window | 최고 성능 (Val Loss) | 결과 및 한계 |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| `frozen_lora_leftright_20251204` | Regression | Frozen VLM | 10 | 8 | 0.027 | Baseline 시도, 방향 구분 실패 |
| `kosmos2_fixed_20251209` | Regression | Frozen VLM | 10 | 8 | 0.048 | Xavier Init 수정, 성능 악화 |
| `kosmos2_aug_abs_20251209` | Regression | Frozen VLM | 10 | 8 | 0.050 | Data Augmentation + Abs Action 적용 |
| `right_only_20251207` | Regression | Frozen VLM | 10 | 8 | 0.016 | 우회전 전용 데이터, 일반화 실패 |
| `no_chunk_20251209` | Regression | Frozen VLM | 1 | 8 | 0.0005 | Val Loss 상 최고, 그러나 연속값 Overfitting |
| `mobile_vla_chunk5_20251217` | Regression | Frozen VLM | 5 | 8 | 0.067 | 10-Chunk 대비 Train-Val Gap 작음 |
| `mobile_vla_chunk10_20251217` | Regression | Frozen VLM | 10 | 8 | 0.284 | 시퀀스가 길어져 Overfitting 극심 |

> **얻은 교훈**: 불균형한 주행 데이터(직진 50% 이상)에서 Regression은 평균(직진)으로 수렴하는 심각한 편향(Bias)을 유발함.

---

## 2. Phase 1: V2 (Discrete Classification) - 이산 액션 분류

회귀의 한계를 깨닫고, 로봇의 실제 입력값이 `[-1.15, 0, 1.15]`라는 점에 착안하여 9-Class Classification으로 변경했습니다. 클래스 가중치를 두어 소수 움직임(조향)을 강조했습니다.

| 실험명 | 조향 방식 | 학습 방법 | Chunk | Window | 최고 성능 | 결과 및 한계 |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| `mobile_vla_v2_classification_9cls` | Classification | Frozen VLM | - | 8 | N/A | 이산 액션 분류 첫 도입 |
| `mobile_vla_exp11_discrete` | Classification | Frozen VLM | - | 8 | N/A | Resampler 적용 기반 Discrete 테스트 |
| `mobile_vla_exp16_win6_k1` | Classification | Frozen VLM | 1 | 6 | N/A | Window 크기 6으로 축소 테스트 |
| `mobile_vla_exp17_win8_k1` | Classification | Frozen VLM | 1 | 8 | 85.0% (Val Acc) | Window 8 + Chunk 1 이 최적임을 확정 |
| `mobile_vla_exp_v2_17` | Classification | Frozen VLM | 1 | 8 | 99.17% (PM) | 단일 방향(Left/Right 분리 학습) 시 완벽에 가까운 오프라인 수렴 |

> **얻은 교훈**: Classification 변경 만으로 편향 문제는 해소. 하지만 VLM 백본이 굳어(Frozen) 있어 이미지 도메인과 텍스트 명령어 간의 상호작용(Grounding) 학습 불가.

---

## 3. Phase 1: V3 (LoRA) - 시각·언어 그라운딩 튜닝

VLM 백본의 Attention 레이어에 파라미터를 소규모로 추가(LoRA)하여, 모바일 환경의 이미지와 명령어를 직접 매핑하도록 했습니다.

| 실험명 | LoRA (rank/α) | Learning Rate | Class Weights | 필터링 | 성능 (Val Loss / PM) | 비고 |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| `mobile_vla_v3_exp01_aug` | 16 / 32 | 5e-5 | 기본 | 전체 | N/A | LoRA 첫 도입, Data Augmentation |
| `mobile_vla_v3_exp02_baseline`| 16 / 32 | 5e-5 | 기본 | 전체 | N/A | 증강 기능 해제 베이스라인 |
| `mobile_vla_v3_exp03_weighted`| 16 / 32 | 5e-5 | F:0.1, L:5.0 | 전체 | N/A | 클래스 가중치 재도입 |
| `mobile_vla_v3_exp04_lora` | 16 / 32 | 5e-5 | F:0.2, L/R:5.0 | 전체 | 0.294 / 65.8% | Left/Right 가중치 본격 최적화 |
| `mobile_vla_v3_exp05_lora` | 16 / 32 | 5e-5 | F:0.1, L:10.0, R:2.0| 전체 | 0.240 / 89.7% | 가중치 편차 극대화로 성능 대폭 향상 |
| `mobile_vla_v3_exp06_lora` | 32 / 64 | 3e-5 | F:0.08, L:15.0| Left | 0.107 / 95.7% | LoRA rank 증가 및 LR 감소 |
| `mobile_vla_v3_exp07_lora` | 32 / 64 | 1e-5 | **데이터 실측 역수 적용**| **L+R** | **0.053 / 97.9%**| Data Aug 전면 해제 + 역수 가중치 |
| `mobile_vla_v3_exp08_center_goal` | **32 / 64** | **1e-5** | **데이터 실측 역수 적용**| **L+R** | **0.031 / 100%** | **Goal-Centric 프롬프트로 재설계** |

> **최종 도달 (EXP-08)**: 
> 기존 "장애물로 향해라(Navigate to the brown pot)" 대신, "바스켓이 중앙에 올 때까지 향해라(Navigate toward the gray basket until it is centered)"로 Instruction을 재설계한 후 PM(Perfect Match)과 DM(Direction Match)에서 **100%** 수렴(In-Distribution 기준)에 성공했습니다.

---

> 본 기록은 `vla-driving` 브랜치의 실측 로그(`runs/`, `.json`, `.csv`)를 바탕으로 재구성되었으며, 환각이나 미수행 실험의 추정치가 배제되었습니다.

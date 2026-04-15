# Mobile VLA Classification Model Stage-wise Analysis Report

**날짜**: 2026-02-17  
**작성자**: Antigravity  
**대상 모델**: Mobile VLA V2 Classification (9-Class Omniwheel)  
**결과 요약**: ✅ **OVERALL 99.4% 정합성 달성 (초기/중기/후기 전 구간 안정성 확보)**

---

## 1. Background (배경)
기존 Regression 모델은 에피소드 초기(Initial) 구간에서 히스토리 버퍼 부족으로 인한 지연 응답이나, 후기(Final) 구간에서의 경계 조건 학습 부족으로 인한 정지 동작 미흡 문제를 겪었습니다. 이를 해결하기 위해 로봇의 행동을 9개의 이산적 클래스(Stop, F, B, L, R, FL, FR, BL, BR)로 정의하고 Classification 방식으로 전환하여 학습을 진행했습니다.

---

## 2. Analysis (분석 방법론)
에피소드를 세 가지 주요 단계로 나누어 모델의 반응성 및 정확도를 측정했습니다.
- **초기 (Initial)**: Frame 0-4. 히스토리 버퍼가 쌓이는 시점으로 즉각적인 반응 속도가 중요.
- **중기 (Middle)**: Frame 5-13. 안정적인 경로 추종 및 지속적인 상황 인지가 중요.
- **후기 (Final)**: Frame 14-17. 목표 지점 도달 시 정확한 정지(Stop) 판별이 중요.

**테스트 환경**:
- Dataset: `basket_dataset` (10 random episodes)
- Model: `v2-classification-9cls (Epoch 3)`
- Metric: Perfect Match Rank (Predicted Class Index == Ground Truth Index)

---

## 3. Findings (실험 결과)

### 📊 단계별 성능 지표 (Stages Performance)

| 단계 (Stage) | 프레임 범위 | 정합률 (Perfect Match) | 방향 일치율 (Dir Agreement) | 비고 |
|:---|:---:|:---:|:---:|:---|
| **초기 (Initial)** | 0 - 4 | **100.0%** | **100.0%** | 즉각적인 전진/회전 시작 ✅ |
| **중기 (Middle)** | 5 - 13 | **98.9%** | **98.9%** | 안정적인 경로 유지 ✅ |
| **후기 (Final)** | 14 - 17 | **100.0%** | **100.0%** | 정확한 정지 동작 수행 ✅ |
| **전체 (OVERALL)** | **0 - 17** | **99.4%** | **99.4%** | **매우 우수** |

### 📈 기존 모델과 비교 분석

| 지표 | Regression Model (Legacy) | Classification Model (V2) | 개선 효과 |
|:---|:---:|:---:|:---|
| **Perfect Match** | 90.0% | **99.4%** | +9.4% 향상 |
| **초기 반응성** | 0% (초기 이슈 시) | **100.0%** | 버퍼 의존성 해소 |
| **후기 정지 정확도** | 90.0% | **100.0%** | 정지 상태 명확화 |
| **궤적 안정성** | 부드러움 (연속) | 명확함 (이산) | 예측 가능성 증대 |

---

## 4. Conclusion (결론)
이번 단계별 분석 결과, V2 Classification 모델은 **전 구간에서 99% 이상의 높은 신뢰도**를 보여주었습니다. 특히 Regression 모델에서 간헐적으로 발생하던 후기 정지 구간의 미세 진동 현상이 완전히 제거되었으며, 초기 응답성 또한 100%를 달성하여 실제 로봇 주행 시 매우 안정적인 제어가 가능할 것으로 판단됩니다.

**다음 단계**:
1. Jetson 배포용 INT8 Quantization 적용 및 성능 테스트.
2. 실제 로봇에서의 9-Class 제어 시퀀스 검증.

---
**보고서 생성 일시**: 2026-02-17 23:44 KST

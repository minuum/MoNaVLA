# Mobile VLA 실험 매트릭스 및 현황

**날짜**: 2025-12-07 10:05  
**목적**: CALVIN 스타일 ablation study를 위한 실험 현황 정리

---

## 📊 CALVIN 논문 스타일 실험 매트릭스

### 필요한 실험 (TABLE III 스타일)

| Backbone | Structure | Action Space | Data | Task | 상태 |
|:---|:---|:---:|:---:|:---:|:---:|
| **KosMos** | Policy-Head | Cont. | 500 | Left+Right | ✅ Done |
| **KosMos** | Policy-Head | Cont. | 250 | Right Only | ✅ Done |
| **KosMos** | Policy-Head | Cont. | 250 | Left Only | 📝 Todo |
| **KosMos** | LoRA + P.H. | Cont. | 500 | Left+Right | ⚠️ Old |
| **KosMos** | LoRA + P.H. | Cont. | 1000+ | Left+Right | 📝 Todo |

---

## 📋 현재 학습된 모델 상태

### ✅ Done (완료)

| 실험명 | 설정 | Val Loss | 방향 정확도 | 비고 |
|:---|:---|:---:|:---:|:---|
| **Case 2: Frozen L+R** | Frozen VLM + Action Head | **0.027** | **92%** | 메인 실험 |
| **Case 4: Right Only** | Frozen VLM + Action Head | **0.016** | - | 단일 방향 |
| **Old LoRA L+R** | LoRA + Action Head | 0.013 | - | 검증 필요 |

### 📝 Todo (해야 할 실험)

| 실험명 | 설정 | 데이터 | 우선순위 |
|:---|:---|:---:|:---:|
| **Case 3: Left Only** | Frozen VLM + Action Head | 250 | 🟡 중간 |
| **Case 1: LoRA L+R (New)** | LoRA + Action Head | 1000~3000 | 🔴 높음 |

---

## 🔬 비교 분석용 실험 결과 필요 목록

### TABLE III 스타일 (Action Space & Structure 비교)

| 항목 | 필요 데이터 | 현재 상태 |
|:---|:---|:---:|
| Consecutive Task 1 성공률 | forward_continuous 테스트 | 📝 Todo |
| Consecutive Task 2~5 성공률 | Multi-step 테스트 | 📝 Todo |
| Avg. Length | 평균 성공 길이 | 📝 Todo |

### TABLE IV 스타일 (Data Scale 비교)

| Data Scale | 모델들 | 현재 상태 |
|:---|:---|:---:|
| 0.1x (50 episodes) | 모든 모델 | 📝 Todo |
| 1x (500 episodes) | 모든 모델 | ✅ Done (일부) |
| 5x (2500 episodes) | 모든 모델 | ❌ 데이터 부족 |

---

## 📊 시각화를 위해 필요한 데이터

### 1. 방향별 정확도 비교표

| 모델 | Left 정확도 | Right 정확도 | 전체 |
|:---|:---:|:---:|:---:|
| **Frozen L+R** | 84% | 100% | **92%** |
| **Right Only** | - | ? | ? |
| **Left Only** | ? | - | ? |
| **LoRA L+R** | ? | ? | ? |

**상태**: Left Only 와 LoRA 테스트 필요

### 2. 의미 벡터 비교표

| 비교 | Cosine Sim | L2 Dist | CKA |
|:---|:---:|:---:|:---:|
| **Frozen: Left vs Right** | 0.894 | 2.26 | ✅ Done |
| **LoRA: Left vs Right** | ? | ? | 📝 Todo |
| **Frozen vs LoRA** | ? | ? | 📝 Todo |

**상태**: LoRA 모델 벡터 추출 필요

### 3. 학습 곡선 비교

| 모델 | Train Loss | Val Loss | 수렴 Epoch |
|:---|:---:|:---:|:---:|
| **Frozen L+R** | 0.012 | 0.036 | 8 |
| **Right Only** | ? | 0.016 | ? |
| **LoRA L+R** | ? | 0.013 | ? |

**상태**: 로그 파싱 필요

---

## 🚀 다음 단계 액션 플랜

### 즉시 실행 가능

| 순서 | 작업 | 소요 시간 | 효과 |
|:---:|:---|:---:|:---|
| 1 | Old LoRA 모델 방향 정확도 테스트 | 5분 | LoRA 성능 파악 |
| 2 | Right Only 모델 방향 정확도 테스트 | 5분 | 비교 데이터 |
| 3 | LoRA 의미 벡터 추출 | 10분 | Frozen vs LoRA 비교 |
| 4 | 학습 로그 파싱 (곡선 데이터) | 10분 | 시각화 |

### 새 학습 필요

| 순서 | 작업 | 소요 시간 | 효과 |
|:---:|:---|:---:|:---|
| 5 | Left Only 학습 | ~1시간 | 완전한 비교 |
| 6 | 데이터 확장 (1000개) | 수집 필요 | 스케일 비교 |

---

## 📈 CALVIN 스타일 결과표 템플릿

### TABLE III 스타일 결과표 (우리 실험)

| Backbone | Structure | Action Space | 방향 1 | 방향 2 | Avg Acc |
|:---|:---|:---:|:---:|:---:|:---:|
| KosMos | Policy-Head | Cont. | 0.84 | 1.00 | **0.92** |
| KosMos | LoRA+P.H. | Cont. | ? | ? | ? |

### TABLE IV 스타일 결과표 (Data Scale)

| Architecture | Data Scale | Task 1 | Task 2 | Avg |
|:---|:---:|:---:|:---:|:---:|
| KosMos P.H. | 0.5x (250) | ? | - | ? |
| KosMos P.H. | 1x (500) | 0.92 | ? | ? |
| KosMos LoRA | 1x (500) | ? | ? | ? |

---

## 📝 결론

### 현재 완료된 것

| 항목 | 상태 |
|:---|:---:|
| Frozen VLM + Action Head (L+R) | ✅ |
| Frozen VLM + Action Head (R) | ✅ |
| 방향 정확도 (Frozen L+R) | ✅ |
| 의미 벡터 분석 (Frozen) | ✅ |

### 표/시각화를 위해 부족한 것

| 항목 | 상태 | 해결 방법 |
|:---|:---:|:---|
| LoRA 방향 정확도 | 📝 | 기존 LoRA 모델 테스트 |
| Right Only 방향 정확도 | 📝 | 테스트 실행 |
| Frozen vs LoRA 벡터 비교 | 📝 | 벡터 추출 후 비교 |
| Left Only 실험 | 📝 | 새로 학습 필요 |
| 학습 곡선 데이터 | 📝 | 로그 파싱 |
| Data Scale 비교 | ❌ | 추가 데이터 필요 |

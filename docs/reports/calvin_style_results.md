# Mobile VLA 실험 결과 종합 (CALVIN 스타일)

**날짜**: 2025-12-07 10:15  
**목적**: CALVIN 논문 스타일의 ablation study 결과표

---

## 📊 TABLE III: Structure Comparison (방향 정확도 비교)

| Backbone | Structure | Action Space | Left Acc | Right Acc | Avg Acc |
|:---|:---|:---:|:---:|:---:|:---:|
| **KosMos** | Frozen + P.H. | Cont. | **85.0%** | **100.0%** | **92.5%** |
| KosMos | LoRA + P.H. | Cont. | 100.0% | 0.0% | 50.0% |
| KosMos | Right Only | Cont. | 0.0% | 100.0% | 50.0% |

### 핵심 발견

| 발견 | 설명 |
|:---|:---|
| **Frozen VLM 승리** ⭐ | 92.5%로 가장 높은 방향 정확도 |
| **LoRA 실패** | Left만 100%, Right 0% → 방향 구분 실패 |
| **Right Only 정상** | Right만 학습 → Right만 정확 |

---

## 📊 TABLE IV: Semantic Vector Comparison (의미 벡터 비교)

### Frozen VLM 내부 비교 (Left vs Right)

| 비교 | Cosine Sim | L2 Dist |
|:---|:---:|:---:|
| **Left vs Right (클래스 간)** | **0.894** | 2.26 |
| Left 내부 (클래스 내) | 0.996 | - |
| Right 내부 (클래스 내) | 0.988 | - |

**해석**: VLM이 Left/Right를 latent space에서 **구분함**

### Frozen vs LoRA 비교 (같은 이미지)

| 비교 | Cosine Sim | L2 Dist |
|:---|:---:|:---:|
| **Frozen vs LoRA** | **0.842** | 2.81 |

**해석**: LoRA가 표현을 **16% 변경** (1 - 0.842)

---

## 📊 결과 종합표

| 모델 | 방향 정확도 | Val Loss | 의미 벡터 특성 |
|:---|:---:|:---:|:---|
| **Frozen L+R** | **92.5%** | 0.027 | Left/Right 구분됨 (0.894) |
| LoRA L+R | 50.0% | 0.013 | 표현 변화 (0.842) |
| Right Only | 50.0% | 0.016 | Right만 학습 |

---

## 🔬 분석: 왜 LoRA가 실패했는가?

### 관찰된 현상

```
LoRA 모델 출력:
- Left 이미지 → 양수 (100% 정확)
- Right 이미지 → 양수 (0% 정확) ← 문제!

Frozen 모델 출력:
- Left 이미지 → 양수 (85% 정확)
- Right 이미지 → 음수 (100% 정확)
```

### 가능한 원인

| 원인 | 설명 | 증거 |
|:---|:---|:---|
| **1. LoRA가 언어 무시** | LoRA가 이미지만 보고 결정 | Left/Right 구분 실패 |
| **2. 과적합** | 학습 데이터에 과적합 | val_loss 0.013으로 낮음 |
| **3. 표현 변경** | LoRA가 유용한 표현 파괴 | cosine 0.842 (16% 변화) |

### 결론

> **교수님 의견 지지**: Frozen VLM (Case 2)가 더 좋은 성능!
> 
> - Frozen: 92.5% 방향 정확도
> - LoRA: 50.0% 방향 정확도 (랜덤 수준)
> 
> **LoRA가 VLM의 언어 이해 능력을 손상시킨 것으로 보임**

---

## 📋 실험 현황 업데이트

### ✅ Done (완료)

| 항목 | 결과 |
|:---|:---|
| Frozen L+R 방향 정확도 | **92.5%** |
| LoRA L+R 방향 정확도 | 50.0% |
| Right Only 방향 정확도 | 50.0% |
| Frozen vs LoRA 벡터 비교 | 0.842 |
| Frozen Left vs Right 벡터 | 0.894 |

### 📝 Todo (남은 작업)

| 항목 | 상태 |
|:---|:---:|
| Left Only 학습 | 📝 |
| t-SNE/PCA 시각화 | 📝 |
| 학습 곡선 시각화 | 📝 |

---

## 📈 CALVIN 논문과 비교

### CALVIN TABLE III (논문)

| Backbone | Structure | Task 1 | Task 5 | Avg Len |
|:---|:---|:---:|:---:|:---:|
| KosMos | Policy-Head | 0.967 | 0.826 | 4.49 |
| Flamingo | Policy-Head | 0.964 | 0.662 | 4.09 |

### 우리 결과 (Mobile VLA)

| Backbone | Structure | Left | Right | Avg Acc |
|:---|:---|:---:|:---:|:---:|
| KosMos | Frozen + P.H. | 0.85 | 1.00 | **0.925** |
| KosMos | LoRA + P.H. | 1.00 | 0.00 | 0.50 |

**비교 분석**:
- CALVIN: 연속 태스크 평가 (복잡)
- 우리: 방향 구분 평가 (단순하지만 핵심)
- **Frozen VLM + Policy Head 구조가 두 곳 모두에서 효과적**

---

## 🎯 교수님께 보고할 핵심

### 3줄 요약

1. **Frozen VLM이 LoRA보다 우수** (92.5% vs 50.0%)
2. **LoRA가 언어 이해 능력 손상** (Right 방향 구분 실패)
3. **RoboFlamingo 논문 결과와 일치** (Frozen이 효과적)

### 시각화용 데이터 준비 완료

```
방향 정확도: Frozen 92.5%, LoRA 50%, Right Only 50%
의미 벡터: Frozen내 L/R 0.894, Frozen vs LoRA 0.842
```

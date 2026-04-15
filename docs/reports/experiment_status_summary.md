# VLA 실험 현황 정리 및 다음 단계

**날짜**: 2025-12-07 03:45  
**교수님 의견**: Frozen VLM (Case 2)가 의미 있을 것 같다

---

## 📊 비율화 비교 (우리 모델 = 1.0 기준)

### 에피소드 수 비교

| 모델 | 에피소드 | 우리 대비 비율 | 시각화 |
|:---|---:|:---:|:---|
| OpenVLA (pre) | 970,000 | **1940x** | ████████████████████ |
| RT-2 | 73,499 | **147x** | ███████ |
| OpenVLA (fine) | ~100 | **0.2x** | █ |
| **우리 모델** | **500** | **1.0x** | █ |

### 태스크 수 비교

| 모델 | 태스크 | 우리 대비 비율 | 시각화 |
|:---|---:|:---:|:---|
| RT-2 | 200+ | **100x** | ████████████████████ |
| CALVIN | 32 | **16x** | ████████ |
| OpenVLA (pre) | 20+ | **10x** | █████ |
| **우리 모델** | **2** | **1.0x** | █ |

### 오브젝트 수 비교

| 모델 | 오브젝트 | 우리 대비 비율 | 시각화 |
|:---|---:|:---:|:---|
| RT-2 | 17 | **8.5x** | █████████ |
| CALVIN | ~10 | **5x** | █████ |
| **우리 모델** | **2** | **1.0x** | █ |

---

## 🔬 의미 벡터 분석 결과 (NEW!)

### Frozen VLM 내 Left vs Right 벡터 비교

```
클래스 간 유사도 (Left ↔ Right): 0.894
클래스 내 유사도 (Left ↔ Left): 0.996
클래스 내 유사도 (Right ↔ Right): 0.988
```

| 비교 항목 | Cosine Similarity |
|:---|:---:|
| **Left vs Right (평균)** | **0.900** |
| **Left 내부** | 0.996 |
| **Right 내부** | 0.988 |

### 해석

> **VLM의 의미 벡터에서 Left/Right 구분이 존재합니다!**
> - 클래스 간: 0.894 (10% 차이)
> - 클래스 내: 0.99+ (거의 동일)
> - **→ Latent space에서 Left/Right 클러스터가 분리됨**

### Case 1: LoRA + Action Head (Unfrozen VLM)

```
[Image] → [VLM + LoRA] → [의미 벡터 A] → [Action Head] → [Action]
            ↑
         학습됨
```

**특징**:
- VLM 자체가 로봇 태스크에 적응
- 더 많은 파라미터 학습 (LoRA weights)
- **데이터 많이 필요** (1000~3000개 권장)

### Case 2: Frozen VLM + Action Head (교수님 선호 ⭐)

```
[Image] → [Frozen VLM] → [의미 벡터 B] → [Action Head] → [Action]
              ↑                              ↑
           고정됨                          학습됨
```

**특징**:
- VLM의 사전학습 지식 보존
- Action Head만 latent space에 매칭
- **적은 데이터로 가능** (500개)
- Transfer Learning의 정석

---

## 🎯 핵심 비교: 의미 벡터 A vs B

### 분석 목표

```
Case 1 (LoRA):   Image → VLM_adapted → 의미 벡터 A
Case 2 (Frozen): Image → VLM_frozen  → 의미 벡터 B

질문: A와 B가 얼마나 다른가?
```

### 측정 방법

| 메트릭 | 설명 | 예상 |
|:---|:---|:---|
| **Cosine Similarity** | 방향 유사도 | 0.7~0.9? |
| **L2 Distance** | 거리 차이 | 의미 변화 측정 |
| **CKA (Centered Kernel Alignment)** | 표현 유사도 | 구조적 차이 |

---

## 📋 작업 현황 (Done / In Progress / Todo)

### ✅ Done (완료)

| 작업 | 날짜 | 결과 |
|:---|:---|:---|
| Case 2 학습 (Frozen + Action Head) | 12/04 | val_loss 0.027 |
| Left/Right 구분 검증 | 12/07 | **92% 정확도** |
| VLA 논문 비교 분석 | 12/07 | 비율화 완료 |
| 학부생 브리핑 문서 | 12/07 | 완료 |
| 추론 코드 수정 (forward_continuous) | 12/07 | 완료 |
| 정량적 성능 분석 (50 샘플) | 12/07 | RMSE 0.24 |

### 🔄 In Progress (진행 중)

| 작업 | 현황 | 다음 단계 |
|:---|:---|:---|
| Case 1 학습 (LoRA + Action Head) | 설정 필요 | 데이터 1000~3000개 고려 |
| 의미 벡터 비교 (A vs B) | 코드 준비 중 | 코사인 유사도 측정 |

### 📝 Todo (해야 할 일)

| 우선순위 | 작업 | 설명 |
|:---:|:---|:---|
| **1** | Case 1 데이터셋 확장 | 1000~3000개로 증가 |
| **2** | Case 1 학습 실행 | LoRA + Action Head |
| **3** | 의미 벡터 비교 분석 | 코사인, L2, CKA |
| **4** | 다른 논문 예시 수집 | Frozen vs LoRA 비교 논문 |
| **5** | 시각화 (t-SNE, PCA) | latent space 비교 |

---

## 🔗 다른 논문에서의 Frozen vs LoRA 비교

### 참고할 논문들

| 논문 | 접근법 | 결과 |
|:---|:---|:---|
| **RoboFlamingo** | Frozen VLM + Policy Head | CALVIN SOTA |
| **OpenVLA** | LoRA Fine-tuning | 다중 태스크 성능 |
| **VLM2VLA** | Frozen + Adapter | 효율적 Transfer |

### 핵심 인사이트

> **RoboFlamingo 논문 (교수님 의견 지지)**:
> "Frozen VLM + Fine-tuned Policy Head"로 CALVIN에서 SOTA 달성
> → VLM을 frozen시켜도 충분히 좋은 성능

---

## 🎯 다음 세션에서 할 일

### 즉시 실행 (우선순위 순)

1. **의미 벡터 비교 코드 작성**
   ```python
   # Case 2 (현재 모델) 의미 벡터 추출
   frozen_vector = model_frozen.encode_images(images)
   
   # Case 1 (LoRA 모델) 의미 벡터 추출 (학습 후)
   lora_vector = model_lora.encode_images(images)
   
   # 비교
   cosine_sim = F.cosine_similarity(frozen_vector, lora_vector)
   ```

2. **Case 1 데이터셋 확장 계획**
   - 현재: 500개
   - 목표: 1000~3000개
   - 방법: 추가 수집 or 증강

3. **비교 시각화 준비**
   - t-SNE / PCA / UMAP
   - Left vs Right 클러스터링

---

## 📊 교수님 미팅 준비 요약

### Case 2 (Frozen VLM) 장점 - 교수님 의견 지지

| 장점 | 설명 |
|:---|:---|
| **효율성** | 적은 데이터로 학습 가능 |
| **안정성** | VLM 사전지식 보존 |
| **해석성** | latent space 분석 용이 |
| **선례** | RoboFlamingo 성공 사례 |

### 다음 미팅에서 보여줄 것

1. ✅ Case 2 성능 (92% 방향 정확도)
2. 🔄 Case 1 vs Case 2 의미 벡터 비교
3. 📝 데이터 확장 계획

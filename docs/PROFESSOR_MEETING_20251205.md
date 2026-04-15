# 교수님 미팅 (2025-12-05) - VLM Frozen vs LoRA 비교 실험

**미팅 일시**: 2025-12-05 (목)  
**다음 미팅**: 2025-12-11 (수) 16:00  
**작성일**: 2025-12-05 20:00

---

## 📋 미팅 내용 요약

### 핵심 실험 제안: VLM 학습 방법 비교

**목적**: VLM을 Freeze 하는 것 vs LoRA로 Fine-tuning 하는 것의 효과 비교

---

## 🎯 두 가지 실험 방법

### 방법 1: VLM LoRA + Action Head (Fine-tuning)
```
구성:
  - VLM: LoRA로 Fine-tuning (일부 학습)
  - Action Head: 처음부터 학습
  
데이터 요구사항:
  - 많은 데이터 필요: 1,000~3,000 episodes
  - 이유: VLM 파라미터도 일부 업데이트되므로 더 많은 데이터 필요
  
출력:
  - Context Vector (의미 벡터)
  - Action predictions
```

### 방법 2: VLM Frozen + Action Head (Current approach)
```
구성:
  - VLM: Frozen (학습 안 함)
  - Action Head: 처음부터 학습
  
데이터 요구사항:
  - 적은 데이터로 가능: 500~1,000 episodes
  - 이유: Action Head만 학습
  
출력:
  - Context Vector (의미 벡터)
  - Action predictions
```

---

## 🔬 비교 분석 계획

### 1. Context Vector (의미 벡터) 비교

**추출 위치**:
```python
# VLM 출력 → Action Head 입력 사이
Context Vector = VLM.encode_images(images)  # Shape: (N, T, 64, 2048)

방법 1 (LoRA): context_lora
방법 2 (Frozen): context_frozen
```

**비교 메트릭**:
1. **Cosine Similarity (코사인 유사도)**
   ```python
   similarity = cosine_similarity(context_lora, context_frozen)
   # 1에 가까우면 유사, 0에 가까우면 다름
   ```

2. **Euclidean Distance (유클리드 거리)**
   ```python
   distance = torch.norm(context_lora - context_frozen, p=2)
   # 0에 가까우면 유사
   ```

3. **KL Divergence (분포 차이)**
   ```python
   kl_div = F.kl_div(context_lora, context_frozen)
   # 0에 가까우면 분포가 유사
   ```

4. **Feature Correlation (특징 상관관계)**
   ```python
   correlation = np.corrcoef(
       context_lora.mean(axis=0).flatten(),
       context_frozen.mean(axis=0).flatten()
   )[0, 1]
   ```

### 2. Latent Space 매칭 분석

**목적**: Action Head의 latent space에서 두 방법의 결과 비교

```python
# Action Head 내부 LSTM hidden state 추출
방법 1: latent_lora = action_head.lstm.hidden_state
방법 2: latent_frozen = action_head.lstm.hidden_state

비교:
  - Latent space distribution
  - Activation patterns
  - Feature importance
```

---

## 📊 실험 설계

### Case 4: VLM LoRA + Action Head
```
VLM: Kosmos-2 (LoRA fine-tuning)
Training: LoRA (rank=8) + Action Head
Data: 1,000 episodes (500 left + 500 right) - 추가 수집 필요
Epochs: 10
Learning Rate: 
  - VLM LoRA: 1e-5
  - Action Head: 1e-4

비교 대상: Case 3 (Frozen + Action Head)
```

### Case 3: VLM Frozen + Action Head (기존)
```
VLM: Kosmos-2 (Frozen)
Training: Action Head only
Data: 500 episodes (250 left + 250 right) - 보유
Epochs: 10
Learning Rate: 1e-4

현재 상태: ✅ 학습 완료
```

---

## 🔍 교수님 의견

### 방법 2 (Frozen) 가 의미 있을 것 같다

**이유 (추정)**:
1. **데이터 효율성**
   - 적은 데이터로도 학습 가능
   - Mobile-VLA는 현재 500 episodes만 보유

2. **VLM Pretrain 활용**
   - Kosmos-2가 이미 일반적인 vision-language 이해 능력 보유
   - Mobile task에 특화하지 않아도 될 가능성

3. **일반화 능력**
   - Frozen VLM은 다양한 task에 재사용 가능
   - Action Head만 교체하면 다른 task도 가능

4. **안정성**
   - VLM을 freeze하면 학습이 안정적
   - Catastrophic forgetting 방지

---

## 📝 다른 논문 사례 조사

### 관련 논문들

1. **RT-2 (Google DeepMind, 2023)**
   ```
   접근: VLM Frozen + Action tokens
   방법: PaLI-X VLM을 Frozen, action을 language token으로 출력
   결과: Frozen VLM도 robotic task에 효과적
   ```

2. **OpenVLA (2024)**
   ```
   접근: VLM Fine-tuning
   방법: DinoV2 + Llama를 전체 Fine-tuning
   데이터: 970K episodes (Open-X)
   결과: 많은 데이터로 Fine-tuning 시 성능 향상
   ```

3. **RoboFlamingo (2023)**
   ```
   접근: VLM Frozen + Few-shot
   방법: Flamingo VLM Frozen, Action Head만 학습
   결과: Few-shot으로도 좋은 성능
   ```

4. **PaLM-E (2023)**
   ```
   접근: VLM Fine-tuning
   방법: PaLM + ViT 전체 Fine-tuning
   데이터: 대규모 (수백만)
   결과: 많은 데이터 필요하지만 성능 우수
   ```

**패턴**:
- **Frozen**: 데이터 적을 때 효과적, 안정적
- **Fine-tuning**: 데이터 많을 때 성능 우수, 불안정

---

## 🎯 실험 계획 (환각 없이)

### Phase 1: 현재 상태 확인 (즉시 가능)
```
✅ Case 3 (Frozen) 학습 결과 분석
  - Checkpoint: epoch_epoch=08-val_loss=val_loss=0.027.ckpt
  - Context vector 추출
  - Latent space 분석
  
실행:
  1. Context vector 추출 스크립트 작성
  2. Latent space visualization
  3. Baseline 성능 정리
```

### Phase 2: 데이터 추가 수집 (필요시)
```
목표: 1,000 episodes (Case 4용)
현재: 500 episodes
추가: 500 episodes (250 left + 250 right)

난이도 다양화:
  - Easy: 100L + 100R
  - Medium: 150L + 150R (기존)
  - Hard: 100L + 100R

예상 소요: 1주일
```

### Phase 3: Case 4 (LoRA) 학습
```
Config 작성:
  - VLM: LoRA (rank=8, alpha=16)
  - Action Head: LSTM
  - Data: 1,000 episodes

학습 실행:
  - Epochs: 10
  - 예상 시간: 6~8시간

비교 분석:
  - vs Case 3 (Frozen)
  - Context vector 차이
  - Latent space 차이
  - 성능 차이
```

### Phase 4: 비교 분석 및 시각화
```
1. Context Vector 비교
   - Cosine similarity
   - Distribution plot
   - t-SNE visualization

2. Latent Space 비교
   - LSTM hidden state 추출
   - Activation patterns
   - Feature importance

3. 성능 비교
   - Val Loss
   - RMSE
   - Generalization (left/right)

4. 논문 수준 시각화 생성
```

---

## 📅 타임라인 (수요일 미팅까지)

### Day 1 (목, 12/5): 계획 수립 ✅
```
✅ 미팅 내용 정리
✅ 실험 계획 수립
⬜ Context vector 추출 스크립트 작성
```

### Day 2 (금, 12/6): Baseline 분석
```
⬜ Case 3 context vector 추출
⬜ Latent space visualization
⬜ Baseline 성능 정리
⬜ 논문 사례 조사 및 정리
```

### Day 3-4 (토-일, 12/7-8): 데이터 수집 (선택)
```
⬜ 추가 500 episodes 수집 여부 결정
⬜ 수집 시 난이도 다양화
```

### Day 5-6 (월-화, 12/9-10): Case 4 실험
```
⬜ LoRA config 작성
⬜ Case 4 학습 실행
⬜ Context vector 추출
⬜ 비교 분석
```

### Day 7 (수, 12/11): 미팅 준비
```
⬜ 결과 정리
⬜ 시각화 생성
⬜ 발표 자료 준비
```

---

## 📊 예상 결과 (가설)

### 가설 1: Context Vector가 유사할 것
```
Frozen vs LoRA context similarity > 0.8

이유:
  - 같은 Kosmos-2 backbone
  - Mobile task가 비교적 단순
  - LoRA가 일부 파라미터만 조정
```

### 가설 2: Latent Space는 다를 것
```
Frozen vs LoRA latent space difference > 0.3

이유:
  - Action Head가 다르게 학습됨
  - Input distribution이 약간 다름
  - LSTM이 다른 패턴 학습
```

### 가설 3: 성능은 비슷할 것
```
|Loss_frozen - Loss_lora| < 0.01

이유:
  - Mobile task가 단순
  - 500 vs 1000 episodes 차이
  - VLM frozen도 충분한 context 제공
```

---

## 🔬 비교 메트릭 정리

### 1. Context Vector 레벨
| 메트릭 | 수식 | 의미 | 목표 |
|:---|:---|:---|:---|
| Cosine Similarity | cos(θ) = (A·B)/(‖A‖‖B‖) | 방향 유사도 | > 0.8 |
| Euclidean Distance | d = ‖A - B‖₂ | 절대 거리 | < 0.5 |
| Correlation | r = corr(A, B) | 선형 관계 | > 0.7 |

### 2. Latent Space 레벨
| 메트릭 | 측정 대상 | 의미 |
|:---|:---|:---|
| Hidden State Similarity | LSTM h_n | 시간적 표현 비교 |
| Activation Pattern | Layer-wise | 학습된 패턴 비교 |
| Feature Importance | Attention weights | 중요 feature 비교 |

### 3. Performance 레벨
| 메트릭 | Case 3 (Frozen) | Case 4 (LoRA) | 차이 |
|:---|:---:|:---:|:---:|
| Val Loss | 0.027 | ??? | ??? |
| Train Loss | 0.0123 | ??? | ??? |
| RMSE | 0.170 | ??? | ??? |

---

## 📚 참고 문헌 (추가 예정)

1. RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control
2. OpenVLA: An Open-Source Vision-Language-Action Model
3. RoboFlamingo: Vision-Language Foundation Models for Robot Manipulation
4. PaLM-E: An Embodied Multimodal Language Model
5. LoRA: Low-Rank Adaptation of Large Language Models

---

## ✅ Action Items (우선순위)

### Immediate (이번 주)
```
1. ✅ 미팅 내용 정리 및 문서화
2. ⬜ Context vector 추출 스크립트 작성
3. ⬜ Case 3 baseline 분석 완료
4. ⬜ 논문 사례 조사 및 정리
```

### Short-term (다음 주)
```
5. ⬜ 데이터 추가 수집 여부 결정
6. ⬜ Case 4 (LoRA) config 작성
7. ⬜ Case 4 학습 실행
8. ⬜ 비교 분석 및 시각화
```

### Before Meeting (수요일 전)
```
9. ⬜ 결과 정리
10. ⬜ 발표 자료 준비
11. ⬜ 추가 실험 계획 제안
```

---

## 💡 교수님께 추가 질문 사항 (다음 미팅)

1. **데이터 규모**
   - 500 vs 1,000 episodes로 충분한가?
   - 추가 수집 필요성?

2. **LoRA 설정**
   - Rank는 8로 충분한가?
   - 어떤 layer를 tuning 할 것인가?

3. **비교 기준**
   - Context vector 유사도 threshold?
   - 어느 정도 차이가 의미 있는가?

4. **후속 연구**
   - 두 방법의 장단점 분석 후 방향?
   - 논문 작성 시 어느 결과를 사용?

---

**다음 미팅**: 2025-12-11 (수) 16:00  
**준비 사항**: Case 3 분석 완료, Case 4 진행 상황, 비교 결과 (가능하면)

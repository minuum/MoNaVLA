# Experiment Configuration - Strategy Explanation

**목적**: 각 실험 케이스의 Strategy가 무엇을 의미하는지 상세 설명

---

## Strategy 상세 설명

### Case 1: Baseline
**전략**: 기본 설정 (특수 기법 없음)

**의미**:
- **Frozen Backbone**: VLM(Kosmos-2)의 backbone은 freeze
- **LoRA Fine-tuning**: LoRA adapter만 학습
- **Standard Settings**: 
  - Action chunking: fwd_pred_next_n=10 (표준)
  - No data augmentation
  - No special action processing
  - Xavier initialization (기본값)

**역할**: 
- 모든 비교의 기준점 (Baseline)
- 다른 전략들의 효과를 측정하는 기준

**결과**: Val Loss 0.027

---

### Case 2: Xavier Init
**전략**: Xavier 초기화 수정

**의미**:
- Case 1과 동일한 기본 설정
- **차이점**: Action head의 initialization 방법 변경
  - 기본: Kaiming/He initialization
  - Case 2: **Xavier initialization**으로 명시적 변경
  
**목적**: 
- Initialization 방법이 성능에 미치는 영향 검증
- 다른 초기화 strategyrhk 비교

**가설**: Xavier init이 더 안정적인 학습을 제공할 것
**결과**: Val Loss 0.048 (오히려 악화)
**결론**: 기본 초기화가 더 우수

---

### Case 3: Aug+Abs
**전략**: 데이터 증강 + 절대값 액션

**의미**:
1. **Data Augmentation** (`augment=True`):
   - 이미지 증강 (밝기, 대비, 회전 등)
   - 목적: 모델의 일반화 성능 향상
   - 학습 데이터를 다양하게 변형

2. **Absolute Action** (`abs_action=True`):
   - 액션 처리 방식 변경
   - 일반: `linear_y` 그대로 사용 (음수/양수)
   - abs_action: `|linear_y| * direction_from_language`
   - 언어에서 방향 추출 ("go left" → direction=-1)
   - 최종 액션: 절대값 × 방향

**목적**: 
- 방향 정확도 100% 보장 (언어 파싱)
- 데이터 증강으로 robustness 향상

**결과**: Val Loss 0.050 (효과 없음)
**결론**: Chunk=10에서는 Aug+Abs 조합이 비효율적

---

### Case 4: Baseline
**전략**: 기본 설정 (Case 1과 동일)

**의미**:
- Case 1과 완전히 동일한 설정
- **차이점은 데이터만**:
  - Case 1: L+R (500 episodes)
  - Case 4: R only (250 episodes)

**목적**: 
- 데이터 규모 효과 검증
- 단순화 (Right only)의 영향 측정

**결과**: Val Loss 0.016 (Case 1보다 우수)
**이유**: 
- 단순한 태스크 (한 방향만)
- 데이터가 적어도 단일 방향은 잘 학습

**한계**: 일반화 부족 (Left 방향 불가)

---

### Case 5: No Chunk ⭐
**전략**: Action Chunking 제거

**의미**:
1. **No Action Chunking**:
   - 일반: fwd_pred_next_n=10 (10개 미래 액션 예측)
   - Case 5: fwd_pred_next_n=1 (현재 액션만 예측)
   
2. **Reactive Policy**:
   - Chunk=10: "다음 10 step 계획" (복잡)
   - Chunk=1: "지금 뭘 할까" (단순)
   
3. **Immediate Response**:
   - 매 step마다 새로운 관측에 즉시 반응
   - Navigation에 최적 (Reactivity > Precision)

**왜 성공했는가?**:
- **Task 특성**: 2D Navigation은 실시간 반응이 중요
- **Data 부족**: 500 episodes로는 복잡한 chunk 예측 어려움
- **Model 용량**: LoRA는 단순한 태스크에 집중

**결과**: Val Loss **0.000532** (최고!)
**개선**: Case 1 대비 98% 향상 (50배)

---

### Case 8: No Chunk+Abs
**전략**: No Chunking + 절대값 액션

**의미**:
1. **No Chunk** (from Case 5):
   - fwd_pred_next_n=1
   - 즉각 반응형 정책

2. **Absolute Action** (from Case 3):
   - abs_action=True
   - 방향을 언어에서 추출
   - 100% 방향 정확도 보장

**목적**: 
- Case 5의 성능 + 방향 정확도 보장
- 최고 전략(No Chunk) + 안정성(Abs Action)

**Trade-off**:
- 장점: 방향 오류 0%
- 단점: 학습 난이도 증가
  - 모델이 언어 파싱 + 액션 예측 동시 수행
  - 출력 공간 복잡도 증가

**결과**: Val Loss 0.00243
- Case 5보다 4.6배 높음
- 하지만 여전히 Case 1-4보다 우수

**결론**: 안정성과 성능의 균형점

---

## Strategy 요약 비교

| Strategy | 핵심 기법 | 목적 | 효과 |
|:---|:---|:---|:---|
| **Baseline** | 기본 설정 | 비교 기준 | 0.027 |
| **Xavier Init** | 초기화 변경 | 학습 안정성 | ❌ 0.048 (악화) |
| **Aug+Abs** | 증강 + 절대액션 | 일반화 + 방향 정확도 | ❌ 0.050 (효과 없음) |
| **No Chunk** | Chunking 제거 | 즉각 반응 | ✅ 0.000532 (최고!) |
| **No Chunk+Abs** | 즉각 반응 + 절대액션 | 성능 + 안정성 | ✅ 0.00243 (2등) |

---

## 핵심 인사이트

### 1. 단순함이 최고
- **No Chunk** (단순) >> **Chunk=10** (복잡)
- Navigation 태스크는 즉각 반응이 중요
- 복잡한 전략(Aug, Abs)은 Chunk=10에서 비효율적

### 2. Task-Strategy Alignment
- **Manipulation** (조작): Chunk 필요 (정밀도)
- **Navigation** (주행): No Chunk 최적 (반응성)

### 3. Data Efficiency
- 500 episodes로는 단순한 전략만 가능
- Chunk=10은 학습 데이터 부족
- Chunk=1은 충분

### 4. Trade-offs
- **Case 5**: 최고 성능, 방향 미검증
- **Case 8**: 방향 보장, 성능 약간 감소
- 선택: 배포 환경의 우선순위에 따름

---

## 기술 용어 설명

### Action Chunking (fwd_pred_next_n)
```python
# Chunk=10
model.predict() → [action_0, action_1, ..., action_9]
# 10 timesteps 미래까지 예측

# Chunk=1 (No Chunk)
model.predict() → [action_0]
# 현재 timestep만 예측
```

### Absolute Action (abs_action)
```python
# Standard
linear_y = model.predict()  # -1.0 ~ +1.0
# 음수 = 왼쪽, 양수 = 오른쪽

# Absolute Action
linear_y_abs = |model.predict()|  # 0.0 ~ 1.0 (always positive)
direction = extract_from_language(instruction)  # "left" → -1, "right" → +1
linear_y_final = linear_y_abs * direction
```

### Data Augmentation
```python
# Augmentation 예시
original_image → [
    brightness_adjusted,
    contrast_adjusted,
    rotated_slightly,
    ...
]
# 학습 데이터 다양성 증가
```

---

**작성**: 2025-12-10 12:20  
**문서**: Strategy 상세 설명서  
**목적**: 각 실험의 전략을 명확히 이해

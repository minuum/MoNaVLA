# 실험 설계 매트릭스 (Experiment Design Matrix)

**작성일**: 2025-12-10 01:55  
**목적**: 모든 실험 케이스를 변수별로 분해하고 가능한 조합 분석

---

## 1. 실험 변수 분류

### 현재 실험명 분석

| Case | 실험명 | 변수 추출 |
|:---:|:---|:---|
| 1 | mobile_vla_kosmos2_frozen_lora_leftright_20251204 | kosmos2 + frozen_lora + leftright + baseline |
| 2 | mobile_vla_kosmos2_fixed_20251209 | kosmos2 + frozen_lora + leftright + fixed |
| 3 | mobile_vla_kosmos2_aug_abs_20251209 | kosmos2 + frozen_lora + leftright + aug_abs |
| 4 | mobile_vla_kosmos2_right_only_20251207 | kosmos2 + frozen_lora + right_only + baseline |
| 5 | mobile_vla_no_chunk_20251209 | kosmos2 + frozen_lora + leftright + no_chunk |

### 독립 변수 (Independent Variables) 정의

#### A. 데이터 범위 (Data Scope)
- **A1**: `leftright` = Left + Right 전체 (500 episodes)
- **A2**: `right_only` = Right 방향만 (250 episodes)

#### B. Action Chunking 전략
- **B1**: `chunk` = fwd_pred_next_n=10 (기본값, 명시 안 함)
- **B2**: `no_chunk` = fwd_pred_next_n=1 (명시함)

#### C. 특수 전략 (Special Strategy)
- **C1**: `baseline` = 특별한 전략 없음 (명시 안 함)
- **C2**: `fixed` = Xavier initialization 수정
- **C3**: `abs_action` = 절대값 액션 + 방향 언어 추출
- **C4**: `aug_abs` = 데이터 증강 + abs_action

#### D. 모델 (Model) - 고정
- **D1**: `kosmos2` (모든 실험 동일)

#### E. 학습 방식 (Training Method) - 고정
- **E1**: `frozen_lora` (모든 실험 동일)

---

## 2. 실험 케이스 매핑

### 현재 수행된 실험

| Case | A (Data) | B (Chunk) | C (Strategy) | D (Model) | E (Training) | Val Loss | 상태 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | A1 (L+R) | B1 (chunk) | C1 (baseline) | D1 | E1 | 0.027 | 완료 |
| 2 | A1 (L+R) | B1 (chunk) | C2 (fixed) | D1 | E1 | 0.048 | 완료 |
| 3 | A1 (L+R) | B1 (chunk) | C4 (aug_abs) | D1 | E1 | 0.050 | 완료 |
| 4 | A2 (R only) | B1 (chunk) | C1 (baseline) | D1 | E1 | 0.016 | 완료 |
| 5 | A1 (L+R) | B2 (no_chunk) | C1 (baseline) | D1 | E1 | 0.000532 | 완료 |

---

## 3. 가능한 모든 조합 (Combinatorial Space)

### 조합 가능 수

```
총 조합 = A × B × C × D × E
        = 2 × 2 × 4 × 1 × 1
        = 16가지
```

### 전체 조합 매트릭스

| # | Data (A) | Chunk (B) | Strategy (C) | Model (D) | Training (E) | 실험명 예시 | 수행 여부 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---|:---:|
| 1 | A1 | B1 | C1 | D1 | E1 | mobile_vla_kosmos2_leftright | **Case 1** |
| 2 | A1 | B1 | C2 | D1 | E1 | mobile_vla_kosmos2_leftright_fixed | **Case 2** |
| 3 | A1 | B1 | C3 | D1 | E1 | mobile_vla_kosmos2_leftright_abs_action | 미수행 |
| 4 | A1 | B1 | C4 | D1 | E1 | mobile_vla_kosmos2_leftright_aug_abs | **Case 3** |
| 5 | A1 | B2 | C1 | D1 | E1 | mobile_vla_kosmos2_leftright_no_chunk | **Case 5** |
| 6 | A1 | B2 | C2 | D1 | E1 | mobile_vla_kosmos2_leftright_no_chunk_fixed | 미수행 |
| 7 | A1 | B2 | C3 | D1 | E1 | mobile_vla_kosmos2_leftright_no_chunk_abs | 미수행 |
| 8 | A1 | B2 | C4 | D1 | E1 | mobile_vla_kosmos2_leftright_no_chunk_aug_abs | 미수행 |
| 9 | A2 | B1 | C1 | D1 | E1 | mobile_vla_kosmos2_right_only | **Case 4** |
| 10 | A2 | B1 | C2 | D1 | E1 | mobile_vla_kosmos2_right_only_fixed | 미수행 |
| 11 | A2 | B1 | C3 | D1 | E1 | mobile_vla_kosmos2_right_only_abs_action | 미수행 |
| 12 | A2 | B1 | C4 | D1 | E1 | mobile_vla_kosmos2_right_only_aug_abs | 미수행 |
| 13 | A2 | B2 | C1 | D1 | E1 | mobile_vla_kosmos2_right_only_no_chunk | 미수행 |
| 14 | A2 | B2 | C2 | D1 | E1 | mobile_vla_kosmos2_right_only_no_chunk_fixed | 미수행 |
| 15 | A2 | B2 | C3 | D1 | E1 | mobile_vla_kosmos2_right_only_no_chunk_abs | 미수행 |
| 16 | A2 | B2 | C4 | D1 | E1 | mobile_vla_kosmos2_right_only_no_chunk_aug_abs | 미수행 |

**진행률**: 5/16 = 31.25%

---

## 4. 변수별 효과 분석

### 데이터 범위 효과 (A1 vs A2)

| Condition | A1 (L+R, 500ep) | A2 (R only, 250ep) | 차이 |
|:---|:---:|:---:|:---:|
| Baseline + Chunk | 0.027 (Case 1) | 0.016 (Case 4) | A2가 낮음 (단순화 효과) |

**결론**: Right만 사용하면 Loss는 낮지만 일반화 부족

### Action Chunking 효과 (B1 vs B2)

| Condition | B1 (chunk=10) | B2 (no_chunk=1) | 개선율 |
|:---|:---:|:---:|:---:|
| L+R + Baseline | 0.027 (Case 1) | 0.000532 (Case 5) | **98% (50배)** |

**결론**: No Chunk가 압도적 효과

### 특수 전략 효과 (C1 vs C2 vs C4)

| Condition | C1 (baseline) | C2 (fixed) | C4 (aug_abs) |
|:---|:---:|:---:|:---:|
| L+R + Chunk | 0.027 (Case 1) | 0.048 (Case 2) | 0.050 (Case 3) |

**결론**: 특수 전략들이 오히려 성능 악화 (기본이 최고)

---

## 5. 핵심 발견사항

### 가장 중요한 변수: Action Chunking (B)

```
효과 크기:
B (Chunking)  >>> A (Data) > C (Strategy)
  98% 개선        41% 악화      77% 악화
```

### 최적 조합

**현재 최고**: Case 5 (A1 + B2 + C1)
- Data: Left+Right 전체
- Chunking: No Chunk
- Strategy: Baseline (특수 전략 없음)

**Val Loss**: 0.000532

### 추가 실험 가치

#### 높은 우선순위

| # | 조합 | 예상 효과 | 이유 |
|:---:|:---|:---|:---|
| 7 | A1+B2+C3 | abs_action + no_chunk | 방향 정확도 향상 가능성 |
| 8 | A1+B2+C4 | aug_abs + no_chunk | 데이터 증강 + 최고 전략 |

#### 낮은 우선순위

| # | 조합 | 예상 효과 | 이유 |
|:---:|:---|:---|:---|
| 13 | A2+B2+C1 | right_only + no_chunk | 이미 Case 5가 더 나음 |
| 6 | A1+B2+C2 | no_chunk + fixed | Case 2가 실패했으므로 기대 낮음 |

---

## 6. 실험 공간 시각화

### 2D 매트릭스 (Data × Chunking)

|  | B1 (Chunk=10) | B2 (No Chunk=1) |
|:---|:---:|:---:|
| **A1 (L+R)** | Case 1: 0.027 | **Case 5: 0.000532** ⭐ |
| **A2 (R only)** | Case 4: 0.016 | 미수행 (#13) |

### 3D 매트릭스 (Data × Chunking × Strategy)

#### L+R 데이터 (A1)

|  | C1 (baseline) | C2 (fixed) | C3 (abs) | C4 (aug_abs) |
|:---|:---:|:---:|:---:|:---:|
| **B1 (chunk)** | 0.027 | 0.048 | - | 0.050 |
| **B2 (no_chunk)** | **0.000532** ⭐ | - | - | - |

#### Right Only 데이터 (A2)

|  | C1 (baseline) | C2 (fixed) | C3 (abs) | C4 (aug_abs) |
|:---|:---:|:---:|:---:|:---:|
| **B1 (chunk)** | 0.016 | - | - | - |
| **B2 (no_chunk)** | - | - | - | - |

**명확한 패턴**: B2 (No Chunk) 조합이 압도적

---

## 7. 향후 실험 제안

### Tier 1: 필수 (No Chunk 조합 완성)

```
우선순위 1: A1 + B2 + C3 (no_chunk + abs_action)
- 목적: 최고 성능 + 방향 정확도 보장
- 예상: Val Loss 0.001 이하 + 95% 방향 정확도

우선순위 2: A1 + B2 + C4 (no_chunk + aug_abs)
- 목적: 데이터 증강 효과 검증
- 예상: Val Loss 0.001 이하
```

### Tier 2: 참고 (Right Only 조합)

```
우선순위 3: A2 + B2 + C1 (right_only + no_chunk)
- 목적: 단순화 극대화
- 예상: Val Loss ~0.0001
- 문제: 일반화 부족
```

### Tier 3: 저우선순위 (Fixed 조합)

```
Case 2, Case 3 실패 사례로 보아 C2, C4 전략은 효과 없음
더 이상 실험 불필요
```

---

## 8. 실험 명명 규칙 제안

### 현재 규칙 (암묵적)

```
mobile_vla_[model]_[특수전략]_[데이터범위]_[날짜]
```

### 제안 규칙 (명시적)

```
mobile_vla_[model]_[data]_[chunk]_[strategy]_[날짜]

예시:
mobile_vla_kosmos2_leftright_nochunk_baseline_20251210
mobile_vla_kosmos2_leftright_nochunk_absaction_20251210
mobile_vla_kosmos2_rightonly_chunk_baseline_20251207
```

**장점**:
- 모든 변수가 명확히 드러남
- 조합 파악 용이
- 일관성 확보

---

## 9. 요약

### 변수 중요도

```
1. Action Chunking (B):  ████████████████████ (압도적)
2. Data Scope (A):       ███████ (중간)
3. Special Strategy (C): ██ (미미)
```

### 현재 진행률

- **수행 완료**: 5/16 (31.25%)
- **최고 성능**: Case 5 (0.000532)
- **의미 있는 조합**: 8/16 (No Chunk 계열)

### 핵심 인사이트

1. **No Chunk가 게임 체인저**: 50배 성능 향상
2. **Left+Right 데이터 필수**: 일반화 위해 필요
3. **특수 전략 불필요**: Baseline이 최고

### 추천 Next Step

```
현재 최고 조합 (Case 5) 로봇 실증
→ 성공 시: 배포
→ 방향 문제 발생 시: #7 (no_chunk + abs_action) 실험
```

---

**문서 작성**: 2025-12-10 01:55  
**총 가능 조합**: 16개  
**현재 진행**: 5개 (31.25%)  
**최적 조합**: A1 + B2 + C1 (Case 5)

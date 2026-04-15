# 정규화 해제 (Denormalization) 전략 문서

**작성일**: 2025-12-09  
**적용 파일**: `src/robovlms_mobile_vla_inference.py`

---

## 요약

모델 출력: `[-1.0, 1.0]` → 실제 로봇: `[-1.15, 1.15]` 변환

**권장 전략**: `safe` (Option C)

---

## 설정값

### 모델 출력 범위
```python
norm_min: float = -1.0
norm_max: float = 1.0
```

### 실제 로봇 속도 범위
```python
robot_max_linear_x: float = 1.15  # m/s
robot_max_linear_y: float = 1.15  # m/s
```

### 안전 속도 제한
```python
max_linear_x: float = 0.5  # m/s (safe 모드에서 사용)
max_linear_y: float = 0.5  # m/s
```

---

## 3가지 전략

### Option A: Scale (단순 스케일링)

```python
denormalize_strategy: str = "scale"
```

**공식**:
```
실제_속도 = 모델_출력 × robot_max
```

**예시**:
| 모델 출력 | 실제 속도 (robot_max=1.15) |
|:---:|:---:|
| -1.0 | -1.15 m/s |
| 0.0 | 0.0 m/s |
| +1.0 | +1.15 m/s |

**장점**: 단순, 선형 관계 유지  
**단점**: 최대 속도가 고정됨, 안전 제한 없음

---

### Option B: MinMax (RoboVLMs 방식)

```python
denormalize_strategy: str = "minmax"
```

**공식**:
```
실제_속도 = 0.5 × (모델_출력 + 1) × (max - min) + min
```

**예시**:
| 모델 출력 | 실제 속도 |
|:---:|:---:|
| -1.0 | 0.5×0×2.3 + (-1.15) = -1.15 m/s |
| 0.0 | 0.5×1×2.3 + (-1.15) = 0.0 m/s |
| +1.0 | 0.5×2×2.3 + (-1.15) = +1.15 m/s |

**장점**: RoboVLMs 원본과 호환  
**단점**: 비대칭 범위에서 유용, 현재는 scale과 동일 결과

---

### Option C: Safe (안전 모드) ⭐ 권장

```python
denormalize_strategy: str = "safe"  # 기본값
```

**공식**:
```
1. 클리핑: action = clip(action, -1, 1)
2. 스케일링: 실제_속도 = action × max_linear (안전 제한값)
```

**예시 (max_linear=0.5)**:
| 모델 출력 | 클리핑 후 | 실제 속도 |
|:---:|:---:|:---:|
| -1.5 | -1.0 | -0.5 m/s |
| -1.0 | -1.0 | -0.5 m/s |
| 0.0 | 0.0 | 0.0 m/s |
| +1.0 | +1.0 | +0.5 m/s |
| +1.5 | +1.0 | +0.5 m/s |

**장점**:
- ✅ 안전 보장 (이상치 클리핑)
- ✅ 조절 가능 (max_linear 파라미터)
- ✅ 점진적 속도 증가 가능

**사용 시나리오**:
1. 테스트 시작: `max_linear=0.3`
2. 안정 확인 후: `max_linear=0.5`
3. 최종: `max_linear=1.0` or `1.15`

---

## 사용법

### Config에서 설정

```python
config = MobileVLAConfig(
    # 전략 선택
    denormalize_strategy="safe",  # "scale", "minmax", "safe"
    
    # 실제 로봇 범위
    robot_max_linear_x=1.15,
    robot_max_linear_y=1.15,
    
    # safe 모드 안전 제한
    max_linear_x=0.5,
    max_linear_y=0.5
)
```

### 추론 시 사용

```python
# 모델 예측
actions, info = inference_engine.predict_action(images, instruction)

# 정규화 해제
real_actions = inference_engine.denormalize_action(actions)

# 또는 특정 전략 지정
real_actions = inference_engine.denormalize_action(actions, strategy="scale")
```

---

## 테스트 계획

### 단계별 속도 증가

```bash
# 1단계: 낮은 속도 테스트
max_linear_x=0.3, max_linear_y=0.3

# 2단계: 중간 속도
max_linear_x=0.5, max_linear_y=0.5

# 3단계: 높은 속도
max_linear_x=0.8, max_linear_y=0.8

# 4단계: 최대 속도
max_linear_x=1.15, max_linear_y=1.15
```

### 검증 체크리스트

- [ ] 모델 출력 -1.0 → 음수 방향 이동 확인
- [ ] 모델 출력 0.0 → 정지 확인
- [ ] 모델 출력 +1.0 → 양수 방향 이동 확인
- [ ] 속도가 max_linear를 초과하지 않음 확인
- [ ] 떨림/진동 없음 확인

---

## 권장 사항

1. **초기 테스트**: `safe` 전략, `max_linear=0.3`으로 시작
2. **안정 확인 후**: 점진적으로 속도 증가
3. **최종 배포**: `scale` 또는 `safe`에서 `max_linear=1.15`

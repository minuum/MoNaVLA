# Continuous Regression vs Discrete Classification 설계 분석

**작성일**: 2026-01-12 01:04  
**핵심 발견**: **데이터가 100% discrete!**

---

## 🎯 핵심 발견

### 실제 데이터 분포

```python
Linear X: 오직 2개 값만!
  - 0.00 m/s:  11.1% (정지)
  - 1.15 m/s:  88.9% (전진)
  
Linear Y: 오직 3개 값만!
  - -1.15 m/s: 16.7% (오른쪽)
  -  0.00 m/s: 38.9% (중립)
  - +1.15 m/s: 44.4% (왼쪽)

커버리지: 100%! ← 완벽히 discrete!
```

**결론**: 데이터가 완전히 discrete인데 continuous regression으로 학습 중!

---

## 💡 권장: Discrete Classification (6-class)

### Action Space

```python
Classes (2×3 = 6):
  0: [0.00, -1.15]  # Stop + Right
  1: [0.00,  0.00]  # Stop + Neutral
  2: [0.00, +1.15]  # Stop + Left
  3: [1.15, -1.15]  # Forward + Right ⭐
  4: [1.15,  0.00]  # Forward + Neutral ⭐
  5: [1.15, +1.15]  # Forward + Left ⭐
```

### 장점 ✅

1. **Perfect data alignment** - 100% discrete 데이터와 일치
2. **No post-processing** - 모델 출력 바로 사용
3. **Better loss** - Cross-entropy > MSE for discrete
4. **Clear interpretation** - 각 클래스 확률 확인 가능

---

## 📋 현재 모델 처리 방법

### 임시 해결책: Quantization

```python
def quantize_action(action):
    # Linear X
    linear_x = 0.0 if action[0] < 0.5 else 1.15
    
    # Linear Y
    if action[1] < -0.5:
        linear_y = -1.15
    elif action[1] > 0.5:
        linear_y = +1.15
    else:
        linear_y = 0.0
    
    return [linear_x, linear_y]
```

**현재 Model_LEFT/RIGHT**:
- Continuous로 학습됨
- Quantization으로 작동 가능 (임시)
- 하지만 최적은 아님

---

**다음 버전**: Discrete Classification 재설계 권장!

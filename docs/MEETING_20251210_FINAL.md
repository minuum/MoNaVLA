# 미팅 발표 자료 (2025-12-10 16:00) - FINAL

**발표 시간**: 25분  
**현재**: 15:06 (54분 남음)

---

## 1. Task 정의 (3분)

### Obstacle Avoidance Navigation with Turning Decision

**환경**:
- Robot → Box (장애물) → Bottle (목표)
- 모두 일직선 상에 고정

**Input**:
- Camera image (720x1280)
- Language: "Navigate around obstacles and reach... **on the left/right**"

**Output** (2 DOF):
- **linear_x**: 전진 속도 (forward velocity)
- **angular_z**: 회전 속도 (turning velocity)

**Goal**:
- 박스를 **왼쪽 또는 오른쪽으로 회피**하며
- Bottle 앞까지 도달

**핵심**:
- **"on the left"** → 왼쪽으로 회전 (angular_z > 0)
- **"on the right"** → 오른쪽으로 회전 (angular_z < 0)

---

## 2. 실험 설계 (2분)

### 변수
1. **Action Chunking**: fwd_pred_next_n
   - Chunk=1: 다음 1 step만 예측
   - Chunk=10: 다음 10 steps 예측 (RoboVLMs 기본값)

2. **Data**: 500 episodes (L+R) vs 250 (R only)

3. **Strategy**: Baseline vs Augmentation vs Absolute action

### 고정
- Model: Kosmos-2 (Frozen) + LoRA (r=32)
- Window: 8 frames
- Output: 2 DOF (linear_x, angular_z)

---

## 3. 핵심 발견 (10분) ⭐

### Finding 1: No Chunk 압도적 (98% 개선)

| Chunk | Val Loss | Train Loss | 비고 |
|:---:|---:|---:|:---|
| **1** | **0.000532** | ~0.0001 | Case 5 (Best) |
| 10 | 0.027 | 0.027 | Case 1 (Baseline) |

**개선**: 98% ⭐⭐⭐

**왜 Chunk=1이 좋은가?**
- ✅ **Reactive turning**: 실시간 회전 조정
- ✅ **Obstacle avoidance**: 박스와 거리 즉시 대응
- ✅ **Fine-grained control**: 미세한 각도 제어
- ✅ **Coupled action**: 전진+회전 동시 제어

**Chunk=10의 한계** (무조건 나쁜 건 아님):
- Mobile **manipulation**에는 유용 (물체 조작)
- 하지만 **navigation**은 환경 변화 빠름
- Obstacle 회피는 **즉각 반응** 필요

---

### Finding 2: Simple is Best

| Strategy | Val Loss | vs Baseline |
|:---|---:|---:|
| **Baseline** | **0.000532** | - |
| Abs | 0.00243 | 4.6x worse |
| Aug+Abs | 0.004 | 7.5x worse |

**결론**: Language instruction 충분히 informative

---

### Finding 3: Data Diversity

| Data | Episodes | Val Loss |
|:---|:---:|---:|
| **L+R** | 500 | **0.000532** |
| R only | 250 | 0.016 |

**개선**: 30x

---

## 4. Best Model (5분)

### Case 5: Champion 🏆

**설정**:
- Data: L+R 500 episodes
- Chunk: 1 (No Chunk)
- Strategy: Baseline
- Window: 8 frames
- Output: 2 DOF

**성능**:
- Val Loss: **0.000532**
- Train Loss: ~0.0001
- Epochs: 4

**Action 분포** (검증):
- Left: angular_z 평균 +0.805 ✅
- Right: angular_z 평균 -0.805 ✅

---

## 5. 기술적 세부사항 (3분)

### Model Architecture
- **VLM**: Kosmos-2 (Frozen, 1.3B params)
- **LoRA**: rank=32, alpha=16
- **Action Head**: LSTM Decoder (512 hidden)
- **Training**: FP16, AdamW, lr=1e-4

### 2 DOF Action Space
```
action = [linear_x, angular_z]
- linear_x ∈ [-1, 1]: 전진/후진
- angular_z ∈ [-1, 1]: 좌/우 회전
```

### Data Processing
- Images: 720x1280 → 224x224 resize
- Normalization: ImageNet stats
- Language: Tokenized (max 256 tokens)
- Window: 8 consecutive frames

---

## 6. 실용적 가치 (2분)

### Deployment Ready
- ✅ Best model identified (Case 5)
- ✅ Robust performance (Val Loss < 0.001)
- ✅ Efficient (LoRA fine-tuning)

### Design Guidelines
**Mobile Navigation VLA 설계 시**:
1. ✅ Use Chunk=1 for reactive control
2. ✅ Simple baseline over complex strategies
3. ✅ Diverse data (both turning directions)
4. ✅ Frozen VLM + LoRA for efficiency

### Research Contribution
- Novel finding: No chunk for navigation
- Empirical evidence: 98% improvement
- Practical guideline: Simplicity works

---

## 7. 결론 및 향후 계획 (2분)

### 핵심 메시지
**"Reactive control (Chunk=1)이 obstacle avoidance navigation의 핵심"**

### 향후 계획

**Short-term** (이번 주):
- Real robot deployment
- Edge case testing
- Performance monitoring

**Mid-term** (다음 주):
- 논문 작성 시작
- More environments
- Generalization 연구

**Long-term**:
- Multi-obstacle scenarios
- Dynamic obstacles
- Complex navigation tasks

---

## 핵심 요약 (3줄)

1. **No Chunk (Chunk=1)로 98% 성능 개선**
2. **Obstacle avoidance는 reactive control 필요**
3. **Simple baseline > Complex strategies**

---

**준비**: 완료 ✅  
**시간**: 25분 발표  
**자신감**: High

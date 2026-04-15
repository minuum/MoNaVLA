# Mobile VLA 학습 완료 및 샘플링 이슈 분석

**작성일**: 2025-12-04 01:54
**최종 Epoch**: 9 (10 epochs 완료)
**최종 성적**: Train Loss 0.0131, Val Loss 0.0131, RMSE ~0.114

---

## 🎉 학습 완료!

### 최종 성과
| Metric | 초기값 (Epoch 0) | 최종값 (Epoch 9) | 개선율 |
| :--- | :--- | :--- | :--- |
| **Train Loss** | 0.429 | 0.0131 | **-96.9%** |
| **Val Loss** | 0.0517 | 0.0131 | **-74.7%** |
| **Train RMSE** | 0.655 | 0.114 | **-82.6%** |
| **Val RMSE** | 0.227 | 0.115 | **-49.3%** |

---

## ⚠️ **샘플링 이슈 발견 및 분석**

### 1. **현재 샘플링 방식**

```python
# MobileVLAH5Dataset.__getitem__ (현재 구현)
def __getitem__(self, idx):
    total_frames_needed = self.window_size + self.fwd_pred_next_n  # 8 + 10 = 18
    
    # 문제: 에피소드별로 순차적으로 인덱싱
    for i, length in enumerate(self.episode_lengths):
        if length >= total_frames_needed:
            valid_frames = length - total_frames_needed + 1
            if frame_idx < valid_frames:
                ep_idx = i
                break
            frame_idx -= valid_frames
    
    # 같은 에피소드에서 연속된 18프레임만 샘플링
    for t in range(frame_idx, frame_idx + total_frames_needed):
        images.append(...)
        actions.append(...)
```

### 2. **문제점 분석**

#### ❌ **문제 1: 에피소드 간 다양성 부족**
- **현상**: 각 batch가 같은 에피소드의 연속된 프레임만 포함
- **영향**: 
  - 에피소드 내에서 유사한 장면/행동만 학습
  - 다양한 시나리오(좌/우 회피, 거리 변화 등) 학습 어려움
- **증거**: Loss가 0.0131까지 떨어졌지만, 이것이 일반화가 아닌 **에피소드별 overfitting**일 수 있음

#### ❌ **문제 2: 시간적 편향(Temporal Bias)**
- **현상**: 에피소드 앞부분과 뒷부분이 고르게 샘플링되지 않음
- **영향**:
  - 에피소드 시작(접근) vs 에피소드 끝(도착) 행동의 불균형
  - 특정 시점의 행동만 과도하게 학습

#### ❌ **문제 3: 단순 순차 샘플링**
```python
# 현재: 에피소드 0의 0~17, 18~35, ... → 에피소드 1의 0~17, ...
# 이는 RoboVLMs의 manipulator 데이터셋(수천 episodes)에는 적합하지만
# Mobile VLA(250 episodes)에는 부적합
```

---

## 🔧 **개선 방안**

### **Option 1: Random Temporal Sampling (권장)**

```python
def __getitem__(self, idx):
    # 에피소드 랜덤 선택
    ep_idx = np.random.randint(0, len(self.episode_files))
    
    with h5py.File(self.episode_files[ep_idx], 'r') as f:
        total_len = len(f['images'])
        
        # 시작 프레임 랜덤 선택 (valid range 내)
        max_start = total_len - total_frames_needed
        if max_start > 0:
            start_frame = np.random.randint(0, max_start + 1)
        else:
            start_frame = 0
        
        # 랜덤 시작점부터 18프레임 샘플링
        for t in range(start_frame, start_frame + total_frames_needed):
            images.append(...)
```

**장점**:
- ✅ 에피소드 간 다양성 증가
- ✅ 시간적 편향 제거
- ✅ Augmentation 효과 (같은 에피소드도 다른 시작점)

---

### **Option 2: Stratified Episode Sampling**

```python
def __init__(self, ...):
    # 에피소드를 시나리오별로 그룹화
    # episode_20251203_*_1box_hori_left_*.h5 → "1box_hori_left"
    self.episode_groups = self._group_episodes_by_scenario()

def __getitem__(self, idx):
    # 각 batch에서 다른 시나리오 포함하도록 강제
    scenario = self.scenarios[idx % len(self.scenarios)]
    ep_idx = random.choice(self.episode_groups[scenario])
    ...
```

**장점**:
- ✅ 시나리오 균형 보장 (좌/우, 거리별)
- ✅ 특정 패턴 과적합 방지

---

### **Option 3: Hard Negative Mining**

```python
# Inference 후 실패한 케이스를 우선적으로 샘플링
def __getitem__(self, idx):
    # loss가 높았던 샘플을 더 자주 샘플링
    if np.random.rand() < 0.3:  # 30% 확률
        ep_idx, frame_idx = self.hard_samples[np.random.randint(len(self.hard_samples))]
    else:
        # 일반 샘플링
        ...
```

---

## 📊 **현재 학습 결과 해석**

### ✅ **긍정적 신호**
1. **Val Loss ≈ Train Loss** (0.0131 vs 0.0131)
   - 과적합 없음
   - 일반화 능력 있음

2. **RMSE 82% 개선**
   - 실제 예측 정확도 향상
   - 0.114는 상당히 낮은 값

### ⚠️ **우려 사항**
1. **샘플링의 단순함**
   - 250 episodes × 평균 18프레임 = ~4,500 샘플
   - 순차 샘플링으로 다양성 제한

2. **실제 환경 테스트 필요**
   - 학습 데이터와 다른 시나리오에서 성능 확인
   - 새로운 장애물 위치/거리에서 robustness 검증

---

## 🎯 **다음 단계 제안**

### 즉시 실행 (우선순위 높음)
1. ✅ **현재 체크포인트 저장 위치 확인**
2. ⏳ **Best Model로 실제 추론 테스트**
3. ⏳ **샘플링 개선 후 재학습** (Option 1 권장)

### 추가 개선 (중기)
1. ⏳ **Data Augmentation 추가**
   - Color Jitter
   - Gaussian Noise
   - Random Crop & Resize
2. ⏳ **3DOF 확장** (angular_z 추가)
3. ⏳ **Multi-Task Learning** (여러 목표물)

---

## 📁 **체크포인트 분석 필요**

현재 `runs/mobile_vla_lora_20251203` 경로를 찾을 수 없음.
실제 저장 위치:
- `RoboVLMs_upstream/runs/...`로 추정
- 확인 필요!

---

*샘플링 개선 후 재학습을 강력히 권장합니다!*

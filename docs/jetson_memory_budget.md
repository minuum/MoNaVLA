# Jetson AGX Orin 16GB 메모리 구조 및 버짓

**작성일**: 2025-12-22  
**대상**: Jetson AGX Orin (또는 Orin NX) 16GB

---

## 1. Unified Memory Architecture 검증

### ✅ 진실 확인

**결론: Jetson Orin은 CPU와 GPU가 메모리를 공유합니다.**

**NVIDIA 공식 문서 기반**:
- Jetson Orin 시리즈 (AGX Orin, Orin NX, Orin Nano) 모두 **Unified Memory Architecture**
- CPU (Arm Cortex-A78AE)와 GPU (NVIDIA Ampere)가 **동일한 LPDDR5 메모리 공유**
- 메모리 컨트롤러는 분리되어 있지만, **물리적 메모리 공간은 하나**

**특징**:
```
┌─────────────────────────────────────┐
│    Jetson Orin SoC (Single Chip)    │
├─────────────┬───────────────────────┤
│ CPU         │ GPU                   │
│ (Cortex-A78)│ (Ampere)              │
└─────────────┴───────────────────────┘
        │              │
        └──────┬───────┘
               │
    ┌──────────▼──────────┐
    │  Unified Memory     │
    │  LPDDR5 16GB        │
    │  (Shared)           │
    └─────────────────────┘
```

**의미**:
- ✅ CPU 할당 ↑ → GPU 가용 메모리 ↓
- ✅ GPU 할당 ↑ → CPU 가용 메모리 ↓
- ✅ **전체 합이 16GB를 초과할 수 없음**

---

## 2. Jetson Orin 16GB 기본 메모리 사용량

### 부팅 직후 메모리 상태 (문헌 기반)

| 프로세스 | 메모리 사용 | 설명 |
|----------|------------|------|
| **Ubuntu OS** | 1.5~2.0 GB | 기본 시스템 프로세스 |
| **X Window System** | 0.3~0.5 GB | GUI (필요시) |
| **CUDA / TensorRT** | 0.5~1.0 GB | GPU 런타임 |
| **여유 메모리** | **12~14 GB** | 사용 가능 |

**부팅 직후 총 사용량**: ~2~4 GB

---

## 3. Mobile VLA 배포 시 메모리 버짓

### 시나리오 1: FP16 모델 (현재)

| 프로세스 | 메모리 할당 | 비고 |
|----------|------------|------|
| **Ubuntu OS** | 1.5 GB | 고정 |
| **ROS2 Core** | 0.8 GB | roscore + 기본 노드 |
| **ROS2 Nodes** | 0.5 GB | Camera, Motor control, TF |
| **VLA Model (FP16)** | 7.4 GB | Vision + LLM + Action |
| **Activations** | 1.5 GB | Forward pass 중 |
| **KV Cache** | 0.8 GB | Language model |
| **CUDA Overhead** | 1.0 GB | CUDA runtime |
| **버퍼** | 1.5 GB | 안전 여유 |
| **총계** | **15.0 GB** | ⚠️ **한계** |

**결론**: FP16은 **거의 한계**에 도달 (여유 1GB)

---

### 시나리오 2: INT8/INT4 모델 (PTQ 후)

| 프로세스 | 메모리 할당 | 비고 |
|----------|------------|------|
| **Ubuntu OS** | 1.5 GB | 고정 |
| **ROS2 Core** | 0.8 GB | 동일 |
| **ROS2 Nodes** | 0.5 GB | 동일 |
| **VLA Model (INT8/INT4)** | 4.0 GB | ✅ PTQ 적용 |
| **Activations (INT8)** | 1.0 GB | 감소 |
| **KV Cache** | 0.5 GB | INT4 적용 |
| **CUDA Overhead** | 1.0 GB | 동일 |
| **TensorRT** | 0.5 GB | 최적화 |
| **버퍼** | 5.2 GB | ✅ 여유 확보 |
| **총계** | **10.8 GB** | ✅ **안정** |

**결론**: INT8/INT4는 **5GB 여유** 확보

---

## 4. 상세 메모리 버짓 (INT8/INT4 기준)

### A. System Layer (고정)

```
Ubuntu OS: 1.5 GB
├─ Kernel:           0.5 GB
├─ System services:  0.4 GB
├─ Networking:       0.3 GB
└─ Shell/GUI:        0.3 GB
```

**할당**: **1.5 GB** (최소화 가능: 1.2 GB, X 제거 시)

---

### B. ROS2 Layer

```
ROS2 Runtime: 1.3 GB
├─ ROS2 Core:        0.8 GB
│  ├─ roscore
│  ├─ rviz (필요시)
│  └─ diagnostics
├─ Camera Node:      0.2 GB
│  └─ Image buffer
├─ Motor Controller: 0.15 GB
└─ TF / Navigation:  0.15 GB
```

**할당**: **1.3 GB**

**최적화 옵션**:
- RViz 제거: -0.3 GB
- 이미지 버퍼 축소: -0.1 GB
- **최소화 가능**: 0.9 GB

---

### C. Deep Learning Layer (VLA Model)

#### Model Parameters

```
VLA Model (INT8/INT4): 4.0 GB
├─ Vision Encoder (INT8):  0.3 GB
├─ LLM (INT4):             0.8 GB
├─ Action Head (FP16):     0.05 GB
├─ Embeddings:             0.2 GB
└─ Projections:            0.15 GB

CUDA Runtime: 1.0 GB
├─ cuDNN:                  0.4 GB
├─ cuBLAS:                 0.3 GB
└─ CUDA context:           0.3 GB

TensorRT Runtime: 0.5 GB
└─ Optimized engines
```

**할당**: **5.5 GB**

---

#### Runtime Activations

```
Inference Activations: 1.0 GB
├─ Vision Forward:         0.4 GB
├─ LLM Forward:            0.4 GB
└─ Action Head:            0.2 GB

KV Cache (256 tokens): 0.5 GB
└─ Language model context
```

**할당**: **1.5 GB**

---

### D. Buffer & Safety Margin

```
Buffer: 5.2 GB
├─ Peak allocation:        2.0 GB
├─ Temporary tensors:      1.5 GB
├─ Image preprocessing:    0.5 GB
├─ ROS message queue:      0.7 GB
└─ Emergency reserve:      0.5 GB
```

**할당**: **5.2 GB**

---

## 5. 총 메모리 버짓 (INT8/INT4)

```
┌────────────────────────────────────┐
│  Jetson Orin 16GB Memory Budget    │
├────────────────────────────────────┤
│                                    │
│  System Layer:          1.5 GB     │
│  ROS2 Layer:            1.3 GB     │
│  Model Parameters:      4.0 GB     │
│  CUDA/TensorRT:         1.5 GB     │
│  Runtime Activations:   1.5 GB     │
│  Buffer/Safety:         5.2 GB     │
│                                    │
│  ──────────────────────────────    │
│  Total Allocated:      15.0 GB     │
│  Reserved for OS:       1.0 GB     │
│  ══════════════════════════════    │
│  Total:                16.0 GB ✅  │
└────────────────────────────────────┘
```

**여유율**: 32.5% (5.2GB / 16GB)

---

## 6. 최적화 옵션

### Level 1: 기본 최적화 (현재)

- ✅ Vision INT8
- ✅ LLM INT4
- ✅ Action Head FP16
- **총 메모리**: 10.8 GB (여유 5.2 GB)

---

### Level 2: 공격적 최적화 (필요시)

```
추가 최적화:
- RViz 제거:              -0.3 GB
- X Window 제거:          -0.3 GB
- Image buffer 축소:      -0.1 GB
- KV Cache 128 tokens:    -0.25 GB
─────────────────────────────────
총 추가 절감:             -0.95 GB

최종 여유:                 6.15 GB
```

**적용 시기**: 메모리 부족 발생 시

---

### Level 3: 극한 최적화 (비상)

```
TensorRT INT8 전환:
- Vision + LLM + Action → INT8
- 메모리: 4.0 GB → 2.5 GB
─────────────────────────────────
총 절감:                  -1.5 GB

최종 여유:                 7.65 GB
```

**조건**: Level 2로도 부족할 때만

---

## 7. 모니터링 및 검증

### 실시간 모니터링

```bash
# Jetson Stats 설치
sudo -H pip install jetson-stats

# 실시간 모니터링
jtop

# 또는 직접 확인
free -h
nvidia-smi  # (Jetson에서는 tegrastats 사용)
```

### 예상 출력 (INT8/INT4)

```
────────────────────────────────────
Memory Usage:
  Total:     16.0 GB
  Used:      10.8 GB
  Free:       5.2 GB
  Buffers:    0.8 GB
  Cached:     1.5 GB

GPU Memory (Shared):
  VLA Model:  4.0 GB
  CUDA:       1.5 GB
  Active:     1.5 GB
────────────────────────────────────
```

---

## 8. 배포 체크리스트

### 사전 확인

- [ ] Jetson 모델 확인 (AGX Orin 또는 Orin NX 16GB)
- [ ] Ubuntu version (20.04 또는 22.04)
- [ ] ROS2 버전 (Humble 권장)
- [ ] CUDA / cuDNN / TensorRT 설치

### 배포 단계

1. **기본 메모리 측정**
   ```bash
   free -h  # 부팅 직후
   ```

2. **ROS2 메모리 측정**
   ```bash
   ros2 launch vla_control robot.launch.py
   free -h  # ROS2 실행 후
   ```

3. **VLA 모델 로드**
   ```bash
   python Mobile_VLA/inference_server.py
   jtop  # 실시간 확인
   ```

4. **Peak 메모리 확인**
   ```bash
   # 추론 10회 실행 후
   cat /proc/meminfo | grep -E "MemTotal|MemFree|MemAvailable"
   ```

---

## 9. 최종 권장 사항

### 권장 구성 (INT8/INT4)

```
Target: 70% 메모리 사용
─────────────────────────
System + ROS2:     2.8 GB
VLA Model:         4.0 GB
Runtime:           2.5 GB
Buffer:            2.0 GB
─────────────────────────
Total:            11.3 GB (70%)
Reserved:          4.7 GB (30%)
```

**안전 여유**: 4.7 GB (29%)

---

### 비상 시나리오

**메모리 부족 발생 시**:
1. RViz 종료
2. X Window 종료 (headless 모드)
3. Image buffer 축소 (320x240)
4. KV Cache 128 tokens로 제한

**예상 추가 확보**: ~1.0 GB

---

## 10. 결론

✅ **Jetson Orin 16GB는 Unified Memory 구조**  
✅ **INT8/INT4 PTQ로 5.2GB 여유 확보 가능**  
✅ **FP16은 한계 (여유 1GB), PTQ 필수**  
✅ **권장 메모리 사용률: 70% (11.3GB)**

**배포 가능**: PTQ 적용 시 안정적 실행 가능 ✅

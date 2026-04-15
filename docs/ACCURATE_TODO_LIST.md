# 남은 TODO 리스트 - 환각 없는 정확한 분석

**작성일**: 2025-12-04 07:36
**목적**: 실제로 남은 작업만 정확히 파악하고 우선순위 설정

---

## ✅ **이미 완료된 작업 (정확히 파악)**

### **1. RoboVLMs validation** ✅
- Context vector analysis ✅
- Sampling test ✅
- Original model analysis ✅

### **2. Mobile-VLA 초기 학습** ✅
- Box learning verification ✅ (Sim 0.54)
- Feasibility report ✅
- 첫 학습 완료 ✅ (Epoch 9, Loss 0.013)

### **3. 7DOF → 2DOF 변환 분석** ✅
- 문서 작성 완료: `docs/7dof_to_2dof_conversion/FEASIBILITY_ANALYSIS.md`
- VLM pretrain 불일치 분석 완료
- 데이터 요구량 분석 완료

### **4. Mobile vs Manipulator 연구** ✅
- 문서 작성 완료: `docs/Mobile_vs_Manipulator_Research/FEASIBILITY_ANALYSIS.md`
- 기존 연구 비교 완료
- 실현 가능성 분석 완료

### **5. Inference Scenario** ✅
- 설계 완료: `docs/Inference_Scenario/INFERENCE_DESIGN.md`
- 0.4초 간격, action chunk 방식
- ROS 노드 코드 준비 완료

### **6. Data Augmentation 전략** ✅
- 문서 작성 완료: `docs/Mobile-VLA/DATA_AUGMENTATION_STRATEGY.md`
- Simulation 증강 계획 완료
- Image augmentation 방안 완료

---

## 🔄 **실제로 진행 중인 작업**

### **1. RoboVLMs Frozen+LoRA 학습** ⏳
```bash
# 방금 시작
Config: mobile_vla_robovlms_frozen_lora_20251204.json
목적: Robot pretrain VLM vs 일반 VLM 비교
예상 시간: ~25분
```

---

## ⏳ **실제로 남은 TODO (환각 없이)**

### **Priority 1: Inference 구현 및 테스트** 🔥

#### **1-1. Latency 측정 스크립트 작성**
```python
# 파일: test_inference_latency.py
# 목적: Best checkpoint의 실제 추론 속도 측정
# 측정 항목:
#   - VLM forward time
#   - Action Head forward time
#   - Total inference time
# 목표: < 200ms
```

**현재 상태**: 스크립트 없음, 작성 필요 ❌

---

#### **1-2. Velocity 출력 검증**
```python
# 파일: verify_velocity_output.py
# 목적: 예측된 velocity가 합리적인지 검증
# 측정 항목:
#   - Predicted vs Ground Truth
#   - Mean, Std, Range
#   - Sample outputs
```

**현재 상태**: 스크립트 없음, 작성 필요 ❌

---

#### **1-3. ROS 노드 구현**
```python
# 파일: ROS_action/src/vla_inference/vla_inference/vla_node.py
# 현재 상태: 뼈대만 있음
# 필요 작업:
#   - Checkpoint 로딩 코드
#   - Image callback 구현
#   - Inference loop 구현
#   - cmd_vel publishing
```

**현재 상태**: 일부 코드 있음, 완성 필요 ⏳

---

### **Priority 2: 샘플링 개선 재학습** (선택)

#### **현재 상황**
```
✅ Random temporal sampling 구현됨
❌ 재학습 안 함

이유: 우리 태스크는 단일 시나리오라 다양성 제한적
→ 샘플링 개선 효과가 크지 않을 수 있음
```

**결정 필요**: 재학습할 가치가 있는가?
- 데이터 250 episodes, 모두 비슷한 시나리오
- 박스 위치만 약간 다름
- → **우선순위 낮음** ⏬

---

### **Priority 3: Data Augmentation** (선택)

#### **Option A: Image Augmentation** (빠름)
```python
# 현재: 구현 안 됨
# 필요: 코드 작성
# 예상 시간: ~1시간
```

#### **Option B: Simulation** (느림)
```python
# 현재: 설계만 됨
# 필요: Gazebo/PyBullet 환경 구축
# 예상 시간: ~2주
```

**결정 필요**: 할 것인가?
- 현재 Loss 0.013은 이미 좋음
- 실제 로봇 테스트 먼저 해보는게 나음
- → **우선순위 낮음** ⏬

---

## 🎯 **실제로 즉시 실행 가능한 항목**

### **1. Inference Latency 측정** 🔥🔥🔥
```bash
# 필요: test_inference_latency.py 작성
# 시간: ~30분
# 중요도: 높음 (실제 사용 가능성 확인)
```

### **2. Velocity 검증** 🔥🔥🔥
```bash
# 필요: verify_velocity_output.py 작성
# 시간: ~30분
# 중요도: 높음 (출력 정확성 확인)
```

### **3. ROS 노드 완성** 🔥🔥
```bash
# 필요: vla_node.py 구현
# 시간: ~1-2시간
# 중요도: 중간 (실제 로봇 테스트용)
```

### **4. RoboVLMs 학습 모니터링** 🔥
```bash
# 현재: 백그라운드 진행 중
# 필요: 결과 확인 (25분 후)
```

---

## 📊 **실제 실행 계획**

### **Step 1: Inference 스크립트 작성 (즉시)** 
```bash
1. test_inference_latency.py 작성 (30분)
2. verify_velocity_output.py 작성 (30분)
3. 두 스크립트 실행 (10분)
```

### **Step 2: RoboVLMs 학습 결과 확인 (25분 후)**
```bash
1. Loss 비교 (Kosmos-2 vs RoboVLMs)
2. 성능 차이 분석
```

### **Step 3: ROS 노드 완성 (선택, 2시간)**
```bash
1. vla_node.py 구현
2. 로컬 테스트
3. 실제 로봇 연동 (하드웨어 필요)
```

---

## ❌ **하지 않을 것 (환각 제거)**

### **1. 샘플링 개선 재학습** ❌
- 이유: 태스크 단순, 데이터 한정적
- 효과: 미미할 것으로 예상

### **2. Simulation 데이터 증강** ❌
- 이유: 시간 오래 걸림 (2주)
- 필요성: 현재 Loss 0.013으로 충분

### **3. Image Augmentation** ❌
- 이유: 이미 좋은 성능
- 우선순위: 낮음

---

## 📝 **정확한 TODO 리스트**

| 순위 | 작업 | 파일 | 시간 | 상태 |
| :---: | :--- | :--- | :---: | :---: |
| **1** | Latency 측정 | `test_inference_latency.py` | 30분 | ❌ 작성 필요 |
| **2** | Velocity 검증 | `verify_velocity_output.py` | 30분 | ❌ 작성 필요 |
| **3** | RoboVLMs 결과 | - | 25분 | ⏳ 진행 중 |
| **4** | ROS 노드 | `vla_node.py` | 2시간 | ⏸️ 선택 |

---

## 🎯 **다음 액션**

### **즉시 실행 (병렬)**
1. ✅ RoboVLMs 학습 (백그라운드, 진행 중)
2. ⏳ Latency 측정 스크립트 작성
3. ⏳ Velocity 검증 스크립트 작성

### **25분 후**
1. RoboVLMs 학습 결과 확인
2. Inference 스크립트 실행

---

*환각 없이 실제로 해야 할 것만 정리했습니다!*

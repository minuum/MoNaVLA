# Mobile-VLA 모델 버전 및 테스트 계획

**작성일**: 2025-12-04 02:33
**목적**: RoboVLMs 원본 vs LoRA 파인튜닝 버전 비교 테스트 계획

---

## 📦 **사용 가능한 모델 버전**

### **1. 원본 모델 (HuggingFace)**

| Model | 출처 | 설명 | 경로 | 상태 |
| :--- | :--- | :--- | :--- | :---: |
| **Microsoft Kosmos-2** | HF: `microsoft/kosmos-2-patch14-224` | 일반 VLM (COCO, Flickr 학습) | `.vlms/kosmos-2-patch14-224/` | ✅ 다운로드됨 |
| **RoboVLMs** | HF: `robovlms/RoboVLMs` | Robot VLM (Manipulator 학습) | 미다운로드 | ❌ 필요 |

---

### **2. 우리가 학습한 LoRA 파인튜닝 버전**

| 실험명 | 날짜 | Epochs | Best Val Loss | Checkpoint 경로 | 비고 |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **mobile_vla_lora_20251106** | 2025-11-12 | 20 | ? | `runs/.../20251106/` | 초기 실험 |
| **mobile_vla_lora_20251114** | 2025-11-20 | 10 | 0.280 | `runs/.../20251114/epoch_epoch=05-val_loss=0.280.ckpt` | 중간 실험 |
| **mobile_vla_lora_20251203** ⭐ | 2025-12-03 | 10 | **0.013** | `runs/.../20251203/epoch_epoch=09-val_loss=0.013.ckpt` | **Best!** |

---

## 🧪 **테스트 계획 매트릭스**

### **Phase 1: 모델 비교 (VLM Backbone)**

| Test ID | VLM Backbone | Action Head | 학습 데이터 | 목적 | 예상 결과 | 우선순위 |
| :---: | :--- | :--- | :---: | :--- | :--- | :---: |
| **T1-1** | Microsoft Kosmos-2 (Frozen) | 랜덤 초기화 → 학습 | 250 eps | Baseline (현재) | Loss 0.013 | ✅ 완료 |
| **T1-2** | RoboVLMs (Frozen) | 랜덤 초기화 → 학습 | 250 eps | Robot VLM 효과 | Loss < 0.013? | 🔥 High |
| **T1-3** | Kosmos-2 (파인튜닝) | 함께 학습 | 250 eps | VLM 파인튜닝 필요성 | Overfitting? | ⏳ Low |
| **T1-4** | RoboVLMs (파인튜닝) | 함께 학습 | 250 eps | VLM+Action 동시 학습 | Overfitting? | ⏳ Low |

---

### **Phase 2: LoRA 파인튜닝 버전 비교**

| Test ID | 체크포인트 | Val Loss | Test 내용 | 측정 지표 | 우선순위 |
| :---: | :--- | :---: | :--- | :--- | :---: |
| **T2-1** | 20251203 Epoch 09 ⭐ | 0.013 | 실제 로봇 추론 | 성공률, Latency | 🔥 High |
| **T2-2** | 20251203 Epoch 07 | 0.014 | 조기 체크포인트 | 성능 차이 | ⏳ Medium |
| **T2-3** | 20251114 Epoch 05 | 0.280 | 이전 버전 비교 | 데이터 차이 효과 | ⏳ Low |

---

### **Phase 3: 추론 성능 테스트**

| Test ID | 모델 | 테스트 내용 | 측정 항목 | 목표 | 우선순위 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **T3-1** | Best (20251203-E09) | Latency 측정 | VLM time, Action Head time, Total | < 200ms | 🔥 High |
| **T3-2** | Best (20251203-E09) | 실제 로봇 주행 | 성공률, 주행 시간, 경로 | > 80% | 🔥 High |
| **T3-3** | Best (20251203-E09) | Velocity 값 검증 | Predicted vs Ground Truth | RMSE < 0.12 | 🔥 High |
| **T3-4** | Kosmos vs RoboVLMs | 비교 추론 | 성능 차이 | - | ⏳ Medium |

---

### **Phase 4: 데이터 증강 효과**

| Test ID | 데이터 | 모델 | 학습 | 예상 효과 | 우선순위 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **T4-1** | 250 (Real) | Kosmos-2 Frozen | ✅ 완료 | Baseline (0.013) | ✅ 완료 |
| **T4-2** | 1,500 (Real + Aug) | Kosmos-2 Frozen | 재학습 | Loss < 0.010 | ⏳ Medium |
| **T4-3** | 5,000 (Sim) | Kosmos-2 Frozen | 재학습 | Sim2Real gap | ⏳ Low |
| **T4-4** | 5,000 (Sim+Real mix) | Kosmos-2 Frozen | 재학습 | Best generalization | ⏳ Medium |

---

## 🎯 **즉시 실행 항목 (우선순위 순)**

### **Priority 1: 원본 RoboVLMs 다운로드 및 학습** 🔥
```bash
# 1. RoboVLMs 다운로드
huggingface-cli download robovlms/RoboVLMs \
  --cache-dir .vlms/ \
  --local-dir .vlms/RoboVLMs

# 2. Config 생성 (RoboVLMs 버전)
cp Mobile_VLA/configs/mobile_vla_20251203_lora.json \
   Mobile_VLA/configs/mobile_vla_robovlms_20251204.json

# 3. model_path 수정
# "model_path": ".vlms/RoboVLMs"

# 4. 학습
./train_robovlms_version.sh
```

**예상 시간**: 다운로드 1시간 + 학습 25분

---

### **Priority 2: Best Checkpoint 실제 추론 테스트** 🔥
```bash
# Test T3-1: Latency
python test_inference_latency.py \
  --checkpoint RoboVLMs_upstream/runs/.../epoch_09-val_loss=0.013.ckpt

# Test T3-2: 실제 로봇
roslaunch vla_inference vla_inference.launch \
  checkpoint_path:=.../epoch_09-val_loss=0.013.ckpt

# Test T3-3: Velocity 검증
python verify_velocity_output.py \
  --checkpoint .../epoch_09-val_loss=0.013.ckpt \
  --test_data ROS_action/mobile_vla_dataset/
```

**예상 시간**: 각 30분

---

### **Priority 3: Kosmos-2 vs RoboVLMs 비교**
```bash
# Test T1-1 (완료) vs Test T1-2 (필요)
# 성능 차이 = Robot pretrain 효과

# 비교 항목:
# - Loss 수렴 속도
# - 최종 Loss
# - 실제 추론 성공률
```

**예상 시간**: 학습 25분 + 비교 분석 1시간

---

## 📊 **예상 결과 및 가설**

| 가설 | 예상 결과 | 검증 방법 |
| :--- | :--- | :--- |
| **H1**: RoboVLMs가 Kosmos-2보다 좋음 | RoboVLMs Loss < 0.013 | Test T1-2 |
| **H2**: LoRA 파인튜닝 충분 (VLM 고정) | Val Loss 낮음, Overfitting 없음 | Test T1-1 (완료) |
| **H3**: 데이터 증강 효과 있음 | Aug Loss < 0.010 | Test T4-2 |
| **H4**: 추론 Latency 충분 | Total < 200ms | Test T3-1 |
| **H5**: 실제 로봇 작동 가능 | 성공률 > 80% | Test T3-2 |

---

## 📁 **체크포인트 경로 정리**

### **Best Checkpoints (LoRA 파인튜닝)**
```
1. Epoch 09 (Best) ⭐⭐⭐⭐⭐
   RoboVLMs_upstream/runs/mobile_vla_lora_20251203/kosmos/mobile_vla_finetune/2025-12-03/mobile_vla_lora_20251203/epoch_epoch=09-val_loss=val_loss=0.013.ckpt
   Size: 6.9GB
   Val Loss: 0.013

2. Epoch 08 (Backup)
   .../epoch_epoch=08-val_loss=val_loss=0.014.ckpt
   Size: 6.9GB
   Val Loss: 0.014

3. Last (최신)
   .../last.ckpt
   Size: 6.9GB
```

---

## 🚀 **실행 순서 (추천)**

### **Day 1 (즉시)**
1. ✅ **Test T3-1**: Latency 측정 (30분)
2. ✅ **Test T3-3**: Velocity 검증 (30분)
3. ⏳ **RoboVLMs 다운로드** (백그라운드, 1시간)

### **Day 2**
1. ⏳ **Test T1-2**: RoboVLMs 학습 (25분)
2. ⏳ **Test T3-4**: Kosmos vs RoboVLMs 비교 (1시간)
3. ⏳ **Test T3-2**: 실제 로봇 테스트 (2시간)

### **Day 3 (선택)**
1. ⏳ **Test T4-2**: Image augmentation 학습 (1일)
2. ⏳ **Test T2-2, T2-3**: 다른 체크포인트 검증 (2시간)

---

## 📝 **다음 단계**

어떤 테스트부터 시작하시겠습니까?

**A. RoboVLMs 다운로드 및 학습** (T1-2, 가장 중요)
**B. Best Checkpoint 추론 테스트** (T3-1, T3-3, 빠른 검증)
**C. 실제 로봇 테스트** (T3-2, 최종 검증)

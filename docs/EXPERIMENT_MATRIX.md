# Mobile-VLA 전체 실험 케이스 매트릭스

## 🎯 실험 목표
1. **HuggingFace RoboVLMs** 원본 모델 활용
2. **Mobile-VLA** 구현 (RoboVLMs 기반)
3. **LoRA FT vs Frozen** 비교
4. **left, right, left+right** 데이터 효과 분석

---

## 📊 전체 실험 케이스 매트릭스

| Case# | VLM Init | VLM Status | Data | Episodes | 목적 | 상태 |
| :---: | :--- | :--- | :--- | :---: | :--- | :---: |
| **1** | MS Kosmos-2 | Frozen+LoRA | left only | 250 | Baseline | ✅ 완료 (Loss 0.013) |
| **2** | RoboVLMs | Frozen+LoRA | left only | 250 | Robot VLM 효과 | ⏳ 진행중 |
| **3** | MS Kosmos-2 | Frozen+LoRA | left+right | 500 | 균형 데이터 | ❌ 예정 |
| **4** | RoboVLMs | Frozen+LoRA | left+right | 500 | Robot+균형 | ❌ 예정 |
| **5** | MS Kosmos-2 | Full FT | left+right | 500 | VLM 파인튜닝 | ❌ 예정 (선택) |
| **6** | RoboVLMs | Full FT | left+right | 500 | Robot+Full FT | ❌ 예정 (선택) |

### 추가 분석 케이스
| Case# | Data | 목적 | 우선순위 |
| :---: | :--- | :--- | :---: |
| **7** | left only (250) | Left 전용 성능 | ✅ 완료 |
| **8** | right only (250) | Right 전용 성능 | ⏳ 필요 |
| **9** | left+right (250+250) | 균형 효과 | 🔥 High |

---

## 🔥 즉시 실행 순서

### **Step 1: 데이터 확인** ✅
```bash
총 Episodes: TBD
Left: TBD
Right: TBD
균형: Check!
```

### **Step 2: Case 2 확인** (RoboVLMs Frozen, left only)
```bash
# 현재 학습 상태 확인
# 완료/진행중 여부 파악
```

### **Step 3: Case 3 준비** (Kosmos-2 Frozen, left+right)
```json
{
  "exp_name": "mobile_vla_kosmos2_frozen_lora_leftright_20251204",
  "train_dataset": {
    "data_dir": "ROS_action/mobile_vla_dataset",
    "episode_pattern": "episode_20251*.h5"  // left+right 모두
  }
}
```

### **Step 4: Case 4 준비** (RoboVLMs Frozen, left+right)
```json
{
  "exp_name": "mobile_vla_robovlms_frozen_lora_leftright_20251204",
  "model_load_path": "RoboVLMs checkpoint",
  "train_dataset": {
    "episode_pattern": "episode_20251*.h5"  // left+right 모두
  }
}
```

### **Step 5: Context Vector 검증**
```bash
# Kosmos-2 vs RoboVLMs context 비교
python3 verify_context_vector.py
```

---

## 📋 비교 분석 계획

### **비교 1: VLM Pretrain 효과** (Case 1 vs Case 2)
```
변수: VLM (Kosmos-2 vs RoboVLMs)
고정: Data (left only 250), Training (Frozen+LoRA)

기대:
- RoboVLMs가 더 좋을까? (Robot pretrain)
- 아니면 차이 없을까? (Mobile ≠ Manipulator)
```

### **비교 2: 데이터 균형 효과** (Case 1 vs Case 3)
```
변수: Data (left only vs left+right)
고정: VLM (Kosmos-2), Training (Frozen+LoRA)

기대:
- left+right가 일반화 좋을 것
- left/right 개별 성능은 비슷할 것
```

### **비교 3: Robot VLM + 균형** (Case 1 vs Case 4)
```
변수: VLM + Data
고정: Training (Frozen+LoRA)

기대:
- 최고 성능 (Robot pretrain + 균형)
```

### **비교 4: Full FT vs Frozen** (Case 3 vs Case 5, 선택)
```
변수: Training (Frozen+LoRA vs Full FT)
고정: VLM (Kosmos-2), Data (left+right)

기대:
- Frozen이 나을 것 (데이터 부족)
- Full FT는 Overfitting 위험
```

---

## 🚀 실행 계획

### **오늘 (우선순위 High)**
1. ✅ 데이터 확인 (left+right 균형)
2. ⏳ Case 2 결과 확인
3. ⏳ Context vector 검증 완료
4. 🔥 Case 3 준비 및 학습 시작

### **내일**
1. Case 3 결과 분석
2. Case 4 학습
3. 비교 분석 시작

### **선택 (추가)**
1. Case 5, 6 (Full FT)
2. Left/Right 개별 분석

---

## 📊 예상 결과표

| Case | VLM | Data | Val Loss (예상) | 비고 |
| :---: | :--- | :--- | :---: | :--- |
| 1 | Kosmos-2 | left | **0.013** | ✅ 완료 |
| 2 | RoboVLMs | left | ~0.012? | Robot pretrain 효과? |
| 3 | Kosmos-2 | left+right | ~0.015 | 균형 데이터 |
| 4 | RoboVLMs | left+right | ~0.013? | **Best 예상** |

---

*전체 실험 매트릭스 완성 및 실행 준비 완료!*

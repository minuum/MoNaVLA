# 전체 실험 케이스 최종 계획 및 결과

**작성 날짜**: 2025-12-04  
**프로젝트**: Mobile-VLA  
**코드베이스**: `/home/billy/25-1kp/vla/`

---

## 📊 전체 실험 매트릭스

| Case | VLM | Data | Episodes | Status | Val Loss | 날짜 |
|:---:|:---|:---|:---:|:---:|:---:|:---:|
| **1** | Kosmos-2 | left only | 250 | ✅ 완료 | **0.013** | 2025-12-03 |
| **2** | Kosmos-2 | right only | 250 | ⏳ 진행중 | ??? | 2025-12-04 |
| **3** | Kosmos-2 | left+right | 500 | ✅ 완료 | **0.027** | 2025-12-04 |

---

## 🎯 실험 목적

### **Case 1 vs Case 2**: 방향별 성능 비교
- 목적: Left와 Right가 동일한 난이도인지 확인
- 예상: 비슷한 Loss (~0.013)
- 실제: Case 1 = 0.013, Case 2 = ???

### **Case 1 vs Case 3**: 데이터 균형 효과
- 목적: 균형 데이터의 일반화 성능
- 예상: Case 3가 약간 높지만 일반화 우수
- 실제: Case 1 = 0.013, Case 3 = 0.027 (2배, 하지만 양방향 가능)

### **Case 2 vs Case 3**: Right 데이터 효과
- 목적: Right 데이터 추가의 효과
- Case 2 (right only) vs Case 3 (left+right)

---

## ✅ 완료된 실험

### **Case 1: Left Only** (2025-12-03)
```
VLM: Kosmos-2 (Frozen + LoRA)
Data: 250 left episodes
Val Loss: 0.013 (Epoch 9)
Train RMSE: 0.114
```
**Checkpoint**: `...epoch_09-val_loss=0.013.ckpt`

### **Case 3: Left+Right** (2025-12-04)
```
VLM: Kosmos-2 (Frozen + LoRA)
Data: 500 episodes (250 left + 250 right)
Best Val Loss: 0.027 (Epoch 8)
Final Val Loss: 0.036 (Epoch 9)
Train RMSE: 0.111
Val RMSE: 0.170
```
**Checkpoint**: `...epoch_08-val_loss=0.027.ckpt`

---

## ⏳ 진행 중

### **Case 2: Right Only** (2025-12-04 시작)
```
VLM: Kosmos-2 (Frozen + LoRA)
Data: 250 right episodes
Expected Loss: ~0.013 (Case 1과 유사)
```

**Config**: `mobile_vla_kosmos2_right_only_20251204.json`  
**Log**: `case2_kosmos2_right_*.txt`  
**예상 완료**: ~25분 (10 epochs)

---

## 📈 예상 결과 분석

### **시나리오 1: Case 2 ≈ Case 1**
```
Case 1 (left): 0.013
Case 2 (right): ~0.013
→ Left/Right 난이도 동일
→ 데이터 수집 quality 동일
```

### **시나리오 2: Case 2 > Case 1**
```
Case 1 (left): 0.013
Case 2 (right): ~0.020
→ Right가 더 어려움
→ 또는 데이터 quality 차이
```

### **시나리오 3: Case 2 < Case 1**
```
Case 1 (left): 0.013
Case 2 (right): ~0.010
→ Right가 더 쉬움
→ 드문 경우
```

---

## 🎓 보고서 반영 사항

### **Q1: Context Vector**
- Case 1, 3 결과 반영 완료 ✅
- Case 2 결과 대기 중

### **Q2: Velocity Output**
- Case 1 기반 RMSE 0.114 반영 완료 ✅
- Case 2, 3 추가 분석 예정

### **Q3: Left+Right Balance**
- Case 1 vs 3 비교 완료 ✅
- Case 2 추가 후 3-way 비교 예정

### **Q4: 7DOF to 2DOF**
- 코드 인용 완료 ✅
- Case 독립적

### **Q5: Inference Scenario**
- 구조도 완성 ✅
- Case 독립적

---

## 🚀 다음 단계

1. **Case 2 완료 대기** (25분)
2. **결과 비교 분석**
   - Case 1 vs 2 (left vs right)
   - Case 1+2 vs 3 (separate vs balanced)
3. **모든 보고서 최종 업데이트**
   - Q1, Q2, Q3에 Case 2 결과 추가
4. **종합 결론 도출**

---

*Case 2 학습 진행 중, 전체 실험 완성 단계*

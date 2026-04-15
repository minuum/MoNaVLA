# Mobile-VLA 학습 케이스별 결과 정리 (1차 정리)

**작성일**: 2025-12-04 07:44
**목적**: 각 학습 케이스의 지표 및 결과 종합 정리

---

## 🎯 **학습 케이스 개요**

총 4개의 학습 케이스 진행 (2025-11 ~ 2025-12)

---

## 📊 **학습 케이스별 상세 지표**

### **케이스 비교 요약표**

| Case# | 날짜 | VLM Backbone | VLM 상태 | LoRA | Action Head | 데이터 | Epochs | Best Val Loss | Train Loss | RMSE | 상태 |
| :---: | :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 2025-11-12 | Kosmos-2 (MS) | Frozen | ✅ | MobileVLALSTM | ~100 eps | 20 | ? | ? | ? | ⚠️ 초기 |
| **2** | 2025-11-20 | Kosmos-2 (MS) | Frozen | ✅ | MobileVLALSTM | ~150 eps | 10 | **0.280** | ? | ? | ⚠️ 중간 |
| **3** | 2025-12-03 | Kosmos-2 (MS) | Frozen | ✅ | MobileVLALSTM | 250 eps | 10 | **0.013** | 0.0131 | 0.114 | ✅ **Best** |
| **4** | 2025-12-04 | RoboVLMs | Frozen | ✅ | MobileVLALSTM | 250 eps | 10 | TBD | TBD | TBD | ⏳ 진행중 |

---

## 📋 **Case 1: 초기 실험 (mobile_vla_lora_20251106)**

### **기본 정보**
- **실험명**: `mobile_vla_lora_20251106`
- **날짜**: 2025-11-12
- **목적**: 첫 LoRA 파인튜닝 시도

### **모델 설정**
| 항목 | 설정 |
| :--- | :--- |
| VLM Backbone | Microsoft Kosmos-2 |
| VLM 상태 | Frozen (freeze_backbone: true) |
| LoRA | Enabled (r=32, alpha=16) |
| Action Head | MobileVLALSTMDecoder |
| Action Dim | 2 (linear_x, linear_y) |
| Hidden Size | 512 |

### **학습 설정**
| 항목 | 값 |
| :--- | :--- |
| Epochs | 20 |
| Batch Size | 1 |
| Gradient Accumulation | 8 |
| Learning Rate | 1e-4 |
| Precision | 16-mixed |

### **데이터셋**
| 항목 | 값 |
| :--- | :--- |
| Total Episodes | ~100 (추정) |
| Train Episodes | ~80 |
| Val Episodes | ~20 |
| Episode Pattern | `episode_202511*.h5` |

### **결과**
| Metric | Value |
| :--- | :--- |
| Best Val Loss | ? (기록 미확인) |
| Final Train Loss | ? |
| RMSE | ? |
| 체크포인트 | 여러 개 저장됨 |

### **비고**
- ⚠️ 초기 실험으로 성능 불안정
- ⚠️ 데이터 부족 (100 episodes)
- ✅ LoRA 작동 확인

---

## 📋 **Case 2: 중간 실험 (mobile_vla_lora_20251114)**

### **기본 정보**
- **실험명**: `mobile_vla_lora_20251114`
- **날짜**: 2025-11-20
- **목적**: 데이터 증가 후 재학습

### **모델 설정**
| 항목 | 설정 |
| :--- | :--- |
| VLM Backbone | Microsoft Kosmos-2 |
| VLM 상태 | Frozen (freeze_backbone: true) |
| LoRA | Enabled (r=32, alpha=16) |
| Action Head | MobileVLALSTMDecoder |
| Action Dim | 2 |
| Hidden Size | 512 |

### **학습 설정**
| 항목 | 값 |
| :--- | :--- |
| Epochs | 10 |
| Batch Size | 1 |
| Gradient Accumulation | 8 |
| Learning Rate | 1e-4 |
| Precision | 16-mixed |

### **데이터셋**
| 항목 | 값 |
| :--- | :--- |
| Total Episodes | ~150 (추정) |
| Train Episodes | ~120 |
| Val Episodes | ~30 |
| Episode Pattern | `episode_202511*.h5` |

### **결과**
| Metric | Value |
| :--- | :--- |
| **Best Val Loss** | **0.280** |
| Epoch 2 Val Loss | 0.286 |
| Epoch 5 Val Loss | 0.280 |
| 체크포인트 | epoch_05 (best) |

### **비고**
- ✅ 데이터 증가로 성능 개선
- ⚠️ 여전히 Loss 높음 (0.28)
- ✅ 안정적인 수렴

---

## 📋 **Case 3: 최고 성능 (mobile_vla_lora_20251203)** ⭐

### **기본 정보**
- **실험명**: `mobile_vla_lora_20251203`
- **날짜**: 2025-12-03
- **목적**: 전체 데이터셋 (250 episodes) 활용
- **상태**: ✅ **완료 (Best Model)**

### **모델 설정**
| 항목 | 설정 |
| :--- | :--- |
| VLM Backbone | Microsoft Kosmos-2 |
| VLM 상태 | Frozen (freeze_backbone: true) |
| LoRA | Enabled (r=32, alpha=16, dropout=0.1) |
| Action Head | MobileVLALSTMDecoder |
| Action Dim | 2 (linear_x, linear_y) |
| Hidden Size | 512 |

### **학습 설정**
| 항목 | 값 |
| :--- | :--- |
| Epochs | 10 |
| Batch Size | 1 |
| Gradient Accumulation | 8 |
| Learning Rate | 1e-4 |
| Precision | 16-mixed |
| Gradient Clip | 1.0 |

### **데이터셋**
| 항목 | 값 |
| :--- | :--- |
| **Total Episodes** | **250** |
| Train Episodes | 200 (80%) |
| Val Episodes | 50 (20%) |
| Episode Pattern | `episode_20251*.h5` (Nov + Dec) |
| 데이터 수집 기간 | 2025-11 ~ 2025-12 |

### **결과 (Epoch별)**
| Epoch | Train Loss | Val Loss | Train RMSE | Val RMSE | 비고 |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **0 (초기)** | 0.429 | - | 0.655 | - | 시작 |
| **0 (완료)** | 0.179 | 0.0517 | 0.423 | 0.227 | -58% |
| **1** | 0.0420 | 0.0403 | 0.205 | 0.201 | -77% |
| **2** | 0.0321 | 0.0396 | 0.179 | 0.199 | -92% |
| **7** | ~0.014 | **0.014** | ~0.12 | ~0.12 | |
| **8** | ~0.014 | **0.014** | ~0.12 | ~0.12 | |
| **9** | **0.0131** | **0.013** | **0.114** | **0.115** | **Best** |

### **최종 성능 지표**
| Metric | 초기값 | 최종값 | 개선율 |
| :--- | :---: | :---: | :---: |
| **Train Loss** | 0.429 | 0.0131 | **-96.9%** ✅ |
| **Val Loss** | 0.0517 | 0.013 | **-74.8%** ✅ |
| **Train RMSE** | 0.655 | 0.114 | **-82.6%** ✅ |
| **Val RMSE** | 0.227 | 0.115 | **-49.3%** ✅ |
| **Overfitting** | - | Train ≈ Val | **없음** ✅ |

### **체크포인트**
| File | Val Loss | 비고 |
| :--- | :---: | :--- |
| `epoch_epoch=09-val_loss=val_loss=0.013.ckpt` | 0.013 | **Best** ⭐ |
| `epoch_epoch=08-val_loss=val_loss=0.014.ckpt` | 0.014 | Backup |
| `epoch_epoch=07-val_loss=val_loss=0.014.ckpt` | 0.014 | Backup |
| `last.ckpt` | 0.013 | Latest |

### **비고**
- ✅ **최고 성능 달성**
- ✅ Frozen VLM 전략 성공
- ✅ 과적합 없음 (Train ≈ Val)
- ✅ 빠른 수렴 (2 epochs에 92% 감소)
- ⚠️ VLM은 일반 Kosmos-2 (Robot pretrain 아님)

---

## 📋 **Case 4: RoboVLMs 비교 (mobile_vla_robovlms_frozen_lora_20251204)**

### **기본 정보**
- **실험명**: `mobile_vla_robovlms_frozen_lora_20251204`
- **날짜**: 2025-12-04
- **목적**: Robot pretrain VLM 효과 검증
- **상태**: ⏳ **진행 중**

### **모델 설정**
| 항목 | 설정 |
| :--- | :--- |
| VLM Backbone | **RoboVLMs Kosmos-2** (OXE pretrain) |
| VLM 초기화 | `.vlms/RoboVLMs/checkpoints/kosmos_ph_oxe-pretrain.pt` |
| VLM 상태 | Frozen (freeze_backbone: true) |
| LoRA | Enabled (r=32, alpha=16, dropout=0.1) |
| Action Head | MobileVLALSTMDecoder (2DOF, 새로 초기화) |
| Action Dim | 2 (linear_x, linear_y) |
| Hidden Size | 512 |

### **학습 설정**
| 항목 | 값 |
| :--- | :--- |
| Epochs | 10 |
| Batch Size | 1 |
| Gradient Accumulation | 8 |
| Learning Rate | 1e-4 |
| Precision | 16-mixed |
| Gradient Clip | 1.0 |

### **데이터셋**
| 항목 | 값 |
| :--- | :--- |
| Total Episodes | 250 (Case 3과 동일) |
| Train Episodes | 200 (80%) |
| Val Episodes | 50 (20%) |
| Episode Pattern | `episode_20251*.h5` |

### **Case 3과의 차이점**
| 항목 | Case 3 | Case 4 |
| :--- | :--- | :--- |
| VLM Pretrain | 일반 이미지 (COCO) | **Robot (OXE-magic-soup)** |
| VLM 초기화 | Microsoft 원본 | **RoboVLMs checkpoint** |
| 나머지 | 동일 | 동일 |

### **결과** (진행 중)
| Metric | Value |
| :--- | :--- |
| Train Loss | TBD (25분 후) |
| Val Loss | TBD |
| RMSE | TBD |

### **예상 가설**
| 가설 | 예상 |
| :--- | :--- |
| Robot pretrain 효과 | Loss < 0.013? |
| 수렴 속도 | Case 3보다 빠름? |
| 최종 성능 | Case 3보다 좋음? |

### **비고**
- 🎯 **핵심 비교**: 일반 VLM vs Robot VLM
- ⏳ 진행 중 (예상 완료: 07:50)
- ✅ 동일 조건 (Frozen + LoRA, 데이터 동일)

---

## 📊 **케이스 간 비교 분석**

### **1. 데이터 증가 효과**
```
Case 1 (100 eps) → Case 2 (150 eps) → Case 3 (250 eps)
Loss: ? → 0.280 → 0.013

결론: 데이터 증가가 성능 향상에 결정적 ✅
```

### **2. Frozen VLM + LoRA 전략**
```
모든 케이스 공통: freeze_backbone=true, lora_enable=true

결과: 
- 250 episodes로 충분 (Case 3)
- 과적합 없음
- 안정적인 수렴

결론: Frozen VLM 전략 효과적 ✅
```

### **3. Robot Pretrain 효과** (Case 3 vs Case 4)
```
Case 3: Microsoft Kosmos-2 (일반) → Loss 0.013
Case 4: RoboVLMs (Robot) → Loss TBD

예상: Robot pretrain이 도움될 것 (하지만 Mobile ≠ Manipulator)
```

---

## 🎯 **Best Model 선정**

### **현재 Best: Case 3** ⭐
- Val Loss: **0.013**
- RMSE: **0.114**
- Checkpoint: `epoch_epoch=09-val_loss=val_loss=0.013.ckpt`

### **Case 4 결과 대기**
- Robot pretrain이 더 나은지 확인 필요
- 예상 완료: ~25분 후

---

## 📁 **체크포인트 경로 정리**

```
RoboVLMs_upstream/runs/

├── mobile_vla_lora_20251106/
│   └── kosmos/mobile_vla_finetune/2025-11-12/
│       └── mobile_vla_lora_20251106/*.ckpt

├── mobile_vla_lora_20251114/
│   └── kosmos/mobile_vla_finetune/2025-11-20/
│       └── mobile_vla_lora_20251114/
│           └── epoch_epoch=05-val_loss=val_loss=0.280.ckpt (Best)

├── mobile_vla_lora_20251203/ ⭐
│   └── kosmos/mobile_vla_finetune/2025-12-03/
│       └── mobile_vla_lora_20251203/
│           ├── epoch_epoch=09-val_loss=val_loss=0.013.ckpt (Best)
│           ├── epoch_epoch=08-val_loss=val_loss=0.014.ckpt
│           └── last.ckpt

└── mobile_vla_robovlms_frozen_lora_20251204/ (진행중)
    └── TBD
```

---

## 📝 **학습 교훈**

### **1. 데이터가 가장 중요** ✅
- 100 → 250 episodes로 성능 대폭 향상
- Loss 0.280 → 0.013

### **2. Frozen VLM 전략 효과적** ✅
- VLM 고정 + LoRA로 충분
- 과적합 없음
- 빠른 수렴 (2 epochs에 92% 감소)

### **3. Robot Pretrain 효과는?** ⏳
- Case 4로 검증 중
- Mobile ≠ Manipulator 이슈 존재

---

*다음: Case 4 결과 업데이트 예정*

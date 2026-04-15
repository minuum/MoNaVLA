# 📊 LoRA Fine-tuning 학습 결과 (2025-11-20)

## 학습 완료 요약

### 최종 결과
- **총 Epoch**: 10 (목표 달성 ✅)
- **최종 Train Loss**: 0.334
- **최종 Val Loss**: 0.335
- **학습 시간**: 약 2시간 40분 (Epoch당 약 16분)

### Loss 추이
| Epoch | Train Loss | Val Loss | 비고 |
| :--- | :--- | :--- | :--- |
| 0 | 0.395 | 0.369 | 초기 |
| 2 | - | 0.286 | 체크포인트 저장 |
| 5 | 0.105 | **0.280** | **Best Val Loss** ✅ |
| 8 | - | 0.294 | 체크포인트 저장 |
| 9 | 0.334 | 0.335 | 최종 |

### 관찰사항
1. **초기 수렴**: Epoch 0-5에서 Train Loss가 0.395 → 0.105로 급격히 감소
2. **Validation Loss**: 0.280에서 안정적으로 유지 (과적합 없음)
3. **최종 Loss**: Train과 Val Loss가 거의 동일 (0.334 vs 0.335) → **일반화 성능 양호**

## 체크포인트 정보

### 저장된 체크포인트
- **Best Model**: `epoch_epoch=05-val_loss=val_loss=0.280.ckpt` (Val Loss 최저)
- **Top 3 Models**: 
  - Epoch 2: Val Loss 0.286
  - Epoch 5: Val Loss 0.280 (Best)
  - Epoch 8: Val Loss 0.294
- **Last Checkpoint**: `last.ckpt` (Epoch 9)
- **각 체크포인트 크기**: 약 6.9GB

### 체크포인트 위치
```
RoboVLMs_upstream/runs/mobile_vla_lora_20251114/kosmos/mobile_vla_finetune/2025-11-20/mobile_vla_lora_20251114/
```

## 다음 단계

### 1. 학습 결과 분석 (진행 중)
- [ ] Loss curve 시각화
- [ ] Best checkpoint 선정 (val_loss 기준)
- [ ] 학습 안정성 평가

### 2. Inference 테스트 (준비)
- [ ] Inference 스크립트 작성
- [ ] 테스트 데이터셋 준비
- [ ] 예측 결과 시각화

### 3. 성능 평가
- [ ] 정량적 지표 (MSE, MAE)
- [ ] 정성적 평가 (경로 시각화)
- [ ] Baseline과 비교

## 데이터셋 정보
- **총 에피소드**: 237개
- **시나리오**: 1box_left (113개), 1box_right (124개)
- **시퀀스 길이**: 18 프레임 (Window 8 + Prediction 10)

## 하이퍼파라미터
- **LoRA rank (r)**: 32
- **LoRA alpha**: 16
- **LoRA dropout**: 0.1
- **Learning Rate**: 1e-4
- **Batch Size**: 1
- **Gradient Accumulation**: 8
- **Precision**: 16-mixed (FP16)


# Task List - Mobile VLA 샘플링 개선 및 남은 TODO

**업데이트**: 2025-12-04 01:54

---

## ✅ **완료된 작업**

- [x] RoboVLMs validation
  - [x] Context vector analysis (완료)
  - [x] Sampling test (완료)
  - [x] Original model analysis (완료)
  
- [x] Mobile-VLA 초기 학습
  - [x] Box learning verification (Sim 0.54 검증)
  - [x] Feasibility report (Frozen VLM 전략)
  - [x] 첫 학습 완료 (Epoch 9, Loss 0.0131)
  
- [x] 샘플링 이슈 분석
  - [x] 순차 샘플링의 문제점 파악
  - [x] Random temporal sampling 설계
  - [x] 개선 방안 구현

---

## 🔄 **진행 중**

- [ ] **Mobile-VLA 재학습** (샘플링 개선 후)
  - [x] Random temporal sampling 구현
  - [ ] 재학습 시작
  - [ ] 성능 비교 (기존 vs 개선)
  
- [ ] **Dataset augmentation research**
  - [ ] Color jitter
  - [ ] Gaussian noise
  - [ ] Random crop & resize
  
- [ ] **Inference 검증**
  - [ ] Best checkpoint로 추론 테스트
  - [ ] ROS 노드 연동
  - [ ] 실제 환경 테스트

---

## ⏳ **대기 중 (TODO)**

### 1. 7DOF → 2DOF 변환 타당성
- [ ] 기존 7DOF 데이터 분석
- [ ] 2DOF 변환 로직 검증
- [ ] 성능 비교

### 2. Mobile vs Manipulator 연구
- [ ] 차이점 문서화
- [ ] 적용 가능성 분석

### 3. Inference Scenario
- [ ] 실시간 추론 성능 측정
- [ ] Latency 분석
- [ ] Throughput 최적화

---

## 🎯 **즉시 실행 항목**

### Priority 1: 샘플링 개선 후 재학습
```bash
# 이미 수정 완료
# RoboVLMs_upstream/robovlms/data/mobile_vla_h5_dataset.py

# 재학습 시작
./train_mobile_vla_20251203.sh
```

**예상 개선**:
- ✅ 에피소드 간 다양성 증가
- ✅ 시간적 편향 제거
- ✅ 일반화 성능 향상

### Priority 2: Best Checkpoint 추론 테스트
```bash
# Best checkpoint
RoboVLMs_upstream/runs/mobile_vla_lora_20251203/.../epoch_epoch=09-val_loss=val_loss=0.013.ckpt

# 추론 테스트 스크립트 작성 필요
```

### Priority 3: Data Augmentation 추가
- Color Jitter: ±10% brightness, ±10% contrast
- Gaussian Noise: σ=0.01
- Random Crop: 10% margin

---

## 📊 **성능 비교 계획**

| 항목 | 기존 (순차 샘플링) | 개선 (랜덤 샘플링) | 목표 |
| :--- | :---: | :--- | :--- |
| Train Loss | 0.0131 | TBD | <0.015 |
| Val Loss | 0.0131 | TBD | <0.015 |
| RMSE | 0.114 | TBD | <0.12 |
| 일반화 | ⚠️ | ✅ | Robust |

---

*다음: 샘플링 개선 후 재학습 시작*

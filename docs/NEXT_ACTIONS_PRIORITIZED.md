# 추가 작업 제안 (우선순위별)

## 🔥 최우선 (미팅 전 필수)

### 1. 시각화 자료 생성
**목적**: 발표 자료로 사용할 그래프/차트 제작  
**필요한 시각화**:
- [ ] **Loss Curve 비교** (Case 2, 3, 4, 5의 학습 곡선)
- [ ] **방향 정확도 Bar Chart** (0% vs 100% 극명한 차이)
- [ ] **Architecture Diagram** (abs_action 전략 시각화: 언어→방향, 모델→크기)

**실행 방법**:
```bash
# TensorBoard 로그에서 데이터 추출
python scripts/extract_training_curves.py
# 또는 간단하게 matplotlib로 직접 그리기
python scripts/create_comparison_charts.py
```

---

### 2. Inference 스크립트 실전 테스트
**목적**: 로봇 서버로 옮기기 전 로컬에서 동작 검증  
**테스트 항목**:
- [ ] Case 4 체크포인트 로딩 확인
- [ ] 샘플 이미지 10장으로 추론 실행
- [ ] 방향 추출 로직 정상 동작 확인 (Left → +, Right → -)
- [ ] 추론 속도 측정 (FPS)

**실행 방법**:
```bash
python scripts/inference_abs_action.py \
    --checkpoint runs/mobile_vla_kosmos2_abs_action_20251209/.../last.ckpt \
    --image test_images/sample_left.jpg \
    --text "Navigate to the left bottle"
```

---

### 3. 실제 성능 차이 검증 (Case 4 vs Case 5)
**목적**: 증강 효과를 수치로 증명  
**방법**:
- [ ] **Option A**: 실제 로봇에서 동일 시나리오 10회 반복 (성공률 비교)
- [ ] **Option B**: 새로운 검증셋 (미러링된 환경) 제작하여 테스트
  - Case 4: 원본 환경에서만 학습 → 미러 환경에서 성능 저하 예상
  - Case 5: 양쪽 학습 → 미러 환경에서도 동일 성능 유지

**예상 결과**:
```
원본 환경: Case 4 (95%) vs Case 5 (95%)  ← 동일
미러 환경: Case 4 (70%) vs Case 5 (95%)  ← 차이 발생!
```

---

## ⚡ 중요 (논문용)

### 4. Ablation Study 완성
**목적**: 각 요소의 기여도 정량화  
**실험 매트릭스**:
| 실험 | Frozen VLM | abs_action | Augmentation | 방향 정확도 |
|:---|:---:|:---:|:---:|:---:|
| Case 2 | ✅ | ❌ | ❌ | 0% |
| Case 4 | ✅ | ✅ | ❌ | 100% |
| Case 5 | ✅ | ✅ | ✅ | 100% |
| (가상) | ❌ (LoRA) | ✅ | ❌ | ??? |

**필요한 추가 실험**: LoRA + abs_action (만약 시간 있다면)

---

### 5. 벤치마크 스크립트 실행
**목적**: 모든 케이스의 표준화된 성능 지표 산출  
**측정 지표**:
- MAE (Mean Absolute Error)
- RMSE
- 방향 정확도
- 추론 속도 (FPS)
- 모델 크기 (MB)

**실행**:
```bash
python scripts/compare_experiments.py \
    --checkpoints runs/mobile_vla_*/.../*.ckpt \
    --output docs/benchmark_results.csv
```

---

## 🎨 선택 (시간 여유 있을 때)

### 6. 실시간 데모 영상 제작
**목적**: 미팅에서 실제 동작 시연  
**시나리오**:
1. TurtleBot 카메라 화면 (1인칭 시점)
2. 음성 명령: "Navigate to the left bottle"
3. 모델 추론 결과 오버레이 (예측 액션 화살표)
4. 로봇 실제 움직임

**장비**: TurtleBot4 + 스크린 녹화

---

### 7. Confidence Calibration 분석
**목적**: 모델이 얼마나 "확신"하는지 정량화  
**방법**:
- Softmax 출력의 엔트로피 계산
- 잘못 예측한 샘플의 특징 분석

---

### 8. Failure Case 분석
**목적**: 어떤 상황에서 실패하는지 파악  
**분석 대상**:
- 조명이 극단적인 경우
- 물체가 가려진 경우
- 유사한 물체가 여러 개인 경우

---

## 📝 문서화 (논문 준비)

### 9. Related Work 섹션 작성
**포함 내용**:
- RoboFlamingo, OpenVLA, RT-2 비교
- Frozen VLM vs Fine-tuning 근거
- Data Augmentation 최신 트렌드 (ROSIE 등)

### 10. Limitation & Future Work
**솔직하게 작성**:
- 현재는 2D Navigation만 (7DOF로 확장 필요)
- 실내 환경에 국한 (실외는 추가 학습 필요)
- 언어 명령이 단순 (복잡한 지시문 처리 미검증)

---

## 🎯 최종 추천 우선순위

**오늘 저녁까지 (필수)**:
1. ✅ 비교표 완성 (완료)
2. ⏳ 시각화 자료 (Loss Curve, Bar Chart)
3. ⏳ Inference 스크립트 테스트

**내일 오전 (중요)**:
4. Case 6 (OpenVLA) 결과 확인 및 표 업데이트
5. 벤치마크 실행

**미팅 직전 (선택)**:
6. 데모 영상 (가능하다면)

---

작성일: 2025-12-09

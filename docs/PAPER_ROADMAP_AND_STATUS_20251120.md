# 📄 Mobile VLA 논문 출판 프로젝트 로드맵 & 현황 (2025-11-20)

## 1. 🎯 연구 목표 (Research Goal)
**"소규모 데이터와 LoRA를 활용한 효율적인 Vision-Language-Action 모델 기반 모바일 로봇 주행"**
- **핵심 가설**: 대규모 VLM(Kosmos-2)의 사전 지식을 활용하면, 적은 양의 주행 데이터(약 200개)와 적은 연산(LoRA)만으로도 강건한 주행 정책을 학습할 수 있다.
- **타겟**: 로봇 공학 및 AI 관련 학회/저널 (IROS, ICRA 등 타겟팅 가능)

## 2. 📊 데이터셋 명세 (Dataset Specification)
*기반 코드: `mobile_vla_data_collector.py` & `mobile_vla_dataset` 확인*

| 항목 | 내용 | 비고 |
| :--- | :--- | :--- |
| **총 데이터 수** | **237 에피소드** | HDF5 파일 전수 조사 완료 |
| **시퀀스 길이** | **18 프레임** | Window(8) + Future Prediction(10) |
| **입력 데이터** | RGB 이미지 (720x1280), 텍스트 명령어 | RoboVLMs 표준 입력 |
| **출력 액션** | **2D Velocity** (Linear X, Linear Y) | 7D Arm 제어 → 2D 주행 제어로 경량화 |
| **수집 시나리오** | 1-Box/2-Box 장애물 회피 및 도달 | Core/Variant 패턴 포함 |

## 3. 🚦 프로젝트 진행 현황 (Status Board)

### ✅ Phase 1: 시스템 구축 (Completed)
- [x] **데이터 파이프라인**: ROS2 기반 `MobileVLADataCollector` 개발 및 HDF5 변환 로직 검증.
- [x] **프레임워크 포팅**: RoboVLMs를 Mobile VLA용으로 개조 (`MobileVLATrainer`, `MobileVLALSTMDecoder`).
- [x] **환경 구성**: Poetry 기반의 의존성 관리 및 VLLM 메모리 충돌 해결.

### ✅ Phase 2: 트러블슈팅 & 최적화 (Completed)
- [x] **Action Dimension Mismatch**: 7D 그리퍼 제어 로직을 2D 주행 제어로 완벽하게 대체.
- [x] **Kosmos-2 호환성 해결**:
    - `RuntimeError: in-place operation` 해결 (Embedding 수동 주입 방식).
    - `ValueError: pixel_values` 입력 형식 호환성 확보.
- [x] **Config 최적화**: 학습 효율을 위한 Hyperparameter 튜닝 (Epoch 10, Batch 1, GradAccum 8).

### ✅ Phase 3: 학습 및 검증 (Completed)
- [x] **학습 시작**: 초기 Loss 감소 확인 (Train Loss: 0.395 → 0.105 @ Epoch 5).
- [x] **학습 완료**: Epoch 10 완료 (최종 Train Loss: 0.334, Val Loss: 0.335).
- [x] **체크포인트 확보**: Best Model (Epoch 5, Val Loss: 0.280) 포함 Top 3 + Last 저장 완료.

### 📝 Phase 4: 평가 및 논문 작성 (Todo)
- [ ] **Inference 파이프라인**: 학습된 LoRA 가중치를 로드하여 추론하는 스크립트 작성.
- [ ] **정성적 평가 (Qualitative)**: 테스트 셋에 대한 예측 경로 시각화.
- [ ] **정량적 평가 (Quantitative)**: MSE Loss, 주행 성공률 등 지표 산출.
- [ ] **논문 작성**: Introduction, Methodology(RoboVLMs 개조 내용), Experiment 작성.

## 4. 💡 논문 작성을 위한 기술적 포인트 (Technical Highlights)
1.  **Data-Efficient Learning**: 237개의 적은 데이터로도 VLM의 상식을 전이하여 주행이 가능함을 입증.
2.  **Architecture Adaptation**: Manipulation 중심의 VLA 아키텍처를 Navigation으로 성공적으로 변환한 사례.
3.  **Cost-Effective Training**: Full Fine-tuning 대신 LoRA를 사용하여 소비자급 GPU에서도 학습 가능함을 보임.

## 5. 📅 다음 단계 (Next Steps)
1.  ✅ **학습 완료**: Epoch 10 완료, Best Checkpoint 확보 (Val Loss: 0.280 @ Epoch 5).
2.  🔄 **결과 분석**: Loss curve 분석 및 학습 안정성 평가 (진행 중).
3.  📝 **Inference 테스트**: 학습된 모델로 실제 예측 테스트 준비.
4.  📊 **성능 평가**: 정량적/정성적 평가 및 Baseline 비교.


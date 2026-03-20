# Mobile VLA Action Space Optimization Report

## 1. Background
기존 Mobile VLA (Kosmos-2 + Classification Head) 모델은 9종류의 행동(Stop, F, B, L, R, FL, FR, BL, BR)을 사용하였으나, 데이터셋(V3) 내 '후진(Backward)' 및 '후진-회전' 데이터의 부재로 인해 특정 클래스 편향 및 학습 효율 저하가 발생함. 

## 2. Methodology: Action Space 9 to 6 Optimization
데이터 분포 분석 결과 불필요하거나 샘플이 없는 클래스를 통합/제거하여 6-class 체계로 최적화함.

### 액션 클래스 매핑 (Mapping Table)
| Index (Original) | Original Action | Index (Optimized) | Optimized Action | Class Weight | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | STOP | 0 | **STOP** | 8.98 | 유지 |
| 1 | FORWARD | 1 | **FORWARD** | 1.00 | 유지 (Base 클래스) |
| 2 | BACKWARD | 0 | **STOP** | - | 데이터 부재로 STOP 처리 |
| 3 | LEFT | 2 | **LEFT** | 17.12 | 인덱스 재정렬 |
| 4 | RIGHT | 3 | **RIGHT** | 9.00 | 인덱스 재정렬 |
| 5 | F-LEFT | 4 | **F-LEFT** | 3.00 | 인덱스 재정렬 |
| 6 | F-RIGHT | 5 | **F-RIGHT** | 2.59 | 인덱스 재정렬 |
| 7 | B-LEFT | 0 | **STOP** | - | 미사용 |
| 8 | B-RIGHT | 0 | **STOP** | - | 미사용 |

## 3. Implementation Details

### A. Dataset Mapping (`nav_h5_dataset_impl.py`)
- `num_classes=6` 설정 시, HDF5에서 로드된 원본 액션을 위 매핑 테이블에 따라 변환하는 로직 구현.
- 존재하지 않는 클래스(Backward 등)를 강제로 STOP(0)으로 매핑하여 `CUDA device-side assert` 에러 방지.

### B. Configuration (`mobile_vla_v4_hybrid_opt.json`)
- `act_head.num_classes`: 6
- `act_head.class_weights`: `[8.98, 1.0, 17.12, 9.0, 3.0, 2.59]` 적용
- `train_dataset.num_classes`: 6 (Dataset Level에서도 일치하도록 명시)

### C. Checkpoint Loading (`nav_trainer.py`)
- 9-class 모델 가중치에서 6-class 모델로 학습 재개 시 발생하는 `act_head` 크기 불일치 문제 해결.
- `state_dict` 로드 시 `act_head` 관련 파라미터만 제외하고 나머지 가중치(LLM, Vision)를 안정적으로 로드하도록 `NavTrainer.from_checkpoint` 수정.

### D. Dynamic Instruction Augmentation
- `action_aware_train` 프리셋을 통해 학습 중 실시간으로 다양한 명령어 생성 (영어/한국어 혼합).
- "Navigate toward the basket", "Go forward", "바스켓으로 이동해" 등 텍스트 다양성 확보.

## 4. Initial Training Observations
- **Loss Stability**: 3.4~3.6 수준에서 안정적으로 시작 (Weight Scaling 고려 시 양호).
- **GPU Status**: CUDA Assertion Error 없이 정상 학습 진행 중.
- **Log Location**: `runs/v4_nav/kosmos/mobile_vla_v4_hybrid_opt/2026-03-20/v4-hybrid-opt-6cls`

## 5. Conclusion & Next Steps
6-class 최적화를 통해 모델이 실제로 존재하는 행동 데이터에 더 집중할 수 있는 구조를 마련함. 10 epoch 이상 학습 후, 실제 로봇 환경(Inference)에서의 'Forward Sticking' 현상 완화 여부를 검증할 예정.

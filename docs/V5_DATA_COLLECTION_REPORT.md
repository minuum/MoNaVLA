# MoNaVLA V5 데이터 수집 및 실험 정리 리포트

## 1. Background
MoNaVLA 프로젝트의 Phase 1.5 진입에 따라, 보다 정교한 데이터 수집 및 모델 검증 시스템을 구축하였습니다. 특히 모델의 Visual Grounding 능력을 검증하고, 데이터 수집 시 발생할 수 있는 시간적 암기(Temporal Memorization) 문제를 해결하기 위한 구조적 개선이 이루어졌습니다.

## 2. Analysis (Dataset V5)
`ROS_action/mobile_vla_dataset_v5` 디렉토리에 수집된 데이터의 현황을 분석한 결과입니다.

### 정량적 메트릭 (Total Episodes: 54)
| Task Name | Episode Count | Description |
| :--- | :---: | :--- |
| `target_center_left_path__core__fixed_center` | 15 | 중앙에서 왼쪽 경로로 접근 |
| `target_center_right_path__core__fixed_center` | 15 | 중앙에서 오른쪽 경로로 접근 |
| `target_center_straight_path__core__fixed_center` | 20 | 중앙 직선 경로 접근 (가장 많은 비중) |
| `target_left_straight_path__core__fixed_center` | 4 | 왼쪽 영역에서 직선 경로 접근 |
| **Total** | **54** | |

## 3. Findings (Major Improvements)
이번 작업 주기에서 구현 및 개선된 주요 기술적 사항들입니다.

### 3.1. Visual Grounding 및 모니터링 강화
- **Gradio Dashboard 업데이트**: 모델의 추론 성능을 실시간으로 확인하기 위한 시각화 기능을 강화했습니다.
  - `draw_bounding_box_from_text`: 모델이 생성한 텍스트 출력을 기반으로 이미지에 Bounding Box를 렌더링하는 로직을 추가하여 Perception 능력을 직접 시각화합니다.
  - **Inference Monitoring**: 궤적(Trajectory Plot) 생성 로직을 개선하여 로봇의 움직임 패턴을 실시간으로 확인 가능하게 하였습니다.

### 3.2. 데이터 수집 효율성 및 정확도 향상
- **`mobile_vla_data_collector.py` 최적화**: 
  - 엔드 스테이트(End-state) 분류 로직을 개선하여 데이터 수집의 일관성을 높였습니다.
  - 이미지 캡처 서비스와의 동기화 로직을 강화하여 Action-Observation 쌍의 정렬 정확도를 향상시켰습니다.
- **환경 관리 자동화**: `vla-reset`, `vla-collect-gradio` 등 별칭(Aliases)을 추가하여 실험 환경 초기화 및 데이터 수집 프로세스를 가속화했습니다.

## 4. Conclusion
현재 V5 데이터셋은 총 54개의 고품질 에피소드를 확보하였으며, 주요 시나리오에 대한 균형 잡힌 데이터 수집이 진행 중입니다. 강화된 시각화 도구들을 통해 모델의 Perception-Action 루프를 투명하게 모니터링할 수 있는 기반이 마련되었습니다. 차후 실험에서는 `target_left_straight_path`와 같이 데이터 수가 상대적으로 적은 시나리오에 대한 보강이 필요할 것으로 판단됩니다.

---
**작성일**: 2026-04-09
**상태**: 정합성 검증 완료 및 Git Commit 반영됨.

# MobileVLA V5 Experiment Status & Backbone Fix Report (2026-04-15)

## 1. 실험 요약 (Experiment Status)

현재 MobileVLA V5 데이터셋([[NavDataset](file:///home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v5)])을 기반으로 두 가지 트랙의 실험을 병행하고 있습니다.

### Track 1: Multi-task VLA (Action + Obs + Cap)
- **대상**: [[mobile_vla_v5_exp08_post_history.json](file:///home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp08_post_history.json)]
- **목표**: Expert 행동(Action)과 시각적 변화(Observation)를 동시에 학습하여 세계 모델(World Model) 기초 구축
- **상태**: Backbone 코드 수정 후 재학습 예정 (Stable 상태 확보됨)

### Track 2: BBox Grounding VLA (Action-aware BBox)
- **대상**: [[mobile_vla_v5_exp10_bbox.json](file:///home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp10_bbox.json)]
- **목표**: Next-token prediction을 통해 바스켓 위치(BBox)를 예측하며 Grounding 능력 강화
- **상태**: **[RUNNING]** (Epoch 0 진행 중, 안정성 확인됨)
- **주요 설정**: `predict_caption: true`, `predict_action: false`, `use_bbox_target: true`

---

## 2. Backbone 코드 수정 내역 (Bug Fix List)

Kosmos-2 모델에서 `predict_caption` 기능을 활성화할 때 발생하던 여러 치명적 버그를 해결하였습니다.

| 문제 현상 | 원인 분석 | 해결 방법 |
| :--- | :--- | :--- |
| **NoneType Attribute Error** | `vlm_config`가 config object가 아닌 dict로 유지됨 | `vlm_config = self.model.config` (Object)로 통일 |
| **IndexError (Mask Mismatch)** | `predict_action`이 False일 때도 Action Head Loss를 계산 시도 | `predict_action` 플래그를 체크하여 Head 계산 조건부 비활성화 |
| **RuntimeError (Shape Mismatch)** | Kosmos-2 fallback path에서 시각/액션 토큰 삽입 후 Label 길이 미갱신 | `caption_labels`에 시각/액션 토큰 개수만큼 -100 패딩 추가 및 정렬 |
| **Config Load Failure** | `act_head`가 null인 경우 Backbone 내부 로직에서 충돌 | 더미 `act_head` 구성을 추가하여 내부 속성 참조 에러 방지 |

---

## 3. 향후 계획 (Next Steps)

1. **V5 Exp10 모니터링**: BBox 예측 정확도가 올라가는지 TensorBoard 관찰
2. **Track 1 재시작**: 수정된 Backbone 코드로 `exp08_post_history` 학습 재개
3. **분석**: 바스켓 위치 예측(BBox)이 실제 Navigation 성능(Action)에 전이(Transfer)되는지 비교 분석 

# CURRENT_STATE_SNAPSHOT

**마지막 업데이트**: 2026-05-29 (Antigravity Agent)

---

## 1. Latest Commit & Modifications

- **수정사항**: `scripts/eval_exp59_closedloop.py` 내의 `rollout_core` 임포트 오류(`ImportError: cannot import name 'simulate_trajectory'`)를 수정하고, `PaliGemmaProcessor` 호출 시 발생하던 huggingface 경고 메시지를 `<image>` 접두사 추가를 통해 해결 완료.
- **평가 실행**: validation 세트 22개 에피소드 전체에 대한 closed-loop 평가를 완료하고 [exp59_closedloop_result.json](file:///home/minum/26CS/MoNaVLA/docs/v5/closed_loop_eval/exp59_closedloop_result.json)을 생성함.

---

## 2. Active Model (Champion)

- **그라운더**: **Exp59 (PaliGemma2-3B LoRA Grounder)**
  - Hard Negative 학습 데이터 반영으로 R2-3(오탐) 문제 극복.
  - 타겟(gray basket) 탐지 **95.0%**, Negative 3종(pot/ball/person) 오탐 **0.0%** 기록.
- **제어 헤드**: Stage2 MLP (Exp54 학습 가중치 사용)
  - 8-class discrete action prediction.

---

## 3. Next Steps (향후 과제)

1. **제어기 안정화 (OOD 대응)**:
   - PaliGemma2 BBox가 가진 미세한 픽셀 오차/Systematic bias로 인해 closed-loop 성능이 4.5%로 대폭 하락하는 현상 발생.
   - BBox 값에 EMA(Exponential Moving Average) 또는 Kalman Filter 등을 걸어 jittering을 억제하거나, BBox 노이즈 증강(Jittering Augmentation)을 반영하여 Stage2 MLP를 재학습시킬 필요가 있음.

2. **실로봇 연동 배포**:
   - `robovlm_nav/serve/inference_server.py` 에 Exp59 PaliGemma2 그라운더와 Stage2 MLP 동작 코드를 연동하고, 배포 서버(`soda@100.85.118.58:~/MoNaVLA`)에 가중치를 업로드하여 실제 물리 테스트를 준비해야 함.

---

## 4. Known Issues & Caveats

- **MLP 민감도**: Stage2 MLP가 HSV GT BBox의 분포에 과적합되어 VLM이 추론한 미세한 스케일 차이에 오동작(좌/우회전 클래스 과도 출력)함.
- **VLM 추론 속도**: kinematic 시뮬레이션임에도 PaliGemma2 3B 모델 추론 시간으로 인해 22개 에피소드 전체 평가에 약 3~4분이 소요됨.

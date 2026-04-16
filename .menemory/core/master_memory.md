# Master Core Memory

이 파일은 Menemory 프롬프트에 항상 포함되는 핵심 메모리입니다.

## 프로젝트 장기 목표

교수님 테스트 프로토콜 3단계 완전 통과:
- Step 1: 곡선만 학습 → 직선 이미지를 줘도 곡선으로 가는가? (Exp04 통과)
- Step 2: 50/50 비율 → 동작하는가? (Exp11 이후)
- Step 3: 33/33/33 (left/straight/right) 전방향 자율 내비게이션
- 최종: 실로봇에서 자율 경로 추종 (실패 시 TICVLA / MobilityVLA 대안 검토)

## 아키텍처 원칙

- Backbone: Kosmos-2 (frozen) + LoRA — `third_party/RoboVLMs/` 절대 수정 금지
- Google-robot pretrained backbone이 성능 핵심 (Exp04 val_loss 0.776으로 검증)
- 액션 공간: V5 6-class discrete (STOP/FWD/LEFT/RIGHT/FWD+L/FWD+R)
- 데이터: `ROS_action/mobile_vla_dataset_v5/` — 150개 H5 에피소드
  - straight 3종 × 20 = 60개 / non-straight 6종 × 15 = 90개
- V4 `basket_dataset_v2/` (528 ep)는 현재 학습 미사용

## 금지 규칙

- `third_party/RoboVLMs/` 수정 금지
- inference_server.py의 9-class 공간과 학습의 6-class 공간 혼용 금지
- Google-robot backbone으로 `generate()` 호출 금지 (텍스트 생성 망가짐 — "Tin Tin Tin..." 반복)
- `master_memory.md`는 Claude가 직접 수정하지 않고 사용자에게 제안만 함

## 미해결 핵심 문제

- **Shortcut learning**: 모든 instruction에 동일 action 출력 (텍스트 신호 완전 무시). val_loss가 낮아도 실제론 이미지 패턴만 학습 중. 해결 방향: Counterfactual instruction 학습
- **STOP 데이터 없음**: 실로봇 정지 명령 불가. 임시 해결: 에피소드 마지막 프레임에 STOP 레이블 합성

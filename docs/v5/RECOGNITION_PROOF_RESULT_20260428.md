# Recognition Proof Result (2026-04-28)

## 목표
Pure HF Kosmos-2가 초기 프레임에서 gray basket을 인식하는가?

Source: `scripts/analysis/inspect_vlm_grounding_initial18.py`
Output: `docs/v5/grounding_initial18_debug/summary.json`

## 결과 요약

| 항목 | 값 |
|---|---|
| 평가 프레임 | 18 (9 path family × 2 initial frames) |
| bbox 예측 생성 | 18/18 |
| seed_coarse_agreement | 1.0 (방향 위치는 맞음) |
| seed_detection_agreement | 0.333 (실제 대상 인식은 33%) |

## 핵심 발견

**Pure HF Kosmos-2는 gray basket을 단 한 번도 명시적으로 "basket"으로 부르지 않았다.**

모델이 감지한 객체들:
- "white wall", "window"
- "gray air conditioner"
- "gray trash can", "white trash can"
- "chair", "table"

## per-frame 예측 캡션

| path_type | frame | 예측 캡션 (첫 60자) |
|---|---|---|
| center_straight | f0 | the center of the image, with the white wall and the window |
| center_straight | f2 | the center of the image, with the white wall and the window |
| center_left | f0 | the center of the image, with the gray air conditioner sitti |
| center_left | f2 | the bottom of the image. The white wall is behind it. A wind |
| center_right | f0 | the center of the image, with the white wall and the window |
| center_right | f2 | the end of the room, with a chair and a table in the backgro |
| left_straight | f0 | the end of the room, and the chair is in the middle of the i |
| left_straight | f2 | the end of the room, and the gray trash can is in the middle |
| left_left | f0 | the far left of the image. The white wall is the background. |
| left_left | f2 | the bottom of the image, and the white trash can is in the m |
| left_right | f0 | the far end of the room, and the gray trash can is in the mi |
| left_right | f2 | the left side of the image, and the white wall is at right. |
| right_straight | f0 | the end of the room, and the white wall is behind it. |
| right_straight | f2 | the center of the image, with a chair and a desk in the back |
| right_left | f0 | the bottom of the image, and the gray trash can is at the to |
| right_left | f2 | the bottom of the image, and the white wall is behind it. |
| right_right | f0 | the far right of the image. The white wall is the background |
| right_right | f2 | the center of the image, with a chair and a table in the bac |

## 해석

seed_coarse_agreement=1.0 의미: 모델이 감지한 어떤 entity의 bbox 중심이 실제 basket의 coarse 방향(left/center/right)과 일치하는 경우가 많음 → 위치는 비슷하지만 다른 객체(trash can, wall)로 잘못 부르고 있음.

seed_detection_agreement=0.333 의미: 6개 seed 프레임 중 2개만 올바른 detection.

## 교수님 피드백 대응

- 교수님 질문: "객체를 인식하는지 안하는지 정확한 근거가 없다"
- 현재 답변: **현재 Pure HF Kosmos-2는 gray basket을 basket으로 인식하지 못함**
  - basket 대신 "trash can", "air conditioner" 등 비슷하게 생긴 회색 원통형 물체로 감지
  - 위치 자체는 (seed_coarse_agreement=1.0) 어느 정도 맞음
  - 즉: "위치는 보고 있지만 이름을 모른다"

## 다음 단계

1. prompt를 "gray basket" 명시로 변경하여 grounding 재실행 (현재는 자유 캡션)
2. Exp10 grounding 모델 (bbox IoU 0.87)과 비교 — 그건 prompted grounding이었음
3. 교수 미팅에서: "perception이 약하지만 bbox 위치는 살아있음, 문제는 action commitment"로 보고

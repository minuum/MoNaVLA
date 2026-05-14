# Plan — Exp49 실로봇 평가 프로토콜

작성: 2026-05-15  
브랜치: `monavla-driving`

---

## 0. 한 줄 목표

Exp49(GoalNav MLP)의 오프라인 CL 96.7%가 실로봇 환경에서도 재현되는지 확인한다.

---

## 1. 배경

| 항목 | 값 |
|------|-----|
| 모델 | Exp49 GoalNav MLP (d_in=1059, bbox+vision+goal) |
| 오프라인 val acc | 96.4% (bootstrap CI: [94.7%, 97.9%]) |
| 오프라인 CL 성공 | 96.7% (9개 path type 전부 포함) |
| 서버 상태 | VLA_MODEL=exp49, port 8001, 실행 중 |
| 이전 기록 | Exp14 Step2 66.7%, Exp25(end-to-end) 55.6% |

---

## 2. 테스트 구성

### 2.1 필수 Path Type (9가지 × 최소 2회)

| Path Type | 시작 위치 | 목표 | 성공 기준 |
|-----------|----------|------|---------|
| center_straight | 바스켓 정면 중앙 | 직진 | 바스켓 도달, 편차 < 0.4m |
| center_left | 바스켓 정면 중앙 | 왼쪽 회전 후 도달 | 바스켓 도달 |
| center_right | 바스켓 정면 중앙 | 오른쪽 회전 후 도달 | 바스켓 도달 |
| left_straight | 바스켓 왼쪽 | 정렬 후 직진 | 바스켓 도달 |
| left_left | 바스켓 왼쪽 | 왼쪽 곡선 | 바스켓 도달 |
| left_right | 바스켓 왼쪽 | 오른쪽 회전 경유 | 바스켓 도달 |
| right_straight | 바스켓 오른쪽 | 정렬 후 직진 | 바스켓 도달 |
| right_left | 바스켓 오른쪽 | 왼쪽 회전 경유 | 바스켓 도달 |
| right_right | 바스켓 오른쪽 | 오른쪽 곡선 | 바스켓 도달 |

총 최소 18회, 목표 27회(각 3회).

### 2.2 우선 확인 (10분 사전 체크)

```bash
# 서버 상태 확인
curl http://100.85.118.58:8001/health
# 기대: {"status":"healthy","model_name":"exp49",...}

# grounding 동작 확인 (단일 이미지)
# Gradio 대시보드 http://100.85.118.58:7860 에서 이미지 1장 전송 → bbox 표시 확인
```

---

## 3. 실행 절차

### Step 1 — 서버 확인 (로봇 켜기 전)
```bash
# soda 서버에서
curl http://localhost:8001/health | python3 -m json.tool
# model_name이 exp49인지 확인
# model_loaded가 false이면 첫 요청 시 자동 로드 (30초 대기)
```

### Step 2 — Gradio 세션 eval로 사전 체크
```bash
# 로봇 실행 전, 오늘 수집된 최근 H5 에피소드로 세션 평가
python3 scripts/gradio_session_eval.py --port 7861
# 브라우저: http://100.85.118.58:7861
# → grounding_success_rate 확인 (< 50% 이면 조명/바스켓 위치 조정)
```

### Step 3 — 로봇 실행
```bash
# ROS2 launch
cd ROS_action
source /opt/ros/humble/setup.bash
# (기존 launch 명령어 사용)
```

### Step 4 — 결과 기록

각 시도마다 기록:
- 시작 위치(path_type)
- 성공 여부 (바스켓 도달 O/X)
- 실패 원인 (방향 오류 / 조기 정지 / 충돌)
- 육안 관찰: 방향 전환이 자연스러운가

---

## 4. 기록 양식

```json
{
  "date": "2026-05-15",
  "model": "exp49",
  "server": "soda@100.85.118.58:8001",
  "trials": [
    {
      "trial_id": 1,
      "path_type": "center_straight",
      "success": true,
      "failure_reason": null,
      "notes": ""
    }
  ]
}
```

저장 위치: `docs/v5/eval/real_robot_exp49_YYYYMMDD.json`

---

## 5. 성공 기준

| 지표 | 기준 |
|------|------|
| 전체 성공률 | ≥ 80% (오프라인 96.7%의 ±20% 허용) |
| center_straight | ≥ 1/2 성공 |
| 곡선 경로 | ≥ 1/2 성공 |
| straight+rot | ≥ 1/2 성공 |

오프라인과 실로봇 차이(sim-to-real gap)가 > 20%p 이면 원인 분석 필요.

---

## 6. 실패 시 대응

| 증상 | 원인 후보 | 대응 |
|------|----------|------|
| 항상 FORWARD | grounding 실패 (bbox 없음) | 조명 조정, 바스켓 위치 변경 |
| 방향 반대 | 카메라 좌우 반전? | goal cx0 = 1-cx 로 테스트 |
| 초반 정상, 후반 드리프트 | 시간차 오류 누적 | step 수 줄이기 |
| 완전 정지 | STOP 클래스 과예측 | goal area 점검 |

---

## 7. 체크리스트

- [ ] 서버 health 응답 model_name=exp49 확인
- [ ] Gradio 세션 eval로 데이터 품질 사전 점검
- [ ] 9개 path type × 2회 이상 실시
- [ ] 결과 JSON 저장
- [ ] 오프라인 CL과 비교 분석
- [ ] 실패 원인 분류 기록

# 🏷️ BBox 수동 검수 도구 — 사용 가이드

> **목적**: MoNaVLA의 visual grounding 실패가 "데이터 품질 문제"인지 "모델 정책(policy) 실패"인지 구분하기 위한 인간 검수 파이프라인

---

## 왜 이 도구가 필요한가?

```
모델이 바구니를 못 찾음
      ↓
원인 1: GT 데이터 자체가 틀림 (bbox_xyxy_norm 이상, visible 잘못 표기)
원인 2: 모델이 이미지를 보고도 인식 실패 (policy/perception 문제)
      ↓
이 둘을 분리하지 않으면 → 어떤 학습 실험도 의미 없음
      ↓
해결: 사람이 직접 72개 frame을 눈으로 보고 GT 진실을 확정
```

---

## 1. 서버 실행

```bash
# MoNaVLA 루트에서
python3 scripts/label/bbox_labeler.py
```

| 상황 | 결과 |
|------|------|
| 첫 실행 | `http://localhost:7788` 서버 시작 |
| 이미 실행 중 | 안내만 출력하고 종료 (서버는 유지됨) |
| 강제 재시작 | `kill $(lsof -ti:7788)` 후 재실행 |

### 맥북에서 접근 (SSH 터널)
```bash
# 맥에서 실행
ssh -L 7788:localhost:7788 billy@<서버IP> -N
# 그 후 맥 브라우저에서 → http://localhost:7788
```

---

## 2. 화면 구성

```
┌─────────────────────────────────────────────────────────┐
│  헤더: 진행률 바 | 완료N/72 | [이전] [건너뜀] [다음]        │
├──────────────────────────┬──────────────────────────────┤
│                          │  📋 프레임 정보 (메타)           │
│    이미지 뷰어            │  🎯 검수 항목 (4가지 라벨)       │
│    (클릭/드래그 BBox)     │  📝 notes                      │
│                          │  [💾 저장 후 다음]               │
│  [YOLO 자동탐지] [드래그] │                                │
│  [YOLO BBox 승인] [무시] │                                │
└──────────────────────────┴──────────────────────────────┘
```

---

## 3. 권장 검수 순서 (1프레임당 ~15초)

### STEP 1 — 이미지 훑어보기
이미지를 보고 **바구니가 보이는지** 먼저 판단.

### STEP 2 — `target_visible` 설정 ①
| 버튼 | 의미 | 사용 시점 |
|------|------|----------|
| ✅ **보임** | 바구니 전체/대부분 보임 | 명확히 식별 가능 |
| ❌ **안보임** | 바구니 없거나 완전히 가려짐 | 프레임 밖, 벽 뒤 |
| ⚠️ **일부만** | 테두리/일부만 프레임에 걸침 | 시야 가장자리 |

### STEP 3 — `coarse_position` 설정 ②
화면을 3등분했을 때 바구니가 어느 쪽?

```
|  LEFT  |  CENTER  |  RIGHT  |
|   ~33% |  33~66%  |  66%~   |
```
→ `target_visible = false`이면 **없음** 선택

### STEP 4 — `goal_near` 설정 ③
"로봇이 지금 당장 멈춰도 될 만큼 바구니에 충분히 가까운가?"

| 버튼 | 기준 |
|------|------|
| ✅ **근접** | 바구니가 화면의 40% 이상 차지하거나 거의 정면 |
| ❌ **멀리** | 바구니는 보이지만 아직 이동 필요 |
| ❓ **모름** | 판단 불가 |

### STEP 5 — BBox 그리기 ④ (두 가지 방법)

#### 방법 A: YOLO 자동탐지 (권장, 빠름)
```
1. [🤖 YOLO 자동 탐지] 클릭
2. 노란 박스가 바구니 위에 표시됨 → [✅ YOLO BBox 승인]
3. 바구니와 맞지 않으면 → [❌ 무시] 후 방법 B 사용
```
> 💡 YOLO는 COCO 데이터셋 기준 → 바구니 전용 클래스 없음.
> `conf=0.15` (낮은 임계값)으로 "면적 가장 큰 객체"를 대표로 선택.
> 승인된 이미지는 `data/labeled_frames/`에 자동 저장.

#### 방법 B: 직접 드래그
```
1. [🖊️ 드래그] 버튼 클릭 → 커서가 십자선으로 변경
2. 이미지 위에서 바구니 좌상단 → 우하단 드래그
3. 초록 박스 = 최종 BBox
```

#### 방법 C: 직접 입력
- x1(left), y1(top), x2(right), y2(bottom) 값을 0.0~1.0으로 직접 입력

### STEP 6 — 저장
- `[💾 저장 후 다음]` 클릭 또는 `Enter` 키
- 자동으로 다음 `pending` 프레임으로 이동

---

## 4. 키보드 단축키

| 키 | 동작 |
|----|------|
| `Enter` | 저장 후 다음 |
| `→` | 다음 프레임 (저장 없이 이동) |
| `←` | 이전 프레임 |
| `s` | 건너뜀 (skip) |

---

## 5. 사이드바 프레임 정보 해석

| 필드 | 의미 |
|------|------|
| **인덱스** | 현재 프레임 번호 (예: 1/72) |
| **상태** | `pending`(미검수) / `done`(완료) / `skip`(건너뜀) |
| **에피소드** | 로봇 주행 에피소드 이름 |
| **anchor** | 에피소드 내 시간대 (`early`=초반, `mid`=중반, `late`=후반) |
| **진행도** | 0~1, 에피소드 내 위치 (0.15 = 15% 지점) |
| **GT 액션** | 그라운드트루스 행동 (`FWD`/`LEFT`/`RIGHT`/`STOP`) |
| **seed BBox** | 원본 데이터에서 가져온 초기 BBox (참고용, 틀릴 수 있음) |

---

## 6. 서버 상태 모니터링

```bash
# 브라우저에서 JSON으로 확인
http://localhost:7788/api/status   # 전체 요약
http://localhost:7788/api/logs     # 최근 100줄 로그
http://localhost:7788/api/export   # 완료된 항목만 추출

# 터미널에서
curl -s http://localhost:7788/api/status | python3 -m json.tool
```

---

## 7. 판단 기준 요약표 (빠른 참조)

```
바구니 선명하게 정중앙에 있음
  → visible=true / coarse=center / goal_near은 크기 보고 판단 / YOLO 탐지 승인

바구니가 왼쪽 가장자리에 조금만 보임
  → visible=partial / coarse=left / goal_near=false / 직접 BBox 드래그

바구니 없음 (복도, 다른 방)
  → visible=false / coarse=없음 / goal_near=false / BBox 비워두기

GT 액션이 STOP인데 바구니가 아직 멀리 있음
  → 데이터 품질 의심 → notes에 "GT_STOP_TOO_EARLY" 기록

YOLO가 바구니 대신 다른 물체 탐지
  → 탐지 결과 cls_name 확인 (하단에 표시) → 무시 후 직접 드래그
```

---

## 8. 결과 데이터 구조

검수 완료 후 `docs/v5/bbox_truth_mini.json` 업데이트:

```json
{
  "episode": "episode_260408_...",
  "frame_idx": 2,
  "anchor_tag": "early",
  "target_visible": true,          ← 사람이 검수한 값
  "bbox_xyxy_norm": [0.3, 0.4, 0.6, 0.7],  ← 정규화 좌표
  "coarse_position": "center",
  "goal_near": false,
  "review_status": "done",
  "notes": "[YOLO-assisted]"
}
```

---

## 9. 저장 위치

| 종류 | 경로 |
|------|------|
| 검수 결과 JSON | `docs/v5/bbox_truth_mini.json` |
| YOLO 탐지 이미지 | `data/labeled_frames/episode_..._yolo.jpg` |
| 서버 로그 | `logs/labeler/bbox_labeler_YYYYMMDD_HHMMSS.log` |

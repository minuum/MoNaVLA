# MoNaVLA 현황 분석 및 차기 TODO (2026-04-11)

> 교수님 미팅록(3/13, 3/20, 3/27) + Exp01~04 결과를 종합한 현황 점검.

---

## 1. 교수님 지시 사항 요약 (3/27 미팅 기준)

### 검증 순서 (3단계 테스트 프로토콜)
교수님이 명시적으로 지시한 실험 순서:

```
Step 1: 곡선 데이터만으로 학습 → 직선 이미지를 줘도 곡선으로 가는가?
         ↓ 성공하면
Step 2: 50/50 비율 (직선:곡선 = 1:1) → 비율이 맞을 때 동작하는가?
         ↓ 성공하면
Step 3: T3 테스트 (좌/우 각각) → 33/33/33 비율에서 Left/Right 정상 출력?
         ↓ 실패하면 (Step 1부터)
⚠️ "학습 코드 자체가 설계가 잘못된 거예요" → TICVLA/MobilityVLA 대안 검토
```

### 핵심 진단 (교수님 진단)
1. **1차 원인: 데이터 분포** — 학습 데이터 75%가 FORWARD → 모델이 "소리를 들으면 앞으로 가"를 배운 것
2. **2차 원인: 이미지-텍스트 시맨틱 미매칭** — "왼쪽에 있다"는 의미를 모델이 이해 못 함. VLM은 객체 인식은 하나 액션과의 연결을 학습하지 못함
3. **최후 수단**: 위 둘을 해결해도 안 되면 TICVLA(모바일용 VLA, 강화학습) 또는 MobilityVLA 참고

---

## 2. 현재 실험 결과 vs. 교수님 요구사항 대조

### Exp01~04 결과 요약

| 실험 | 설정 | val_loss | 교수님 요구 매핑 | 상태 |
|------|------|----------|-----------------|------|
| **Exp01** | 전체 데이터 (직선 포함), V4 체크포인트 기반 | 2.270 | Step 1 실패 예상 — 직선 75% 그대로 | PM 68% (FORWARD 100%) |
| **Exp02** | 직선 제거, left/right만 30ep, V4 기반 | 2.210 | **Step 1 부분 수행** — FORWARD 제거는 맞는 방향 | PM 50% (일부 개선) |
| **Exp03** | Exp02 + CLIP Norm Loss | 1.784 | Step 1 + 추가 제약 | PM 미측정 |
| **Exp04** | 직선 제거, Google-robot 기반 | **0.776** | **Step 1 가장 근접** — 기반 모델 교체로 급락 | PM 미측정 |

### 핵심 발견: Exp04가 왜 그렇게 다른가?

**Exp01~03 vs Exp04의 근본 차이:**

```
Exp01~03:
  기반 체크포인트 = V4 regression (continuous action 학습됨)
  → image_to_text_projection이 action feature로 오염됨
  → 이미 잘못된 vision→text 매핑 위에 분류 학습
  → val_loss 2.2~2.3 (높음)

Exp04:
  기반 체크포인트 = Google-robot pretrained (navigation pre-training)
  → image_to_text_projection이 더 깨끗한 상태
  → load_vlm_only=true → act_head는 scratch 초기화
  → 더 나은 기반 위에서 분류 학습
  → val_loss 0.776 (급락)
```

**Exp04의 의미**: `image_to_text_projection` 오염 문제가 실제로 학습에 영향을 주고 있음을 간접 증명. Google-robot 사전학습 체크포인트가 V4 regression보다 훨씬 나은 출발점.

---

## 3. 현재 상황 핵심 문제 트리

```
FORWARD Bias (모든 실험 공통)
├── A. 데이터 분포 문제 (직선 75% → 교수님 진단 #1)
│   ├── [해결 시도] Exp02: 직선 제거 → val_loss 2.210 (개선 미미)
│   ├── [해결 시도] Exp04: 직선 제거 + Google 기반 → val_loss 0.776 (큰 개선)
│   └── [미완] PM/DM 오프라인 테스트 미실행 (Exp03, Exp04)
│
├── B. 시맨틱 미매칭 (교수님 진단 #2)
│   ├── VLM은 gray basket을 인식함 (grounding 실험으로 확인)
│   ├── 하지만 "basket이 왼쪽 → 왼쪽으로 가야 함"의 인과관계 미학습
│   └── [해결 시도] CLIP Norm Loss (Exp03) → val_loss 1.784 (개선됨, PM 미측정)
│
├── C. 기반 모델 오염 (새로 발견)
│   ├── V4 regression → image_to_text_projection 오염
│   ├── Exp04로 검증: Google-robot 기반이 훨씬 유리
│   └── [미완] 실제 주행 테스트 미실행
│
└── D. 데이터 양 부족
    ├── left/right 에피소드: 각 15개 (총 30개)
    ├── 교수님 목표: 최소 150~180 에피소드
    └── [미완] 추가 수집 필요
```

---

## 4. Exp04가 정말 "학습이 됐는가"에 대한 의문

val_loss 0.776은 놀라운 수치지만 **진짜 곡선을 학습했는지는 PM/DM 테스트로만 알 수 있다.**

교수님 질문 그대로: "곡선 데이터만 학습시키면 직선 이미지를 줘도 곡선으로 가는가?"

- Exp02/Exp04 설정: 직선 제거 + 곡선만 학습 = 교수님 Step 1 조건에 근접
- **아직 이 조건에서 PM 테스트가 없음**
- val_loss 하락이 진짜 곡선 학습인지, 아니면 단순히 다른 클래스로 bias가 이동했는지 미확인

---

## 5. 세부 TODO 목록

### 🔴 CRITICAL — 즉시 실행 (이번 주)

#### TODO-1: Exp03, Exp04 PM/DM 오프라인 테스트
**목적**: 교수님 Step 1 확인 — 곡선 데이터 학습 시 실제로 곡선 행동이 나오는가?

```bash
# Exp04 best checkpoint로 PM/DM 테스트
python3 scripts/test_v5_pm_dm.py \
  --config configs/mobile_vla_v5_exp04_google_robot.json \
  --checkpoint runs/v5_nav/kosmos/mobile_vla_v5_exp04/2026-04-11/v5-exp04-google-robot/epoch_epoch=epoch=14-val_loss=val_loss=0.776.ckpt
```

**확인 포인트:**
- FORWARD 출력 비율이 Exp01(100%)보다 낮아졌는가?
- FWD+L, FWD+R 클래스가 실제로 나오는가?
- PM이 Exp01(68.18%)보다 높아졌는가?

**판정 기준 (교수님 지시 기반):**
- ✅ FWD+L/FWD+R 출력 > 0% → "곡선 이해 가능성 있음" → Step 2로 진행
- ❌ FORWARD 100% 여전히 → "학습 코드 설계 문제" → 근본 점검 필요

---

#### TODO-2: Exp04 실제 로봇 주행 테스트 (가장 좋은 체크포인트)
**목적**: 오프라인 PM이 통과되면, 실환경에서 곡선 주행이 나오는지 확인

**절차:**
1. `inference_server.py`의 기본 체크포인트를 Exp04로 설정
2. Jetson에서 left_path 에피소드 실행 → 실제 좌회전 나오는가?
3. 교수님 관찰: "T3을 해도 그냥 스트레이트"가 개선되었는가?

**inference_server.py 설정:**
```python
# robovlm_nav/serve/inference_server.py 에서
DEFAULT_CHECKPOINT = "runs/v5_nav/kosmos/mobile_vla_v5_exp04/2026-04-11/v5-exp04-google-robot/epoch_epoch=epoch=14-val_loss=val_loss=0.776.ckpt"
DEFAULT_CONFIG = "configs/mobile_vla_v5_exp04_google_robot.json"
```

---

#### TODO-3: 추가 데이터 수집 (left/right 각 30→50ep)
**목적**: 현재 left 15개, right 15개 = 총 30개. 최소 50개/class(총 100개) 필요

**수집 우선순위:**
1. `right_path` 에피소드 추가 (현재 15개 → 목표 30개)
2. `left_path` 에피소드 추가 (현재 15개 → 목표 30개)
3. `target_left_straight_path` 추가 (현재 4개 → 최소 10개)

**수집 시 주의사항:**
- 교수님 지시: "Fixed Path 9개" 형태 유지
- 각 경로의 출발 지점, 초기 방향 고정
- 프롬프트: `"Navigate toward the gray basket until it gets closer"` 통일

---

### 🟡 HIGH — 이번 주 내 (실험 결과에 따라)

#### TODO-4: Exp02 best ckpt vs Exp04 best ckpt 직접 비교 분석
**목적**: Google-robot 기반 vs V4 기반의 차이를 정량화

```
비교 메트릭:
- val_loss: 2.210 vs 0.776 (Exp04 압도)
- PM (FWD+L, FWD+R 클래스): ??? vs ???
- 혼동 행렬 패턴 비교
- 곡선 클래스 precision/recall 비교
```

**기대 결과**: Exp04의 낮은 val_loss가 실제 곡선 분류 능력 향상으로 이어지는지 확인

---

#### TODO-5: Exp05 설계 — "곡선 전용 + Google-robot + 더 많은 데이터"
**목적**: TODO-1~4 결과를 반영한 최적 설정 실험

**설정 방향:**
```json
{
  "base": "configs/mobile_vla_v5_exp04_google_robot.json",
  "데이터": "left+right 100ep (추가 수집 후)",
  "class_weights": "[5.0, 0.1, 5.0, 5.0, 3.0, 3.0]",  // FORWARD 극단 억제
  "max_epochs": 50,
  "early_stopping patience": 10
}
```

**교수님 Step 2 매핑**: 곡선 데이터만으로 학습이 확인된 후, 직선 포함 50/50 비율 실험

---

#### TODO-6: `test_v5_pm_dm.py` 스크립트 Exp03/04 호환성 확인
**목적**: 기존 PM/DM 테스트 스크립트가 새 config 형식(부모-자식 JSON 상속)을 지원하는지 확인

**확인 포인트:**
- `model_load_source: "torch"` + `load_vlm_only: true` 설정 처리
- `pretrained_vlm_path` 로드 경로 (Exp04는 Google-robot 체크포인트)
- stratified_split + exclude_path_types 파라미터 처리

---

### 🟢 MEDIUM — 다음 주

#### TODO-7: Exp04 학습 계속 실행 (현재 epoch=14에서 멈춤)
**목적**: val_loss 0.776에서 더 개선 가능한지 탐색

```bash
# Exp04 last.ckpt에서 resume
python3 robovlm_nav/train.py \
  --config configs/mobile_vla_v5_exp04_google_robot.json \
  --resume runs/v5_nav/kosmos/mobile_vla_v5_exp04/2026-04-11/v5-exp04-google-robot/last.ckpt
```

**단, TODO-1 PM 테스트 결과를 보고 진행 여부 결정**

---

#### TODO-8: Google-robot 체크포인트 기반 이해 심화
**목적**: 왜 Google-robot이 V4 regression보다 훨씬 나은지 이론 확인

**조사 항목:**
1. Google-robot 사전학습 데이터: navigation 관련 데이터 포함 여부
2. `image_to_text_projection` 가중치 비교 (V4 체크포인트 vs Google-robot)
3. `load_vlm_only=true`로 act_head scratch 초기화 시 초기 수렴 속도 차이

---

#### TODO-9: V5 데이터 품질 검증 (BBox-Centric)
**목적**: 수집된 150ep의 BBox 수렴 패턴 전수 확인

**교수님 요구 (3/27 이전 미팅):**
- "바스켓이 중앙으로 이동 → BBox도 함께 중앙으로 이동해야 함"
- 이 패턴이 안 나오면 데이터 자체가 잘못된 것

**작업:**
1. `v5_grounding.json` 로드
2. 에피소드별 BBox x-center trajectory 플롯
3. 에피소드 말미에 BBox가 0.4~0.6 범위로 수렴하는지 확인
4. 이상 에피소드 태깅 → 재수집 대상 목록 작성

---

#### TODO-10: 교수님 보고 자료 업데이트
**목적**: 다음 미팅 전 현황 정리

**포함 내용:**
1. Exp01~04 비교 표 (val_loss + PM + DM)
2. Exp04 실제 주행 결과 영상 (TODO-2 결과)
3. 교수님 Step 1 통과 여부 명시
4. 데이터 추가 수집 계획 및 현황

---

## 6. 의사결정 트리 (이후 방향)

```
TODO-1: Exp04 PM/DM 테스트
│
├── ✅ FWD+L/FWD+R 출력 있음 (교수님 Step 1 통과)
│   ├── TODO-2: 실제 주행 테스트
│   │   ├── ✅ 곡선 주행 확인 → TODO-5: Exp05 (50/50 비율)
│   │   └── ❌ 실제 주행 안 됨 → 추론 설정 디버깅 (inference_server.py)
│   └── TODO-3: 데이터 추가 수집 병행
│
└── ❌ FORWARD 100% 여전히 (교수님 Step 1 실패)
    ├── 학습 코드 근본 점검:
    │   - loss function 재검토 (cross-entropy가 FORWARD에 collapse하는 이유)
    │   - 레이블 매핑 버그 재확인
    │   - act_head 출력 분포 직접 확인 (softmax 이전 logit 분포)
    └── 교수님 최후 수단:
        - TICVLA (모바일용 VLA, RL 기반) 검토
        - MobilityVLA 참고 코드 검토
```

---

## 7. 지금 당장 실행할 수 있는 명령어 목록

```bash
# [1] Exp04 PM/DM 테스트 (최우선)
python3 scripts/test_v5_pm_dm.py \
  --config configs/mobile_vla_v5_exp04_google_robot.json \
  --checkpoint "runs/v5_nav/kosmos/mobile_vla_v5_exp04/2026-04-11/v5-exp04-google-robot/epoch_epoch=epoch=14-val_loss=val_loss=0.776.ckpt" \
  2>&1 | tee /tmp/exp04_pm_dm_result.txt

# [2] Exp03 PM/DM 테스트 (비교용)
python3 scripts/test_v5_pm_dm.py \
  --config configs/mobile_vla_v5_exp03_clip_norm.json \
  --checkpoint "runs/v5_nav/kosmos/mobile_vla_v5_exp03/2026-04-10/v5-exp03-clip-norm/epoch_epoch=epoch=14-val_loss=val_loss=1.784.ckpt" \
  2>&1 | tee /tmp/exp03_pm_dm_result.txt

# [3] Exp04 inference 서버 시작 (실제 주행 테스트용)
python3 robovlm_nav/serve/inference_server.py \
  --config configs/mobile_vla_v5_exp04_google_robot.json \
  --checkpoint "runs/v5_nav/kosmos/mobile_vla_v5_exp04/2026-04-11/v5-exp04-google-robot/epoch_epoch=epoch=14-val_loss=val_loss=0.776.ckpt"
```

---

## 8. 판단 근거가 되는 핵심 숫자들

| 지표 | Exp01 | Exp02 | Exp03 | Exp04 |
|------|-------|-------|-------|-------|
| val_loss (best) | 2.270 | 2.210 | 1.784 | **0.776** |
| best epoch | 5 | 5 | 14 | **14** |
| 기반 체크포인트 | V4 regression | V4 regression | Exp02 best | **Google-robot** |
| 직선 데이터 포함 | ✅ | ❌ | ❌ | ❌ |
| stratified split | ❌ | ✅ | ✅ | ✅ |
| CLIP Norm Loss | ❌ | ❌ | ✅ | ❌ |
| PM (FORWARD%) | 68% (F 100%) | 50% (일부 개선) | **미측정** | **미측정** |
| 실 주행 테스트 | ❌ | ❌ | ❌ | ❌ |

**핵심**: Exp04 val_loss 0.776은 Exp01(2.270)의 34% 수준. 이것이 진짜 곡선 분류 능력인지 확인이 최우선.

---

*작성: 2026-04-11, 교수님 미팅록(3/13, 3/20, 3/27) + Exp01~04 실험 결과 종합*

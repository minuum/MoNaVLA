# V5 PM (Perfect Match) 계산 방식 — Methodology

**작성일**: 2026-04-18
**목적**: 여러 스크립트/실험에서 서로 다르게 계산된 PM 수치의 정확한 정의, 분모 차이, 비교 시 주의사항을 한 곳에 정리한다.

---

## 1. 한 줄 정의

```
PM (Perfect Match) = (pred_class == gt_class) 프레임 수 / 전체 프레임 수
```

즉 **discrete action class 단위 정확한 일치 비율**. Regression error나 distance 기반이 아닌 **exact match**.

---

## 2. 공통 계산 흐름

모든 V5 PM 평가는 기본적으로 아래 pseudo-code를 공유한다.

```python
for each frame (or window):
    pred_class = argmax(model_logits)          # discrete class 예측
    gt_class   = parse_gt(batch)               # 데이터셋의 정답 class
    total += 1
    if pred_class == gt_class:
        correct += 1

PM = correct / total
```

- `pred_class`: 8-class 또는 6-class discrete action (0=STOP, 1=FORWARD, 2=LEFT, 3=RIGHT, 4=FWD+L, 5=FWD+R, 6=ROT_L, 7=ROT_R)
- `gt_class`: H5 에피소드의 프레임별 action을 discrete class로 매핑한 값 (`frames[t]["gt_class"]` 또는 `action_chunck[0, t, 0]`)

---

## 3. 현재 사용 중인 PM Variant

| Variant | 스크립트 | 분자 (correct) | 분모 (total) | 전형적 수치 |
|:---|:---|:---|:---|:---:|
| **VLA PM (offline, full val)** | [`test_v5_pm_dm.py`](../../scripts/test_v5_pm_dm.py) | 각 window의 `eval_t` 위치 예측과 GT 비교 | 전체 val dataset windows | Exp04: 0%, Exp11: 58.6% |
| **VLA PM (val subset, only_exp11_valid)** | [`compare_exp11_step2_same_split.py`](../../scripts/compare_exp11_step2_same_split.py) | NavDataset의 valid window 추론 | `window_size=8`, `fwd_pred_next_n=5` 제약 통과한 subset 50개 | Exp11: 50%, Step 2: 50% |
| **BBox Step 0 (rule)** | [`test_v5_bbox_nav_step0.py`](../../scripts/test_v5_bbox_nav_step0.py) | bbox 기반 rule이 예측 → GT와 비교 | 9 epi × 10 frame = 90 (첫/중/끝 프레임만) | 31.1% |
| **BBox Step 0-B (Exp10 ckpt + rule)** | [`test_v5_bbox_nav_step0b.py`](../../scripts/test_v5_bbox_nav_step0b.py) | Exp10 grounding ckpt로 bbox 예측 후 rule | 90 frames | 34.4% |
| **BBox Step 0-C (tuned rule)** | [`test_v5_bbox_nav_step0.py`](../../scripts/test_v5_bbox_nav_step0.py) *(tune 옵션)* | rule 경계값 튜닝 후 rule 예측 | 90 frames | 64.4% |
| **BBox Step 1 (bbox MLP)** | [`test_v5_bbox_nav_step1.py`](../../scripts/test_v5_bbox_nav_step1.py) | bbox history(3 frames)만 MLP | test set 158 frames (stratified 80/20, 9 paths) | 68.4% |
| **BBox Step 2 (bbox + 16x16 gray)** | [`test_v5_bbox_nav_step2.py`](../../scripts/test_v5_bbox_nav_step2.py) | bbox history + 16×16 grayscale feature | test set 158 frames | **75.9%** (mean 76.6%±1.6%, 5 seed) |
| **Step 2 Quick Repro** | [`recheck_v5_bbox_nav_step2_seeds.py`](../../scripts/recheck_v5_bbox_nav_step2_seeds.py) | 위와 동일 스크립트, 5 split seed × 8 epoch | 각 seed의 test set (158~159) | 74.8~79.1% |
| **Exp11 same-subset vs Step 2** | [`compare_exp11_step2_same_split.py`](../../scripts/compare_exp11_step2_same_split.py) | 공통 valid window에서 양쪽 모두 추론 | **50개** (공통 subset) | Exp11 50% / Step 2 50% |

---

## 4. 분모(total)가 다른 이유

같은 "75.9% Step 2" 수치라도 분모가 달라 **직접 비교하면 오독**할 수 있다.

### 4.1 Full frame (BBox nav)

BBox 계열 Step 1/2는 에피소드의 **거의 모든 프레임**을 평가 대상으로 삼는다. `bbox_dataset.json` 생성 단계에서 grounding 가능한 프레임만 필터링하기 때문에 실제로 158 frames 정도.

- 대상: 9 path × ~4~5 epi × 프레임 전체 (처음~끝)
- 장점: 에피소드 중반/후반의 "바구니가 크게 보이는 구간"도 포함 → 높은 PM
- 단점: 각 path의 frame 수가 다르면 path 가중치가 불균등

### 4.2 only_exp11_valid subset (same-split 비교)

Exp11은 `window_size=8`, `fwd_pred_next_n=5` 제약이 있어, 에피소드의 앞 `len - 12` 프레임까지만 valid window를 만들 수 있다. 즉 **에피소드 초반 중심**.

- 대상: 9 path × 평균 5~6 frames = 50 frames
- 장점: Exp11/Step 2를 동일 프레임에서 직접 비교 가능
- 단점: 에피소드 초반은 바구니가 멀고 bbox 신호 약함 → Step 2에 불리

### 4.3 VLA offline PM (window 전체)

`test_v5_pm_dm.py`는 NavDataset의 전체 val window를 대상. BBox nav의 `bbox_dataset.json`과 분모가 다름.

---

## 5. 해석 시 주의

1. **"Step 2 75.9% > Exp11 58.6%"** → **full val**에서만 성립. same-subset에서는 50%=50%.
2. **PM 향상이 유의미한가**: 재현성 ±1.6% (5 seed) 이내 변동은 "noise". 3%p 이상 차이가 보수적 유의 기준.
3. **Path-type별 분리 필요**: FORWARD가 47% 차지하므로, "FORWARD만 100% 맞추면 PM 47%". 좌우(LEFT/RIGHT/FWD+L/FWD+R)별 per-path PM을 항상 함께 본다.
4. **eval_t 차이**: VLA 모델은 `eval_t=0`(window 시작) 기본. 과거 보고된 수치가 `eval_t=-1`로 측정됐으면 직접 비교 불가.
5. **1-step TF vs N-step free-running**: 현재 모든 PM은 **1-step teacher-forced**. free-running rollout에서는 exposure bias로 PM이 더 낮아질 가능성.

---

## 6. Parse 함수 정의

```python
def parse_gt(batch, t=0):
    # batch["action_chunck"] shape: [batch, window_size, fwd_pred_next_n]
    ac = batch["action_chunck"].cpu().numpy()
    return int(ac[0, t, 0])          # 첫 번째 chunck step의 class


def parse_logits(outputs, t=0):
    # outputs shape (classification): (bs, window, fwd_pred, num_classes)
    arr = outputs.detach().cpu().float().numpy()
    if arr.ndim == 4:   logits = arr[0, t, 0, :]
    elif arr.ndim == 3: logits = arr[0, t, :]
    elif arr.ndim == 2: logits = arr[0, :]
    return int(np.argmax(logits)), logits
```

- `t=0`: window의 **첫 프레임** 예측 (기본). 실제 inference time 첫 스텝과 대응.
- `t=-1`: window의 **마지막 프레임**. history를 최대 활용한 예측. ROT는 이 위치에서 거의 나오지 않음.

V5에서는 모든 PM 측정을 `eval_t=0`으로 통일했다 (2026-04-16 버그 fix 이후).

---

## 7. DM (Deviation Match) — 현재 미사용

파일명에 `pm_dm`이 들어 있으나 **DM은 V5에서 계산되지 않는다**. V4 시절의 연속 action regression 평가에서 사용하던 지표이며, V5 discrete classification에서는 의미가 없어 제외됐다.

---

## 8. 향후 계획 (선택)

| 메트릭 | 동기 |
|:---|:---|
| **N-step free-running PM** | exposure bias 정량화 |
| **per-path F1** | class imbalance 영향 제거 |
| **closed-loop rollout PM** | 실제 제어 성능 연결 |
| **Grounded PM** (BBox IoU ≥ 0.5 인 프레임만 계산) | perception failure frame 제외 |

---

## 9. 참고 파일 요약

- VLA offline 평가: [scripts/test_v5_pm_dm.py](../../scripts/test_v5_pm_dm.py)
- BBox Step 시리즈: [scripts/test_v5_bbox_nav_step*.py](../../scripts/)
- 재현성 체크: [scripts/recheck_v5_bbox_nav_step2_seeds.py](../../scripts/recheck_v5_bbox_nav_step2_seeds.py)
- 공정 비교: [scripts/compare_exp11_step2_same_split.py](../../scripts/compare_exp11_step2_same_split.py)
- 결과 폴더: [docs/v5/bbox_nav_step*/](.) / [exp11_vs_step2_same_split*/](.)

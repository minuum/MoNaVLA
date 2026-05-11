# Plan: Exp51 — Crop Augmentation (카메라 위치 Robustness)
작성일: 2026-05-11

## 1. 목표

**현재 문제 (Exp50 결과):**
- crop_left10%: 22% / crop_right10%: 33% / crop_center90%: 11%
- flip augmentation은 flip 대칭(0→6/9)에는 효과, crop에는 무효

**달성 목표:**
- crop_left/right10% → ≥60%
- flip 대칭 6/9 → 유지
- val PM ≥90% (Exp50 92.0% 기준, 데이터 더 늘어나면 소폭 하락 가능)

---

## 2. 핵심 설계 결정

### 왜 오프라인 사전 추출인가?

Kosmos-2 vision_model 추론 속도: ~0.3s/프레임 → 학습 중 온라인 aug 불가  
→ Exp50과 동일하게 **augmented vision feature를 npz로 사전 저장**

### Augmentation 종류

| 이름 | 이미지 변환 | cx 변환 | cy/area |
|------|------------|---------|---------|
| `crop_left10%` | 왼쪽 10% 잘라내고 stretch | cx → max(0, cx-0.10) | 유지 |
| `crop_right10%` | 오른쪽 10% 잘라내고 stretch | cx → min(1, cx+0.10) | 유지 |

`crop_center90%`는 cx 변환이 없고 효과가 11%로 낮아 제외.

### 학습 데이터 구성

```
원본:          2626 프레임   (Exp46 캐시 재사용)
flip:          2626 프레임   (Exp50 캐시 재사용)
crop_left10%:  2626 프레임   (신규 추출)
crop_right10%: 2626 프레임   (신규 추출)
─────────────────────────────
합계:         10504 프레임
```

val은 원본만 (526 프레임) — Exp49/50과 동일 조건 비교.

### cx 변환 (bbox_history + goal 동시 적용)

```python
CROP_VARIANTS = {
    "crop_left10%":  {"dir": "left",  "ratio": 0.10, "cx_delta": -0.10},
    "crop_right10%": {"dir": "right", "ratio": 0.10, "cx_delta": +0.10},
}

# bbox_history 각 프레임:
cx_aug = np.clip(cx_orig + cx_delta, 0.0, 1.0)

# goal_cx0:
goal_cx_aug = np.clip(goal_cx0 + cx_delta, 0.0, 1.0)
```

action은 crop 시 변환 없음 (카메라 위치만 달라짐, 목표 행동은 동일).

---

## 3. 아키텍처

Exp49/50과 동일:
```
bbox_history(32) + vision(1024) + goal(3) = 1059-dim → MLP → 8-class
```
변경점: 학습 데이터 2626 → 10504 프레임 (4×)

---

## 4. 구현 단계

- [x] Step 1: crop vision feature 추출 (7.8분 총 소요)
      → `docs/v5/bbox_nav_exp51/crop_left10_vision_features.npz`
      → `docs/v5/bbox_nav_exp51/crop_right10_vision_features.npz`
- [x] Step 2: `scripts/train_v5_exp51_crop_aug.py` 작성 및 학습 (val acc 93.3%)
- [x] Step 3: PM 평가 완료
- [x] Step 4: robustness 재측정 (crop_left 22→78% ✅, crop_right 33→100% ✅, flip 6/9 유지)
- [ ] Step 5: 결과 문서화

---

## 5. 예상 결과

| 테스트 | Exp49 | Exp50 | Exp51 목표 |
|--------|-------|-------|-----------|
| val PM | 96.4% | 92.0% | ≥90% |
| crop_left10% | 22% | 22% | **≥60%** |
| crop_right10% | — | 33% | **≥60%** |
| flip 대칭 | 0/9 | 6/9 | 6/9 유지 |

---

## 6. 리스크

| 리스크 | 가능성 | 대응 |
|--------|--------|------|
| val PM 추가 하락 | 중간 | 4× 데이터로 혼합 신호 증가. 허용 범위 ≥88% |
| crop 여전히 낮음 | 낮음 | cx 변환을 bbox+goal 양쪽에 적용하므로 일관성 확보 |
| 추출 시간 과다 | 낮음 | 백그라운드 실행, 캐시 재사용 flag |

---
**승인 후 구현 시작.**

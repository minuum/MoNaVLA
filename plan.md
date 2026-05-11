# Plan: Exp50 — Flip Augmentation (기하 Robustness 개선)
작성일: 2026-05-11

## 1. 목표

**현재 문제:**
- Exp49: 조명/색상 89~100% ✅, 카메라 10% 이동 22% ❌
- 모델이 학습 때 본 시야각에 과적합됨

**달성 목표:**
- flip augmentation으로 거울 대칭 데이터 추가 → 카메라 위치 robustness 개선
- crop/shift 22% → 목표 ≥60%
- flip 대칭 action 반전율 0/9 → 목표 ≥7/9

## 2. 리서치 요약

### 2.1 flip 시 변환 규칙

| 항목 | 원본 | flip 후 |
|------|------|---------|
| image | 원본 | 좌우 반전 |
| cx | 0.35 | **0.65** (1-cx) |
| cy, area | 유지 | 유지 |
| action | LEFT(2) | **RIGHT(3)** |
| action | FWD+L(4) | **FWD+R(5)** |
| action | ROT_L(6) | **ROT_R(7)** |
| action | STOP/FORWARD | 유지 |
| goal_cx0 | 0.35 | **0.65** |
| vision feature | 원본 | **재추출 필요** (패치 내용 바뀜) |

### 2.2 데이터 변화

```
원본: 150 에피소드, 2626 프레임
flip: 150 에피소드, 2626 프레임 (거울상)
합계: 300 에피소드, 5252 프레임
```

flip 에피소드는 기존 path_type의 거울상 (`left_left` flip ≡ `right_right` 시나리오).
새 환경 데이터는 아니지만 Kosmos-2 vision encoder는 뒤집힌 이미지를 다르게 처리
→ 카메라 위치 불변성 학습에 유효.

### 2.3 작업 순서

1. **Flipped vision feature 추출** — 가장 비싼 작업 (Exp46 추출과 동일한 규모)
   - 150 에피소드 × 각 프레임 flip → Kosmos-2 vision encoder → `flipped_vision_features.npz`
2. **Flipped bbox 계산** — bbox_dataset_full.json에서 cx → 1-cx (빠름, 추가 grounding 불필요)
3. **MLP 학습** — 원본 + flip 합쳐서 Exp49와 동일한 구조로 학습
4. **평가** — PM, crop robustness, flip 대칭 검증

## 3. 아키텍처

Exp49와 동일:
```
bbox_history(32) + vision(1024) + goal(3) = 1059-dim → MLP → 8-class action
```

변경점: 학습 데이터만 2배 (원본 + flip)

## 4. 구현 단계

- [x] Step 1: flipped vision feature 추출 → `docs/v5/bbox_nav_exp50/flipped_vision_features.npz`
- [x] Step 2: `scripts/train_v5_exp50_flip_aug.py` 작성 및 학습
- [x] Step 3: PM 평가 (val acc 92.0%, -4.4%p vs Exp49)
- [x] Step 4: 이미지 robustness 재측정 (flip 0→6/9 ✅, crop 22% → 22~33% ❌)
- [ ] Step 5: 결과 문서화

## 5. 예상 결과

| 테스트 | Exp49 | Exp50 목표 |
|--------|-------|-----------|
| val PM | 96.4% | ≥95% (소폭 하락 가능) |
| crop 10% | 22% | **≥50%** |
| flip 대칭 | 0/9 | **≥7/9** |
| paraphrase | 100% | 100% 유지 |

## 6. 리스크

| 리스크 | 가능성 | 대응 |
|--------|--------|------|
| PM 소폭 하락 | 중간 | flip data가 거울상이라 mixed signal 가능 |
| flip 대칭 여전히 실패 | 낮음 | bbox_history도 flip하므로 일관성 확보 |
| vision feature 추출 오래 걸림 | 높음 | 백그라운드 실행 |

---
**승인 후 구현 시작.**

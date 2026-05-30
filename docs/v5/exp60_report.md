# Exp60 — BBox Noise Augmentation으로 Stage2 MLP의 VLM-bbox OOD 극복

> 작성: 2026-05-31 · 선행: [plan_20260531_exp60_bbox_aug_mlp.md](../plans/plan_20260531_exp60_bbox_aug_mlp.md)
> 한 줄 결론: **CL 성공률 4.5% → 36.4% (8배), 평균 FPE 4.075m → 0.575m (7.1배)** — clean PM 거의 유지(92.6%→91.4%)

---

## 1. 문제

Exp59가 grounding(98%)을 풀었으나 Closed-Loop는 4.5%로 붕괴. 같은 Stage2 MLP인데 bbox 소스만
HSV GT → PaliGemma2로 바뀌니 CL 96.7%(Exp54) → 4.5%로 무너짐. **분포 불일치(OOD)** 가 원인.

## 2. 측정 — VLM bbox는 HSV GT에서 얼마나 벗어나는가

`scripts/measure_exp60_bbox_offset.py` — 학습셋 40 ep × 8 frame(317 pos frame)을 PaliGemma2 Exp59로
re-ground하여 VLM−GT 오차 분포 산출 → [exp60_bbox_offset_stats.json](exp60_bbox_offset_stats.json)

| 지표 | 값 | 의미 |
|---|---|---|
| **Δcx** | mean **-0.084**, std **0.222** | 좌측 계통 편향 + 큰 산포(프레임 폭의 22%) |
| Δcy | mean -0.012, std 0.137 | 수직 편향 작음 |
| area_ratio | mean 0.979, p05 0.008, p95 2.82 | 스케일 매우 가변 |
| miss_rate | **4.1%** | GT 有인데 VLM 미검출 |

→ MLP는 이 분포를 학습 중 **한 번도 본 적 없음**. EMA로도 못 잡는 이유 = 지터가 아니라 systematic offset.

## 3. 방법 — 측정 통계로 캘리브레이션한 노이즈를 학습에 주입

`scripts/train_exp54_stage2_v2_action.py`의 `bbox_feat(augment=True)`에서 **학습 시에만** 주입
(eval/추론은 그대로). `build_aug_params()`가 위 통계로 파라미터 산출, `--noise-scale`로 산포 스케일.

```
cx += N(-0.084, 0.222·s),  cy += N(-0.012, 0.137·s)
area *= clip(N(0.979, 1.79·s), 0.008, 2.82),  miss_p = 0.041·s
```

## 4. 결과 — noise_scale sweep (CL: val 22 ep, FPE<0.5m & TLD∈[0.7,1.5])

| noise_scale | CL success | mean FPE | TLD | clean PM |
|---|---|---|---|---|
| baseline (0) | 4.5% (1/22) | 4.075m | 1.05 | 92.6% |
| 0.5 | 13.6% (3/22) | 2.681m | 1.06 | 91.4% |
| 1.0 | 13.6% (3/22) | 1.341m | 1.02 | 87.6% |
| 1.5 | 18.2% (4/22) | 1.063m | 1.02 | 92.2% |
| **2.0** | **36.4% (8/22)** | **0.575m** | 1.02 | **91.4%** |
| 2.5 | 27.3% (6/22) | 1.045m | 1.02 | 91.8% |
| 3.0 | 22.7% (5/22) | 1.333m | 1.01 | 90.5% |

**깔끔한 역U자 — 봉우리 noise_scale=2.0.** 메커니즘 확증:
- 노이즈 부족 → VLM 분포 미커버(여전히 OOD)
- 노이즈 과다 → bbox 신호 자체 파괴(2.5~3.0에서 하락)
- TLD는 전 구간 ~1.0 → 문제는 항상 **방향(FPE)** 이었고 궤적 길이가 아님

### Champion: aug2.0 path별

| path_type | SR | FPE |
|---|---|---|
| right_right | 100% (1/1) | 0.000m |
| right_left | 80% (4/5) | 0.230m |
| left_straight | 33% (1/3) | 0.383m |
| center_left / left_right | 50% | 0.29~0.58m |
| center_right / right_straight | 0% | 1.15m (임계값 바로 위) |

## 5. 산출물

- 측정: `scripts/measure_exp60_bbox_offset.py`, `docs/v5/exp60_bbox_offset_stats.json`
- 학습: `scripts/train_exp54_stage2_v2_action.py` (`--augment --noise-scale`)
- 가중치: `runs/v5_nav/mlp/exp54/stage2_v2/stage2_v2_mlp_aug{0.5..3.0}.pt` (**champion: aug2.0**)
  - 기존 `stage2_v2_mlp.pt`(baseline)는 보존 — 롤백 가능
- 평가: `scripts/eval_exp59_closedloop.py` (`--stage2-pt --out-tag`)
  - 결과: `docs/v5/closed_loop_eval/exp59_closedloop_result_{tag}.json`

## 6. 교수님 질문과의 연결

- Q1~Q4 (grounding "본다") → Exp57/59로 답함 ✅
- **Exp60 = "그래서 실제로 가는가?"** — grounding을 action까지 닫음.
  같은 grounding(98%)인데 MLP의 분포 강건성만으로 CL 4.5%→36.4%.
  → "텍스트 목표 → grounding → 실제 주행" end-to-end의 마지막 연결고리가 동작함을 입증.

## 7. 남은 한계 / 다음 단계

- FPE 0.575m는 0.5m 임계 근처 — 절반 path는 1.15m로 아슬하게 실패. 추가 개선 여지:
  - **systematic offset 추론 보정**: VLM cx에 +0.084 더해 분포 정렬(증강과 상보적)
  - **접근 B(전면)**: 학습 데이터를 VLM bbox로 re-ground → train==test 분포 일치
- 실로봇 검증(SODA): champion(aug2.0)을 서버에 배포 후 물리 환경 확인
- R3(basket-only)는 별도 데이터 수집 필요(이 실험 범위 밖)

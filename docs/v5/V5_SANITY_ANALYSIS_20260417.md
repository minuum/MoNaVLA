# V5 LEFT/RIGHT Sanity Analysis

작성일: 2026-04-17

## 목적

Exp09와 Exp11의 8-class 정책이 실제로 LEFT/RIGHT 계열을 어떻게 예측하는지,
정성 확인이 아니라 고정된 sanity 샘플 기준으로 빠르게 점검한다.

이번 확인은 아래 산출물을 기준으로 했다.

- Exp11 2-way purity check: [runs/sanity_checks/exp11_pathsets_1/summary.json](/home/billy/25-1kp/MoNaVLA/runs/sanity_checks/exp11_pathsets_1/summary.json:1)
- Exp11 4-way sanity: [runs/sanity_checks/exp11_pathsets_4way/summary.json](/home/billy/25-1kp/MoNaVLA/runs/sanity_checks/exp11_pathsets_4way/summary.json:1)
- Exp09 2-way purity check: [runs/sanity_checks/exp09_pathsets_1/summary.json](/home/billy/25-1kp/MoNaVLA/runs/sanity_checks/exp09_pathsets_1/summary.json:1)
- Exp09 4-way sanity: [runs/sanity_checks/exp09_pathsets_4way/summary.json](/home/billy/25-1kp/MoNaVLA/runs/sanity_checks/exp09_pathsets_4way/summary.json:1)

## 실험 조건

- 서버 환경: 2026-04-17 기준 CPU only
- GPU는 `nvidia-smi` 단계에서 드라이버를 잡지 못함
- sanity 스크립트: [scripts/test/check_v5_left_right_sanity.py](/home/billy/25-1kp/MoNaVLA/scripts/test/check_v5_left_right_sanity.py:1)
- 스크립트는 현재 다음을 지원함
  - config의 `val_dataset` 설정 자동 반영
  - 샘플 선별 후 배치 추론
  - `wanted_ids`로 클래스 지정
  - `subset_patterns` 기준 집계

## 핵심 결과

### Exp11

| Subset | GT | Prediction | Heuristic side | Sample |
|--------|----|------------|----------------|--------|
| `left_left` | `LEFT` | `RIGHT` | `right` | [left__00__idx1.jpg](/home/billy/25-1kp/MoNaVLA/runs/sanity_checks/exp11_pathsets_4way/left__00__idx1.jpg:1) |
| `left_left` | `FWD+L` | `RIGHT` | `left` | [fwd+l__00__idx0.jpg](/home/billy/25-1kp/MoNaVLA/runs/sanity_checks/exp11_pathsets_4way/fwd+l__00__idx0.jpg:1) |
| `right_right` | `RIGHT` | `RIGHT` | `none` | [right__00__idx104.jpg](/home/billy/25-1kp/MoNaVLA/runs/sanity_checks/exp11_pathsets_4way/right__00__idx104.jpg:1) |
| `right_right` | `FWD+R` | `RIGHT` | `right` | [fwd+r__00__idx103.jpg](/home/billy/25-1kp/MoNaVLA/runs/sanity_checks/exp11_pathsets_4way/fwd+r__00__idx103.jpg:1) |

해석:

- `left_left` 계열은 `LEFT`, `FWD+L` 모두 오른쪽 계열로 붕괴했다.
- `right_right` 계열은 `RIGHT`로 수렴하는 경향이 강하다.
- 따라서 Exp11의 문제는 단순 `LEFT=0%`가 아니라, 더 넓게 보면 **left-side 계열을 right-side로 접는 구조적 bias**로 보는 것이 맞다.

### Exp09

| Subset | GT | Prediction | Heuristic side | Sample |
|--------|----|------------|----------------|--------|
| `right_right` | `RIGHT` | `FWD+R` | `none` | [right__00__idx55.jpg](/home/billy/25-1kp/MoNaVLA/runs/sanity_checks/exp09_pathsets_4way/right__00__idx55.jpg:1) |
| `right_right` | `FWD+R` | `FWD+R` | `right` | [fwd+r__00__idx54.jpg](/home/billy/25-1kp/MoNaVLA/runs/sanity_checks/exp09_pathsets_4way/fwd+r__00__idx54.jpg:1) |

해석:

- 이번 val split 기준으로 Exp09는 `left_left`, `center_left`, `center_right` 관련 순수 sanity 샘플이 거의 남지 않았다.
- 다만 `right_right`에서는 `RIGHT`조차 `FWD+R`로 눌리는 경향이 보인다.
- 즉 Exp09는 Exp11처럼 모든 우측 계열을 `RIGHT`로 접지는 않지만, **우측 전방 계열(`FWD+R`)로 눌리는 경향**은 분명하다.

## 결론

이번 sanity만 놓고 보면:

1. Exp11은 우향 편향이 더 강하다.
2. Exp09는 `FWD+R` 쪽으로 수렴하는 경향이 남아 있다.
3. 두 실험 모두 좌우 계열을 안정적으로 분리했다고 보기 어렵다.

## 이번 sanity의 한계

1. 현재 val split 자체가 고정 benchmark가 아니라서 실험마다 남는 샘플 분포가 다르다.
2. `center_left`, `center_right`는 현재 discrete label 기준에서 `LEFT/RIGHT`가 아니라 `FWD+L/FWD+R`로 더 자주 잡힌다.
3. heuristic basket detector는 `none` 비율이 높아 판정 기준으로 쓰기엔 약하다.
4. 따라서 정성 샘플과 `summary.json`은 발견용이며, 실험 채택용 판정 기준은 별도 고정 benchmark split이 필요하다.

## 다음 조치

다음부터는 [benchmarks/definitions/sanity_lr_4way_manifest.yaml](/home/billy/25-1kp/MoNaVLA/benchmarks/definitions/sanity_lr_4way_manifest.yaml:1)과
[benchmarks/definitions/splits/v5_lr_4way_sanity.yaml](/home/billy/25-1kp/MoNaVLA/benchmarks/definitions/splits/v5_lr_4way_sanity.yaml:1)을
기준으로 고정된 sanity benchmark를 먼저 통과한 뒤, 오프라인 PM/DM이나 rollout으로 넘어가야 한다.

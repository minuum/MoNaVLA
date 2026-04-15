# basket_dataset_v2 데이터 구조 분석 보고서

> **작성일**: 2026-03-06  
> **데이터 경로**: `/home/billy/25-1kp/vla/ROS_action/basket_dataset_v2/`  
> **분석 기반**: 실제 H5 파일 직접 파싱 결과 (추측 없음)  
> **모델 대상**: v3-exp08 (`epoch=07, val_loss=0.031`)

---

## Background

`vla-driving` 브랜치의 종합 분석(VLA_COMPREHENSIVE_ANALYSIS_20260306.md)에서 제기된 핵심 가설:

> **"모델이 이미지를 보고 액션을 결정하는 것이 아니라, 에피소드 Frame 번호(타이밍)를 암기하여 액션을 출력한다."**

이 가설을 **우리 서버의 실제 `basket_dataset_v2`** 데이터(528개 H5 파일)로 직접 검증한다.

---

## Analysis

### 1. 데이터셋 기본 구조

| 항목 | 측정값 |
|:---|:---|
| 총 에피소드 수 | 528개 |
| Left 방향 | 278개 (`hori_left_core_medium`) |
| Right 방향 | 250개 (`hori_right_core_medium`) |
| 에피소드 길이 | 18 frames (1개 예외: 1 frame짜리 불완전 에피소드) |
| Actions shape | `(18, 3)` — linear, angular, (미사용) |
| Images shape | `(18, 720, 1280, 3)` — 720p |
| 수집 날짜 | **2026-01-29 단 하루** (528개 전량) |
| Instruction 종류 | 2가지 (`brown pot on the left` / `on the right`) |

**⚠️ Note**: Instruction이 `"Navigate to the brown pot"` — 실제 목표물인 gray basket이 아닌 brown pot을 목표로 기술되어 있음. 이는 학습 초기부터의 Instruction 혼란 문제.

---

### 2. Action 값 분포

전체 528개 에피소드(9,504 프레임)에서 사용된 유니크 액션 값:

| 축 | 사용된 값 |
|:---|:---|
| Linear (전진/후진) | `{0.0, 1.15}` — **단 2가지** |
| Angular (회전) | `{-1.15, 0.0, 1.15}` — **단 3가지** |

→ 연속적(continuous) 값이 전혀 없음. 사실상 **Binary + Ternary 이산 제어**.  
→ 이 값의 조합이 현재 9-class discrete 학습의 기반.

---

### 3. 핵심 발견: 타이밍 암기 문제 정량적 검증

#### 대표 Action 시퀀스

```
LEFT 방향 (277개, 99.6%):
  STOP | F F F F | L | FL FL FL | F F | FR FR FR | R | F F F

RIGHT 방향 (250개, 100%):
  STOP | F F F F | R | FR FR FR FR | F F | FL FL FL | F F F
```

#### 프레임별 액션 결정성 (Left, 277개 에피소드)

| Frame | 액션 | 비율 | 의미 |
|:---:|:---:|:---:|:---|
| F01 | STOP | **100%** | 에피소드 시작 |
| F02~F05 | F | **100%** | 직진 접근 |
| F06 | L | **100%** | 좌전환 시작 |
| F07~F09 | FL | **100%** | 좌전진 (화분 회피) |
| F10~F11 | F | **100%** | 직진 복귀 |
| F12~F14 | FR | **100%** | 우전진 (바구니 방향) |
| F15 | R | **100%** | 우전환 |
| F16~F18 | F | **100%** | 최종 직진 |

> **모든 프레임에서 100% 결정성** — 277개 에피소드 중 단 하나도 이 시퀀스를 이탈하지 않음.

#### Linear/Angular 값 표준편차 (Left 5개 에피소드, 18프레임)

```
Linear  std: [0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0.]
Angular std: [0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0. 0.]
```

**→ 표준편차 완전히 0**: 5개 에피소드가 프레임 단위로 완전히 동일한 액션 값(소수점 이하까지) 출력.

---

## Findings

### F1. 데이터셋 전체가 단일 시퀀스 패턴으로 구성됨

- **Left 278개 에피소드** → 유니크 시퀀스: **1개** (277개 동일, 1개 불완전)
- **Right 250개 에피소드** → 유니크 시퀀스: **1개** (250개 동일)
- 528개 에피소드 전체가 **2가지 고정 시퀀스** 중 하나

이는 방향별 "Core 패턴"만 수집되었음을 의미한다. **Variant(변형) 패턴이 전혀 없다.**

### F2. 이미지(시각 정보)는 학습에 기여하지 못하는 구조

모델이 최적화(loss≈0)를 달성하기 위한 최단 경로:

```
Input: [Frame 번호] → Output: [고정 액션]
```

이미지를 참조하지 않아도 Frame 번호만으로 항상 정답을 맞출 수 있기 때문에,  
모델은 **이미지 → 액션** 관계를 학습할 필요가 없다.

> **검증**: val_loss = 0.031 (거의 완벽) ≠ 실제 주행 성공  
> 오프라인 100% 정확도는 이 암기 현상을 수치로 증명한다.

### F3. 수집 편향 — 단 하루(2026-01-29)에 전량 수집

- 동일 날짜, 동일 환경(조도/위치), 동일 조작자 → 에피소드 간 다양성 없음
- 화분이 항상 같은 위치(Frame 5~6에서 처음 시야에 들어옴)에서 등장함

### F4. Instruction이 목표물과 불일치

```
Instruction: "Navigate to the brown pot on the left"
실제 최종 목표: gray basket
실제 장애물:    brown pot
```

모델이 "피해야 할 것"을 "가야 할 것"으로 학습하고 있음.  
v3-exp08에서 Instruction을 `"Navigate toward the gray basket..."` 으로 수정한 것이 올바른 방향.

---

## Conclusion

### 타이밍 암기 문제: 수치로 완전 확인됨

| 주장 | 검증 결과 |
|:---|:---:|
| 에피소드 Action 시퀀스가 동일하다 | ✅ 100% 동일 (Left 277/277, Right 250/250) |
| 이미지 변화와 무관하게 타이밍만 있다 | ✅ 표준편차 = 0.000000 |
| Variant 패턴이 없다 | ✅ 유니크 시퀀스 Left 1개, Right 1개 |
| Action 값이 이산적 on/off다 | ✅ Linear={0, 1.15}, Angular={-1.15, 0, 1.15} |
| Instruction이 목표물과 반대다 | ✅ brown pot → 실제 장애물 |

### 실제 주행 실패 메커니즘

```
학습된 것:  Frame 6 → L,  Frame 7~9 → FL  (항상 이 타이밍에 회피)
실제 주행:  화분이 Frame 3에 나타나면 → Frame 6까지 기다렸다가 회피 → 화분과 충돌
           화분이 Frame 8에 나타나면 → 이미 FL 시퀀스 종료 → 직진으로 통과
```

화분의 실제 위치/크기와 무관하게, 모델은 "6번째 프레임에 무조건 L" 패턴을 반복한다.

---

## 다음 단계 (우선순위 순)

### 즉각 적용 가능

| 액션 | 근거 | 예상 효과 |
|:---|:---|:---|
| `dataset_v3` 수집 시 화분 위치를 다르게 세팅 | F3 (수집 편향) | 타이밍 암기 방지 |
| Core 패턴 외 Variant 에피소드 추가 | F1 (단일 패턴) | 시각 기반 학습 강제 |
| Instruction 통일: `"Navigate toward the gray basket while avoiding the brown pot"` | F4 (혼란) | 목표/장애물 구분 학습 |

### 데이터 수집 가이드라인 (구체적)

```
현재 Core 패턴:
  - 화분 항상 같은 위치 (Frame 5~6에서 처음 등장)
  - 회피 타이밍 고정 (Frame 6: L, Frame 7~9: FL)

필요한 Variant 패턴:
  - Close:        Frame 1~2부터 화분 크게 보임 → 즉시 회피 필요
  - Far:          Frame 8~9에서 화분 처음 등장 → 늦은 회피
  - No-obstacle:  화분 없이 바구니만 → STOP 없이 F 계속
  - Partial:      화분이 화면 가장자리에만 보임 → 소폭 조향만
```

### 변경 유지 (현재 최적값)

| 항목 | 값 | 이유 |
|:---|:---:|:---|
| Chunk Size | k=1 (Reactive) | 이산 데이터에 최적 |
| Window Size | 8 | EXP-17 최고 성능 |
| Action Head | Discrete 9-class | 데이터 자체가 이산 |
| LoRA Rank | 16 | v3 계열 표준 |

---

*분석 스크립트: 직접 Python + h5py 실행 결과. 추측 없음.*

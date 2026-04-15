# VLA Dataset v3 학습 계획

> **작성일**: 2026-03-06  
> **기반 분석**: [dataset_analysis_basket_v2_20260306.md](./dataset_analysis_basket_v2_20260306.md)  
> **현재 모델**: v3-exp08 (val_loss=0.031, epoch=7)

---

## 문제 정의 (3단계 추론)

### Step 1. 모델이 실제로 학습한 것

모델이 val_loss ≈ 0에 수렴하는 데는 두 경로가 있다:

```
경로 A (원하는 것): 이미지 → "화분이 가까이 있다" → FL 액션
경로 B (일어난 것): Frame 번호 → "6번째다" → L 액션 (항상)
```

528개 에피소드 전체가 동일한 시퀀스이므로, 이미지 파싱이 필요 없는 **경로 B가 수학적으로 더 쉽다.**

### Step 2. Window(히스토리)가 타이머가 된 이유

Window Size = 8: 모델은 현재 + 이전 7개 히스토리를 입력으로 받는다.

```
히스토리: [STOP, F, F, F, F, 현재] → "5스텝 지났다 → 다음은 L"
```

히스토리가 이미지 맥락이 아닌 **스텝 카운터**로 전락했다.  
이것이 val_loss=0.031 ≠ 실제 주행 성공인 이유다.

### Step 3. 데이터를 바꿔야 한다

> **필요충분조건**: 같은 Frame 번호여도, 이미지가 다르면 액션이 달라야 한다.

이 조건이 만족되면 모델은 Frame 번호로 loss를 줄이는 것이 불가능해지고,  
반드시 이미지를 보고 판단해야 한다.

---

## Dataset v3 구성 계획 (Option B — 권장)

> 기존 Core 100개만 유지 + Variant 200개 신규 수집 = **총 300개**  
> (기존 528개 전량 유지 시 Variant:Core = 36%:64% → 희석. Option B는 67%:33% → 다양성 지배)

### Variant 종류 및 수집 방법

| Variant | 수량 (Left+Right) | 로봇 출발 위치 | 예상 시퀀스 특징 |
|:---:|:---:|:---|:---|
| **Core** (유지) | 50+50 = 100개 | 화분으로부터 1~1.5m | 현행 유지 (F×4 후 회피) |
| **V1 Close** | 30+30 = 60개 | 화분 바로 앞 30~50cm | Frame 1~2에서 즉시 회피 |
| **V2 Far** | 30+30 = 60개 | 화분으로부터 2.5~3m | Frame 8~10에서 처음 회피 |
| **V3 Offset** | 20+20 = 40개 | 화분 옆을 비껴가는 경로 | 소폭 조향만, 거의 직진 |
| **V4 No-obs** | 20+20 = 40개 | 화분 없이 바구니만 배치 | STOP 후 순수 F 연속 |
| **합계** | **150+150 = 300개** | | |

### 수집 시 핵심 확인사항

**Close (V1)**
```
- 화분이 Frame 1부터 화면 크기의 30% 이상 차지해야 함
- 로봇이 Frame 2~3 이내에 조향을 시작해야 자연스러운 에피소드
```

**Far (V2)**
```
- Frame 5~7까지 화분이 화면에서 작게 보이거나 안 보여야 함
- 화분이 Frame 8~10에서 갑자기 커지는 패턴이어야 함
```

**Offset (V3)**
```
- 화분이 화면 좌우 끝부분(edge 20%)에만 등장
- 직진 위주 + 화분 반대 방향 소폭 조향
```

**No-obstacle (V4)**
```
- 화분 완전히 제거 후 수집
- 바구니가 정면에 보이면 STOP → F → F → F ... 패턴
- "장애물 없으면 직진" 학습
```

---

## Instruction 재설계

| Variant | Instruction |
|:---|:---|
| Core / Close / Far / Offset | `"Navigate to the gray basket while avoiding the brown bucket"` |
| No-obstacle | `"Navigate directly to the gray basket"` |

**변경 이유**: 기존 `"Navigate to the brown pot"` 는 장애물이 목표물로 기술되는 구조적 혼란이 있었음.

---

## 변경 유지 (현재 최적값)

| 항목 | 값 | 근거 |
|:---|:---:|:---|
| Chunk Size | k=1 (Reactive) | EXP-05/17 검증 |
| Window Size | 8 | EXP-17 94.72% 달성 |
| Action Head | Discrete 9-class | 데이터 자체가 이산 |
| Backbone | Kosmos-2 / RoboVLM-Nav | v3 계열 표준 |
| LoRA rank | 32 | exp08 기준 |

---

## 검증 계획

### 1. 데이터 수집 직후 — 다양성 점검
```python
# 목표: 유니크 시퀀스 수 ≥ 10개 (기존: 좌우 각 1개)
# 목표: 모든 프레임에서 액션 결정성 < 80% (기존: 100%)
python3 scripts/analyze_action_diversity.py --dataset ROS_action/basket_dataset_v3/
```

### 2. 학습 완료 후 — 오프라인 정확도
```bash
python3 scripts/test_pm_dm_discrete.py --checkpoint runs/.../epoch_best.ckpt
# 목표: PM/DM ≥ 85%
# 주의: 100% 달성 시 다시 타이밍 암기 의심
```

### 3. 실제 주행 테스트 — 핵심 시나리오
| 테스트 | 성공 기준 | 실패 기준 |
|:---|:---|:---|
| Close: 화분 50cm 앞 | Frame 1~2에 회피 시작 | Frame 6에 회피 시작 (타이밍 암기) |
| Far: 화분 3m 뒤 | Frame 8~10에 회피 시작 | Frame 6에 회피 시작 (타이밍 암기) |
| No-obstacle | 바구니까지 직진 | 중간에 불필요 조향 |

---

*분석 기반: basket_dataset_v2 실측 (H5 파싱). 추측 없음.*  
*실제 환경: 빈 갈색 플라스틱 화분 / 직사각 회색 세탁 바구니 / 저각 광각 카메라*

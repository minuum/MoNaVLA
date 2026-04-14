# basket_dataset_v3 수집 가이드

> **기반 문서**: `docs/dataset_analysis_basket_v2_20260306.md`, `docs/training_plan_dataset_v3_20260306.md`  
> **목표**: 타이밍 암기 방지 = 동일 Frame 번호에서 이미지가 다르면 액션이 달라야 함  
> **총 수집 목표**: 300개 에피소드

---

## 배치 기준 (모든 Variant 공통)

- **목표물** (바구니): 로봇 정면 기준 2~4m 앞, 상시 배치
- **장애물** (갈색 화분): Variant별 위치 변경 (아래 표 참고)
- **로봇 출발 방향**: 바구니 정면 정렬
- **에피소드 길이**: 18 frames 고정 (`fixed_episode_length = 18`)
- **Instruction**: `"Navigate to the gray basket while avoiding the brown pot"`  
  (No-obstacle만: `"Navigate directly to the gray basket"`)

---

## Variant별 물리 세팅

### Core — 현행 유지 (100개 목표)

| 항목 | 값 |
|:---|:---|
| 화분 거리 | 로봇에서 1~1.5m 앞 |
| 바구니 거리 | 로봇에서 2.5m 앞 |
| 수집 수 | Left 50 + Right 50 |

> 기존 basket_dataset_v2의 Medium 거리와 동일. 유지 목적이므로 새로 수집하지 않고 기존 데이터 100개 샘플링 가능.

---

### V1 Close — 화분 바로 앞 (60개 목표)

| 항목 | 값 |
|:---|:---|
| 화분 거리 | 로봇에서 **30~50cm** 앞 |
| 바구니 거리 | 로봇에서 2.5m 앞 |
| 수집 수 | Left 30 + Right 30 |

**Frame 1에서 확인**: 화분이 화면에서 큰 비율(30% 이상) 차지해야 함  
**예상 시퀀스**: `STOP | FL FL FL | F F | FR FR | F F F`

**수집 Order**:
```
1. 화분을 로봇 바퀴 앞 30~50cm에 배치
2. Data collector 시작 → 에피소드 녹화
3. Frame 1에서 조향 즉시 시작되는지 확인
4. 18 frames 완료 후 저장
5. 위치 미세 조정하며 30회 반복
```

---

### V2 Far — 화분 멀리 (60개 목표)

| 항목 | 값 |
|:---|:---|
| 화분 거리 | 로봇에서 **2.5~3m** 앞 |
| 바구니 거리 | 로봇에서 4~4.5m 앞 |
| 수집 수 | Left 30 + Right 30 |

**Frame 7~9에서 확인**: 화분이 처음 시야에 들어오며 조향 시작  
**예상 시퀀스**: `STOP | F F F F F F | L | FL FL FL | F F | FR | F`

**수집 Order**:
```
1. 화분을 로봇에서 충분히 멀리(2.5~3m) 배치
2. Frame 6까지 화분이 작게 보이거나 보이지 않아야 함
3. 화분이 보이기 시작하는 Frame에서 조향 시작
4. 조향이 Frame 8 전후인지 확인 후 저장
```

---

### V3 Offset — 화분이 옆을 비껴감 (40개 목표)

| 항목 | 값 |
|:---|:---|
| 화분 위치 | 로봇 경로에서 **좌우 30~40cm** 벗어난 위치 |
| 화분 거리 | 로봇에서 1~2m |
| 바구니 거리 | 로봇에서 2.5m |
| 수집 수 | Left 20 + Right 20 |

**화면에서 확인**: 화분이 이미지 가장자리(edge 20%)에만 보여야 함  
**예상 시퀀스**: `STOP | F F F | FL | F F F F F F F | F F F`

---

### V4 No-obstacle — 화분 없음 (40개 목표)

| 항목 | 값 |
|:---|:---|
| 화분 | **없음** |
| 바구니 거리 | 로봇에서 2m |
| 수집 수 | 20 + 20 (Left/Right 구분 의미 없음, 바구니 좌우 위치 변경) |

**예상 시퀀스**: `STOP | F F F F F F F F F F F F F F F F F`

---

## 수집 순서 권장

```
Day 1: V4 No-obstacle 40개 → V1 Close 60개
Day 2: V3 Offset 40개     → V2 Far 60개
Day 3: (Core 기존 데이터 샘플링 100개)
```

V4를 먼저 하는 이유: 가장 단순한 시나리오로 수집 파이프라인 검증

---

## 수집 완료 후 검증

```bash
# basket_dataset_v3 디렉토리 기준
python3 docs/scripts/analyze_action_diversity.py \
  --dataset ROS_action/basket_dataset_v3/

# 합격 기준
# ✅ 유니크 시퀀스 ≥ 10개
# ✅ 프레임별 최대 결정성 < 80%
```

불합격 시 → 결정성이 높은 Frame 번호 확인 → 해당 Frame에서 다양한 액션이 나오는 Variant 추가 수집

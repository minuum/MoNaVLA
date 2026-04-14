# VLA 실험 전체 분석 및 다음 방향 — 학습 서버 참조용

> **작성일**: 2026-03-06  
> **목적**: 이 문서는 추론 서버와 학습 서버 어디서든 동일한 맥락을 가질 수 있도록, 지금까지의 실험 기조와 핵심 발견, 그리고 현재 해결해야 할 진짜 문제를 환각 없이 정리한 문서입니다.

---

## 1. 프로젝트 Task 정의 (명확한 기준)

**로봇**: TurtleBot4 (Omnidirectional, 4방향 + 대각 이동 가능)  
**카메라**: 전방 단안 카메라 (수직 FOV 좁음 — 근접 시 물체 화면 하단 이탈)

**Task 목표 (전체 시퀀스)**:
1. **Phase 1 — 방향 설정**: 회색 바구니(gray basket, 목표물)가 화면에 보임 → 바구니 방향으로 접근
2. **Phase 2 — 장애물 회피**: 갈색 화분(brown pot, 장애물)이 경로에 나타남 → 화분의 화면 내 크기(= 거리감)를 보고 적절히 옆으로 피하면서 전진 유지
3. **Phase 3 — 도达**: 바구니가 화면 하단 중앙에 위치하면 STOP

**핵심**: Phase 2에서 화분의 "화면 속 크기 변화"를 통해 거리를 추정하는 Depth Cue가 필요하다. 단순히 화분이 보이는/보이지 않는 여부가 아니라, **화면에서 얼마나 크게 보이냐**가 회피 타이밍의 기준이다.

---

## 2. 현재 훈련 데이터 실체 분석 (`basket_dataset_v2`)

### 데이터 통계
- **총 에피소드**: 528개 (Left 278개, Right 250개)
- **에피소드 길이**: 17프레임 (Core 패턴 기준)
- **Instruction**: `"Navigate to the brown pot on the left/right"` *(주의: 목표물 명칭이 실제와 반대. 실제 목표는 gray basket이지만 초기 Instruction이 brown pot으로 되어 있었음)*

### 실제 Action 시퀀스 (3개 에피소드 직접 확인결과)

```
episode_20251203_122510_1box_hori_left_core_medium:
  F F | L | FL FL FL FL FL FL FL | F F | FR FR FR | F F

episode_20251203_122758_1box_hori_left_core_medium:
  F F | L | FL FL FL FL FL FL FL | F F | FR FR FR | F F

episode_20251203_122846_1box_hori_left_core_medium:
  F F | L | FL FL FL FL FL FL FL | F F | FR FR FR | F F
```

**발견**: **3개 에피소드 모두 액션 시퀀스가 완전히 동일하다.**

### 이 데이터로 모델이 학습한 것

```
Phase 1 (Frame 1~2):   "직진" → 접근 시작
Phase 2 (Frame 3~10):  "좌이동 → 전진+좌 × 7" → 화분 회피 기동
Phase 3 (Frame 11~17): "직진 → 전진+우 × 3 → 직진" → 화분 지나 바구니 방향 복귀
```

Phase 자체는 데이터에 담겨 있다. 그러나 **모든 에피소드가 동일한 타이밍에 동일한 액션을 취한다.** 이는 화분이 항상 동일한 위치(Frame 3에서 처음 보이고, Frame 4~10 동안 회피)에 있도록 설정된 Core 패턴 수집이기 때문이다.

### 핵심 문제

> 모델이 학습한 것: **"Frame 번호 → Action"** (시간적 타이밍 기반 암기)  
> 모델이 학습해야 할 것: **"현재 이미지에서 화분의 위치/크기 → Action"** (시각 기반 의미론적 이해)

실제 주행에서는 화분이 항상 같은 타이밍에 나타나지 않는다. 화분이 조금 더 멀거나, 시야에 일찍 들어오거나, 더 늦게 시야에서 사라진다. 이 경우 모델은 Frame 번호 기반의 암기만 있기 때문에 올바른 회피를 하지 못한다.

---

## 3. 실제 추론 로그에서 확인된 실패 패턴 (2026-03-06 세션)

- **테스트 모델**: `v3_exp08_center_goal` (epoch=07, val_loss=0.031)
- **세션 수**: 11개 세션 (각 34스텝 = 17프레임 × 2 로그)
- **Instruction**: `"Navigate toward the gray basket until it is centered in the frame"`

### 관찰된 실패

```
모든 세션에서 공통 패턴:
  Step 1~4:   조향 정상 (바구니/화분 보임, 방향 설정)
  Step 5~9:   화분 회피 시도 (FL or FR 조향값 출력)
  Step 10~16: Angular 갑자기 0.0 → 직진만 반복  ← 실패 구간
  Step 17~18: 방향 혼란 (좌우 불규칙 전환)
```

### 실패 원인 (FOV 이탈)

카메라의 수직 FOV 한계로 인해, 로봇이 화분에 가까이 가면 화분이 **화면 하단으로 사라진다.**  
현재 모델은 현재 프레임 이미지에만 의존하는 Reactive Policy이므로, 화면에서 화분이 사라지는 순간 회피 근거가 없어져 직진으로 돌아간다.

### chunk_preview 값 해석

`chunk_preview`는 미래 예측이 아닌, **현재 프레임에 대한 9-class Categorical Logit 벡터**:
```
[[STOP_score, F_score, B_score, L_score, R_score, FL_score, FR_score, BL_score, BR_score]]
```
Argmax값이 실제 실행되는 액션 클래스이다. 값이 크면 더 확신하는 것.

---

## 4. 전체 실험 성능 흐름 (숫자 그대로)

|   실험   | 핵심 변경                      |  PM/DA (오프라인)  | 비고                             |
| :------: | :----------------------------- | :----------------: | :------------------------------- |
|  EXP-04  | Baseline, Linear Proj          |       65.83%       | Initial 9% — VLM만으로 한계      |
|  EXP-05  | Chunk k=1 (Reactive)           |       89.72%       | Middle/Final 100%                |
|  EXP-06  | Resampler 64 latents           |       82.50%       | Initial 81%                      |
|  EXP-09  | Resampler 128 latents          |       77.50%       | 더 많아도 성능 하락              |
|  EXP-10  | Window 16                      |       ❌ 실패       | 18프레임 데이터에 Window 16 불가 |
|  EXP-16  | Window 6, Chunk 1              |       89.72%       | EXP-05와 동일                    |
|  EXP-17  | Window 8, Chunk 1              |     **94.72%**     | 현재 오프라인 최고               |
| v3-exp08 | Discrete 9-class, Goal-Centric | **100%** (in-dist) | 실제 주행에서 Mid-Frame 실패     |

**핵심 교훈**:
- `Chunk=1 (Reactive)`, `Window=8`, `Discrete 9-class`, `Resampler 64`가 현재 아키텍처 최적점
- 오프라인 100% 정확도 ≠ 실제 주행 성공. 훈련 데이터에 없는 상황에서 항상 실패

---

## 5. 현재 해결해야 할 진짜 문제

### 문제의 본질
**"화분 회피"라는 행동은 데이터에 있다. 그러나 그 행동이 이미지를 보고 결정되는 것이 아니라, 에피소드의 타이밍에 의해 암기되어 있다.**

따라서:
- 화분이 다른 거리에서 나타나면 → 회피 타이밍 불일치 → 실패
- 화분이 FOV에서 사라지면 → 회피 근거 없음 → 직진으로 복귀
- 바구니와 화분이 동시에 보이는 프레임에서 → 어떤 게 목표이고 어떤 게 장애물인지 구별 못함 (Instruction이 초기에 brown pot을 목표물로 기술했던 역사적 혼란 포함)

### 검증해야 할 사항 (실제 데이터에서 확인 필요)

> ⚠️ 아래는 H5 파일 접근 없이 확인 불가. 학습 서버(billy)에서 해야 할 작업:

1. **에피소드별 Action 시퀀스 다양성**: Core 패턴 외 Variant 패턴의 실제 Action이 다른지 확인
   ```bash
   python3 -c "import h5py, glob; [print(f['actions'][:, :2]) for f in [h5py.File(p) for p in glob.glob('/path/to/basket_dataset_v2/*.h5')[:5]]]"
   ```

2. **에피소드 내 이미지의 화분/바구니 위치 변화**: 화분이 화면에서 커지다가 사라지는 프레임이 실제로 수록되어 있는지
   - Frame 1~5: 화분 크게 보여야 함 (가까움)
   - Frame 6~10: 화분 화면 밖으로 이탈해야 함 (옆을 지나침)

3. **Action과 이미지의 상관관계**: 같은 이미지를 서로 다른 에피소드 frame에서 봤을 때 다른 Action이 대응되는지 (= 시각 기반 학습이 되었는지)

---

## 6. 다음 단계 제안 (우선순위 순)

### 즉시 (학습 서버에서)
- [ ] basket_dataset_v2 Variant 에피소드 5~10개에서 Action 시퀀스 뽑아서 Core와 비교
- [ ] 동일 에피소드 내 Frame 1, 8, 15 이미지 저장하여 화분/바구니 위치 변화 육안 확인

### 단기 (데이터 수집)
- 화분이 **다양한 거리에서 처음 보이는** 에피소드 추가 수집 (Close: Frame 1부터 크게 보임, Far: Frame 5부터 보임)
- Variant 패턴에서 화분 회피 타이밍이 Core와 다른 에피소드를 의도적으로 수집

### 중기 (모델 개선)
- Instruction 재설계: 현재 `"Navigate to the brown pot"` → `"Navigate to the gray basket while avoiding the brown pot"` 으로 명확히 구분
- 화분이 FOV에서 사라진 직후에도 회피 방향을 유지하는 데이터 필요 (Object Permanence 학습)

---

## 7. 변경 불가 기준 (현재 최적으로 검증된 것 — 바꾸지 말 것)

| 항목              |        현재 값        | 근거                                                                     |
| :---------------- | :-------------------: | :----------------------------------------------------------------------- |
| Action Head       |   Discrete 9-class    | EXP-11 Config 오류 이후 NavPolicy(MobileVLAClassificationDecoder)로 정착 |
| Chunk Size        |    k=1 (Reactive)     | EXP-05/17에서 증명. 짧은 Task에 Reactive가 최적                          |
| Window Size       |           8           | EXP-17에서 94.72% 달성. CALVIN 50% 비율과 일치                           |
| Resampler Latents |          64           | EXP-09에서 128으로 늘려도 동일 성능 확인                                 |
| LoRA Rank         |          16           | 현재 v3-exp 계열 표준                                                    |
| Backbone          | Kosmos-2 (RoboKosMos) | `RoboVLM-Nav` alias로 매핑됨                                             |

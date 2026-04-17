# V5 Exp01~11 종합 분석
작성일: 2026-04-16

> 기준 문서: `CLAUDE.md`, `docs/situation_analysis_20260411.md`, `docs/v5/index.md`, `docs/v5/exp0*/report.md`, `docs/v5/exp10/action_alignment.md`, `plan.md`

## 1. 한 줄 요약

- Exp01~04는 **정책 실패 원인 추적과 foundation 교체**의 과정이었다.
- Exp05~08은 **프롬프트/표현 방식 최적화** 단계였다.
- Exp09는 **8-class 통합 정책 실험**이었지만 Forward Bias가 남았다.
- Exp10은 **Grounding/BBox 트랙**으로 perception evidence를 만들었지만, rule transfer 자체는 약했다.
- Exp11은 **기존 학습형 action baseline**으로 58.6%까지 올라간 현재 기준점이다.
- Exp14 Step 1/2는 **BBox feature -> small MLP** 우회 경로로 68.4% / 75.9%까지 올라갔다.

## 2. 전체 비교표

| Exp | 핵심 질문 | 핵심 변경 | 기준/백본 | 대표 결과 | 현재 판정 |
|-----|-----------|-----------|-----------|-----------|-----------|
| Exp01 | 회귀 대신 분류로 바꾸면 해결되는가 | discrete classification 도입 | V4 기반 | val_loss 2.270, FORWARD 100% | 실패 baseline |
| Exp02 | 직선 편향을 제거하면 나아지는가 | straight 제거, stratified split | V4 기반 | val_loss 2.210, PM 50% | 부분 개선 |
| Exp03 | 텍스트 의미를 더 강하게 넣으면 나아지는가 | CLIP Norm Loss | Exp02 기반 | val_loss 1.784 | 의미 정렬 개선 가능성 |
| Exp04 | foundation을 바꾸면 구조적으로 좋아지는가 | Google-Robot pretrained, head scratch | Google-Robot | val_loss 0.776, PM 0% | loss 대비 inference collapse |
| Exp05 | 행동 전환 문맥을 prompt에 넣으면 안정화되는가 | action-aware instruction | Google-Robot 계열 | 전환 부드러움, loss 1.1~1.2 | 중간 최적화 |
| Exp06 | HF 표준 토큰/포맷과 정렬하면 일반화가 좋아지는가 | `<grounding>`, `<phrase>` 정렬 | Google-Robot 계열 | OOD 일반화 개선 | 인프라/표현 정비 |
| Exp07 | path type 힌트를 주면 좌우 혼동이 줄어드는가 | path-type grounding | Google-Robot 계열 | 좌우 혼동 감소 | 보조 conditioning 성공 |
| Exp08 | 목표 중심 prompt로 STOP을 배울 수 있는가 | center-goal prompt | Google-Robot 계열 | 첫 STOP 로직 성공 | 정책 표현 개선 |
| Exp09 | 8-class full policy가 실제로 작동하는가 | 8-class + center-goal + weights | Google-Robot | val_loss 1.203, PM/DM 85.7%, bias 지속 | 형식적 통합 성공, 정책 실패 |
| Exp10 | policy 대신 grounding을 직접 학습하면 무엇이 보이는가 | next-token BBox grounding | Kosmos-2 grounding track | val_loss 0.012, IoU 0.87, rule transfer 34.4% | perception strong, transfer 약함 |
| Exp11 | Exp04 장점과 Exp09 8-class를 재결합하면 되는가 | Exp04 parent + 8-class 재설계 | Google-Robot | PM 58.6% | 현재 학습형 baseline |
| Exp14 Step 1/2 | BBox를 작은 action head로 바꾸면 되는가 | bbox history MLP / +image feature | Kosmos-2 perception + small head | 68.4% / 75.9% | 현재 최강 실용 baseline |

## 3. 실험별 상세 분석

### Exp01
- 목표: 연속 회귀 대신 discrete action classification으로 강제 선택 구조를 만들기.
- 관찰: 학습은 되지만 거의 모든 장면에서 `Forward`로 붕괴.
- 해석: 문제는 회귀 자체보다 **데이터 불균형과 backbone 오염**이었다.
- 현재 의미: 모든 후속 실험의 실패 baseline.

### Exp02
- 목표: 직선 데이터 비율을 줄여 FORWARD bias를 완화.
- 관찰: `val_loss 2.210`으로 약간 개선됐지만 정책 품질은 충분치 않음.
- 해석: 데이터 분포만 바로잡아도 부족하고, V4 기반의 한계가 여전히 크다.
- 현재 의미: 데이터셋 필터링 방향은 맞았지만 결정타는 아님.

### Exp03
- 목표: `left/right` 지시문의 의미를 action representation에 강제로 붙이기.
- 관찰: `CLIP Norm Loss` 추가 후 `val_loss 1.784`.
- 해석: 텍스트-액션 정렬이 실제로 도움이 될 가능성을 보여줬다.
- 한계: PM/DM 검증 문서가 약하다.
- 현재 의미: semantic alignment 계열의 유효성은 보였지만, 최종 승자는 아님.

### Exp04
- 목표: V4 기반을 버리고 Google-Robot foundation으로 교체.
- 관찰: `val_loss 0.776`로 큰 폭 개선.
- 해석: 이 프로젝트의 핵심 전환점. 저데이터 구간에서는 추가 데이터보다 **foundation quality**가 더 중요했다.
- 한계: 문서상 PM/DM, 실주행 검증이 완전히 닫히지 않았다.
- 현재 의미: foundation 전환의 중요성을 보여준 실험이지만, 최근 재평가 기준으로는 **loss-good / inference-bad** 사례다.

### Exp05
- 목표: 과거/미래 행동 문맥을 instruction에 넣어 temporal consistency 강화.
- 관찰: 부드러운 action transition에 도움이 됐다고 기록.
- 해석: 정책 안정화에는 도움을 줬지만 foundation 교체만큼의 큰 점프는 아니다.
- 현재 의미: prompt engineering 계열의 중간 최적화.

### Exp06
- 목표: Kosmos-2 / HuggingFace 표준 토큰 체계와의 정렬.
- 관찰: custom token 의존도를 줄이고 OOD instruction generalization 개선.
- 해석: 직접 성능 향상보다 **실험 생태계 정비** 성격이 강하다.
- 현재 의미: Exp10 grounding 트랙으로 이어지는 기반 정리.

### Exp07
- 목표: path-type을 명시해 좌/우 모호성 완화.
- 관찰: 초기 학습에서 left/right confusion이 감소.
- 해석: visual scene만으로 부족한 방향 priors를 언어적으로 보완한 실험.
- 현재 의미: Exp08, Exp09의 goal-oriented prompt 전 단계.

### Exp08
- 목표: STOP/종료 조건을 모델이 이해하도록 만들기.
- 관찰: target centered 상태에서 첫 autonomous STOP behavior 성공으로 기록.
- 해석: 이전 실험들이 방향 결정에 집중했다면, Exp08은 termination condition 학습 실험이다.
- 현재 의미: 정책 표현 설계에서 의미 있는 성공.

### Exp09
- 목표: Google-Robot 기반 + 8-class + center-goal까지 모두 통합한 full policy 만들기.
- 관찰: `val_loss 1.203`, trainer accuracy 83%, offline PM/DM 85.7%.
- 핵심 해석: 수치는 그럴듯하지만 문서 결론은 명확하다. **Forward Bias가 여전히 남아 있고 rotation/stop이 실제로 잘 안 배워졌다.**
- 현재 의미: 아키텍처는 8-class를 지원하지만 policy 학습은 아직 실패에 가깝다.

### Exp10
- 목표: navigation policy 대신 grounding/BBox 예측 능력 자체를 next-token prediction으로 실증.
- 관찰:
  - 초기 문서에서는 “학습 예정”이었음.
  - 최신 문서에서는 `val_loss 0.012`, `Grounding IoU 0.87`, `Tactical Match ~92%`, viewer/sequence/batch analysis까지 진전.
- 해석: 최근 가장 강한 성과다. 적어도 모델이 **바구니 위치와 시각 방향성은 잘 읽고 있다**는 증거가 됐다.
- 한계: grounding 성공이 곧바로 navigation policy 성공을 뜻하지는 않는다.
- 현재 의미: perception 자체는 강하지만, free-form generation을 바로 action으로 연결하면 약한 트랙이다.

### Exp11
- 목표: Exp04의 foundation 장점과 Exp09의 8-class를 다시 결합.
- 설정 핵심:
  - `center_straight`만 제외
  - `ROT_L/R` 희귀 클래스 강한 weight
  - 130 episode 기준으로 8-class 재설계
- 해석: 새 아이디어라기보다 Exp09 실패 원인을 반영한 재설계.
- 현재 의미: 현재 남아 있는 기존 학습형 action 기준점.

### Exp14 Step 1/2
- 목표: Exp10이 읽은 bbox/perception을 작은 action head로 바로 연결.
- 관찰:
  - Step 0 rule: `31.1%`
  - Step 0-B Exp10 ckpt rule: `34.4%`
  - Step 1 bbox history MLP: `68.4%`
  - Step 2 bbox + 16x16 grayscale image MLP: `75.9%`
- 해석: 큰 policy를 다시 end-to-end로 학습하는 것보다, 이미 읽힌 spatial cue를 작은 head로 바꾸는 쪽이 더 잘 먹혔다.
- 현재 의미: **현재 가장 강한 실용 baseline**.

## 4. 신뢰도 분류

### A. 확정된 결론

| 항목 | 판정 | 근거 |
|------|------|------|
| Exp01은 실패 baseline이다 | 확정 | FORWARD 100%, val_loss 2.270 |
| Exp04가 현재 정책 baseline이다 | 기각 | 재평가 결과 PM 0% collapse |
| foundation 교체가 큰 효과를 냈다 | 확정 | Exp01~03 대비 Exp04 급락 |
| Exp09는 8-class 형식 통합은 했지만 bias를 못 잡았다 | 확정 | `docs/v5/exp09/report.md` 결론이 명시적 |
| Exp10은 grounding 관점에서 가장 빠르게 진전했다 | 확정 | 최신 action alignment, viewer, report 흐름 일치 |
| Exp11이 현재 학습형 baseline이다 | 확정 | PM 58.6% |
| Exp14 Step 2가 현재 strongest이다 | 확정 | Step 2 PM 75.9% |

### B. 애매하지만 유력한 결론

| 항목 | 판정 | 이유 |
|------|------|------|
| Exp03의 semantic alignment는 실제 행동 개선에도 도움 됐을 것 | 유력 | loss는 개선됐지만 PM/DM 증거가 약함 |
| Exp05~08은 실제 성능보다 표현/프롬프트 안정화 효과가 컸다 | 유력 | 문서가 정성적 결과 위주 |
| Exp10의 tactical alignment가 generation 개선 후 더 강한 transfer로 이어질 수 있다 | 유력 | 현재 free-form generation이 degenerate |

### C. 아직 계획뿐인 결론

| 항목 | 판정 | 이유 |
|------|------|------|
| Step 2가 더 큰 split과 closed-loop에서도 strongest일 것이다 | 미확정 | 아직 작은 held-out split 기준 |
| 8-class에서 ROT_L/R 학습이 실제로 안정화된다 | 미확정 | 희귀 클래스라 추가 검증 필요 |
| Exp10 성공이 Exp11 또는 차기 policy의 구조적 돌파구가 된다 | 미확정 | 연결 가설만 있고 실험 닫힘 없음 |

## 5. 현재 공식 해석

### 지금 믿어도 되는 것
- 기존 학습형 baseline은 **Exp11 (58.6%)**다.
- 8-class를 늘리는 것만으로는 안 되고, Exp09가 그 한계를 보여줬다.
- grounding/perception 쪽은 **Exp10**이 가장 강한 최근 성과지만, 실용 baseline은 **Exp14 Step 2 (75.9%)**다.

### 지금 조심해야 하는 것
- `docs/v5/index.md`는 일부 수치와 상태가 최신 문서를 완전히 반영하지 못한다.
- `docs/v5/exp10/report.md`는 초기 계획 문서라 실제 진행도보다 뒤처져 있다.
- `docs/EXP09_10_11_TRAINING_REPORT.md`는 2026-02의 예전 세대 실험이라 현재 V5 naming과 혼동하면 안 된다.

## 6. 추천 해석 프레임

1. 기존 학습형 baseline: **Exp11**
2. 정책 실패 사례: **Exp09**
3. 최근 시각적 성과: **Exp10**
4. 현재 실용 baseline: **Exp14 Step 2**

## 7. 결론 표

| 분류 | 실험 |
|------|------|
| 가장 중요한 완료 실험 | Exp11 / Exp14 Step 2 |
| 가장 중요한 실패 사례 | Exp09 |
| 가장 흥미로운 최근 성과 | Exp10 |
| 가장 중요한 다음 후보 | Exp10 generation 개선 또는 Step 3 |

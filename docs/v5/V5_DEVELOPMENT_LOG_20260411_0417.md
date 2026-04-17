# V5 Development Log
> **Scope**: 2026-04-11 to 2026-04-17  
> **Purpose**: V5 Exp01~13에서 실제로 시도된 변경, 문서화, 평가, 설계 흔적을 시간축으로 한 번에 파악하기 위한 로그 문서  
> **Rule**: 학습 완료 여부와 별개로, 실제로 손댄 순간들을 모두 남긴다

## 1. 현재 요약

- **정책 baseline**: Exp04
- **8-class 통합 실패 사례**: Exp09
- **최근 가장 빠르게 진전한 트랙**: Exp10
- **재설계 흐름**: Exp11 -> Exp12 -> Exp13
- **평가 체계 정리 시점**: 2026-04-16 ~ 2026-04-17

## 2. Exp01~13 상태표

| Exp | 핵심 시도 | 현재 상태 | 학습 여부 | 핵심 흔적 |
|---|---|---|---|---|
| Exp01 | 6-class discrete baseline | 완료 | 학습됨 | [exp01/report.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp01/report.md:1), [mobile_vla_v5_exp01_discrete.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp01_discrete.json:1) |
| Exp02 | straight 제거 / no-straight | 완료 | 학습됨 | [mobile_vla_v5_exp02_no_straight.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp02_no_straight.json:1) |
| Exp03 | semantic alignment / CLIP norm | 완료 | 학습됨 | [mobile_vla_v5_exp02_clip_norm.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp02_clip_norm.json:1) |
| Exp04 | Google-Robot foundation 전환 | 완료 | 학습됨 | [exp04/report.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp04/report.md:1), [mobile_vla_v5_exp04_google_robot.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp04_google_robot.json:1) |
| Exp05 | action-aware instruction | 완료 | 학습됨 | [exp05/report.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp05/report.md:1), [mobile_vla_v5_exp05_action_aware.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp05_action_aware.json:1) |
| Exp06 | pure HF alignment | 완료 | 학습됨 | [exp06/report.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp06/report.md:1), [mobile_vla_v5_exp06_pure_hf.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp06_pure_hf.json:1) |
| Exp07 | path-type aware instruction | 완료 | 학습됨 | [exp07/report.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp07/report.md:1), [mobile_vla_v5_exp07_path_type.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp07_path_type.json:1) |
| Exp08 | goal / center-aware instruction | 완료 | 학습됨 | [exp08/report.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp08/report.md:1), [mobile_vla_v5_exp08_instruction_follow.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp08_instruction_follow.json:1) |
| Exp09 | 8-class balanced policy 통합 | 완료 | 학습됨 | [exp09/report.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp09/report.md:1), [mobile_vla_v5_exp09_8cls.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp09_8cls.json:1) |
| Exp10 | bbox grounding / alignment track | 완료 | 학습됨 | [exp10/report.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp10/report.md:1), [exp10/action_alignment.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp10/action_alignment.md:1), [mobile_vla_v5_exp10_bbox.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp10_bbox.json:1) |
| Exp11 | Google-Robot + 8-class 재시도 | 완료 | 학습됨 | [plan.md](/home/billy/25-1kp/MoNaVLA/plan.md:1), [mobile_vla_v5_exp11_google_robot_8cls.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp11_google_robot_8cls.json:1), [V5_SANITY_ANALYSIS_20260417.md](/home/billy/25-1kp/MoNaVLA/docs/v5/V5_SANITY_ANALYSIS_20260417.md:1) |
| Exp12 | per-frame action-aware instruction 정렬 | 시도 후 폐기 | 학습 안 함 | [mobile_vla_v5_exp12_action_instr.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp12_action_instr.json:1), [plan.md](/home/billy/25-1kp/MoNaVLA/plan.md:206) |
| Exp13 | instruction-conditioned action head | 구현 완료 / 대기 | 학습 안 함 | [mobile_vla_v5_exp13_instr_cond.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp13_instr_cond.json:1), [plan.md](/home/billy/25-1kp/MoNaVLA/plan.md:236) |

## 3. 2026-04-11 이후 타임라인

### 2026-04-11

**Exp04가 정책 baseline으로 굳어짐**

- Google-Robot foundation이 V4 checkpoint보다 훨씬 낫다는 방향이 정리됨
- 이후 V5 정책 계열의 기준점이 Exp04로 고정됨

근거:

- [docs/situation_analysis_20260411.md](/home/billy/25-1kp/MoNaVLA/docs/situation_analysis_20260411.md:1)
- [docs/v5/exp04/report.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp04/report.md:1)

### 2026-04-14

**V5 문서 허브와 Exp09 8-class 흐름이 등장**

- 대시보드와 archive 정리가 진행됨
- Exp09 8-class 실험이 본격적으로 문서화되기 시작함

대표 커밋:

- `b70a1a45` docs: add interactive track 1 experiment report
- `a582683e` feat(v5): Optimized 8-class action model & Dashboard update
- `20f8729e` docs: Update dashboard design inspired by OpenVLA and NanoLLM
- `1857c921` docs: Consolidate all technical HTML reports into project hub

### 2026-04-15 오전

**Exp01~09 문서가 GitHub Pages용으로 정리됨**

- V5 experiment comparison 페이지가 생김
- Exp05~08 개별 문서가 추가됨
- GitHub Pages에서 V5 흐름을 읽을 수 있는 최소 구조가 생김

대표 커밋:

- `92a9696d` docs: Add V5 experiment comparison and individual reports for GitHub IO
- `0f97387c` docs: Upgrade V5 dashboard to premium HTML and fix Exp01 metadata
- `38f65d6e` docs: All V5 related documents and scripts
- `e3d5b028` docs: Add individual reports for Exp 05-08 and update V5 dashboard table

대표 문서:

- [docs/v5/index.md](/home/billy/25-1kp/MoNaVLA/docs/v5/index.md:1)
- [docs/v5/exp05_08_summary.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp05_08_summary.md:1)

### 2026-04-15 오후

**Exp10이 “계획”에서 “정렬 분석/시각화” 단계로 넘어감**

- bbox grounding 트랙 문서 작성
- action alignment 분석 추가
- real dataset frame, expert-vla action mapping 시각화 추가
- H5 verification, sequence evaluation, batch analysis viewer로 확장

대표 커밋:

- `22135088` Report: V5 Exp10 BBox Training Report (2026.04.15)
- `8a470c8b` feat: add visualization and H5 verification scripts for exp10
- `3748d660` feat: complete navigation inference integration with visual documentation and H5 verification
- `ee290c8a` docs: add V5 Exp10 action alignment analysis and evaluation script update
- `55c2f934` docs: update roadmap for V5 Exp10 success and tactical alignment
- `a53e5036` docs: add full episode sequence evaluation for Exp10 (PMDM style)

대표 문서/산출물:

- [docs/v5/exp10/report.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp10/report.md:1)
- [docs/v5/exp10/action_alignment.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp10/action_alignment.md:1)
- [docs/reports/v5_experiment_report_20260415.md](/home/billy/25-1kp/MoNaVLA/docs/reports/v5_experiment_report_20260415.md:1)
- [docs/v5/exp10/index.html](/home/billy/25-1kp/MoNaVLA/docs/v5/exp10/index.html:1)

### 2026-04-16

**Exp11과 평가 프레임워크 정리가 시작됨**

- Exp11 config 추가
- batch analysis / full episode viewer 추가
- 계획 문서 규격화
- benchmark pipeline / V5 evaluation protocol / closed-loop sim plan 정리
- agent entrypoint 문서까지 추가되어, 다른 에이전트도 같은 진입점에서 프로젝트를 읽을 수 있게 됨

대표 커밋:

- `04fa0d4b` docs: add Exp10 batch analysis & full episode viewer, add Exp11 config
- `068927b1` docs: standardize project plan template and plan format
- `ee7b7da3` docs: define benchmark pipeline and V5 evaluation framework
- `c898e622` docs: add agent entrypoint guide

대표 문서:

- [docs/BENCHMARK_PIPELINE_DESIGN.md](/home/billy/25-1kp/MoNaVLA/docs/BENCHMARK_PIPELINE_DESIGN.md:1)
- [docs/v5/V5_EVALUATION_PROTOCOL.md](/home/billy/25-1kp/MoNaVLA/docs/v5/V5_EVALUATION_PROTOCOL.md:1)
- [docs/v5/V5_CLOSED_LOOP_SIM_PLAN.md](/home/billy/25-1kp/MoNaVLA/docs/v5/V5_CLOSED_LOOP_SIM_PLAN.md:1)
- [docs/AGENT_ENTRYPOINT.md](/home/billy/25-1kp/MoNaVLA/docs/AGENT_ENTRYPOINT.md:1)

### 2026-04-17

**Exp11 실패 원인 분석 -> Exp12 폐기 -> Exp13 설계로 이어짐**

- Exp11 LEFT/RIGHT sanity check 수행
- 좌측 계열을 우측으로 접는 구조적 bias가 문서화됨
- Exp12는 “instruction을 per-frame으로 맞추면 해결될 것”이라는 가설이었지만, oracle 성격 확인 결과 학습 의미가 약해 폐기
- Exp13은 instruction-conditioned action head로 architecture 자체를 바꾸는 방향으로 정리됨
- 동시에 fixed LR sanity benchmark scaffold를 추가해 이후 비교 기준을 고정하기 시작함

대표 문서:

- [docs/v5/V5_SANITY_ANALYSIS_20260417.md](/home/billy/25-1kp/MoNaVLA/docs/v5/V5_SANITY_ANALYSIS_20260417.md:1)
- [benchmarks/definitions/sanity_lr_4way_manifest.yaml](/home/billy/25-1kp/MoNaVLA/benchmarks/definitions/sanity_lr_4way_manifest.yaml:1)
- [benchmarks/definitions/splits/v5_lr_4way_sanity.yaml](/home/billy/25-1kp/MoNaVLA/benchmarks/definitions/splits/v5_lr_4way_sanity.yaml:1)
- [plan.md](/home/billy/25-1kp/MoNaVLA/plan.md:206)

## 4. Exp01~13 개발 흔적을 보는 방법

### 문서 기준

1. [docs/v5/index.md](/home/billy/25-1kp/MoNaVLA/docs/v5/index.md:1)
2. [docs/v5/exp01_11_analysis.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp01_11_analysis.md:1)
3. [docs/v5/V5_SANITY_ANALYSIS_20260417.md](/home/billy/25-1kp/MoNaVLA/docs/v5/V5_SANITY_ANALYSIS_20260417.md:1)
4. [plan.md](/home/billy/25-1kp/MoNaVLA/plan.md:1)

### 설정 파일 기준

1. [configs/mobile_vla_v5_exp01_discrete.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp01_discrete.json:1)
2. [configs/mobile_vla_v5_exp04_google_robot.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp04_google_robot.json:1)
3. [configs/mobile_vla_v5_exp09_8cls.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp09_8cls.json:1)
4. [configs/mobile_vla_v5_exp10_bbox.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp10_bbox.json:1)
5. [configs/mobile_vla_v5_exp11_google_robot_8cls.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp11_google_robot_8cls.json:1)
6. [configs/mobile_vla_v5_exp12_action_instr.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp12_action_instr.json:1)
7. [configs/mobile_vla_v5_exp13_instr_cond.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp13_instr_cond.json:1)

## 5. 현재 위치

현재 V5는 다음 상태에 있다.

- Exp04는 여전히 정책 baseline
- Exp09는 8-class 통합 실패 사례
- Exp10은 grounding 성공 사례
- Exp11은 left/right 붕괴가 드러난 최근 실패 사례
- Exp12는 학습 전 폐기된 중간 가설
- Exp13은 아직 학습 전이지만, instruction-conditioning을 action head에 명시적으로 넣는 첫 architecture 분기

즉 V5의 최근 흐름은 단순한 실험 반복이 아니라:

`foundation 정리 -> prompt/representation 최적화 -> 8-class 통합 -> grounding 검증 -> sanity benchmark 고정 -> architecture 수정`

로 보는 것이 맞다.

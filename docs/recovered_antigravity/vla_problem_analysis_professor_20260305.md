# RoboVLM-Nav 문제 종합 진단 리포트

Recovery source:
- `~/.gemini/antigravity/brain/5842cf4d-40a4-45aa-8443-0a1b79440638/vla_problem_analysis_professor.md`

Recovery note:
- 교수 관점 진단 문서로 보존 가치가 있어 복구했습니다.
- 현재 저장소 문서와 일부 내용이 겹치지만, 이 문서는 독립적 종합 진단 메모로 유지합니다.

> 관점: VLA 연구 랩 교수 입장에서의 독립적 진단
> 작성 기준: EXP-01 ~ V3-EXP07 전체 실험 이력 + `vla-driving` 인퍼런스 세션 분석
> 작성일: 2026-03-05

## Executive Summary

본 프로젝트는 VLM(Kosmos-2 기반) + Action Head 조합으로 실내 로봇 주행을 학습시키는 구조다. 17개 이상 실험에서 확인된 핵심 병목은 단일 버그가 아니라 모델, 데이터, 추론 파이프라인이 서로 얽힌 구조적 문제다.

| 축 | 핵심 증상 | 진단 | 위험도 |
| :--- | :--- | :--- | :--- |
| Model | Instruction grounding 붕괴, default action 고착 | Frozen VLM의 instruction embedding 동질화 | 매우 높음 |
| Dataset | LEFT/RIGHT 차별성 부족, 동일 출력 | 데이터 다양성 부족과 reactive policy 편향 | 높음 |
| Inference | Jetson 메모리 급등, 대상 실종 시 즉시 정지 | Base64 직렬화 누수와 object permanence 부재 | 높음 |

## 핵심 진단

### 1. 모델 축

- Frozen VLM Text Encoder 하에서 LEFT와 RIGHT가 거의 같은 hidden state를 생성
- Action head는 이를 분리하지 못해 mean action collapse가 발생
- `freeze_backbone + action head only` 가정은 로봇 주행 도메인에서 취약
- V3의 LoRA + classification 전환은 grounding 실패와 default action 고착 문제를 완화했지만 object permanence는 해결하지 못함

### 2. 데이터 축

- V3 데이터는 대부분 대상이 시야 내에 있는 상황 중심
- 대상이 시야를 벗어나면 recovery 동작보다 STOP 또는 최근 편향 행동으로 무너짐
- 이는 navigation 영역에서 드러난 imitation learning의 covariate shift 문제로 해석 가능
- Recovery 시나리오 또는 online data aggregation이 필요

### 3. 추론 축

- Jetson에서 Base64 직렬화 기반 이미지 전송은 메모리 사용량과 fragmentation을 키움
- HTTP + Base64 + PIL 변환 경로는 표준 VLA 대비 비효율
- direct image injection, `torch.inference_mode()`, 명시적 GC, 양자화, ROS2 직접 연동이 개선 후보

## 전략 우선순위

### 즉시 권장

- 추론 메모리 최적화
  - direct image injection
  - `torch.inference_mode()`
  - 명시적 `gc.collect()`
- state machine 오버레이
  - 대상 이탈 시 탐색 상태를 별도 소프트웨어 계층으로 보완

### 이번 주 권장

- recovery 시나리오 데이터 수집
- window and chunk 재최적화
- 오프라인 지표 외 평가 체계 보강
  - recovery rate
  - SPL
  - latency at Jetson
  - peak memory

### 중기 권장

- online DAgger
- optical flow 보조 입력
- contrastive instruction loss

## 결론

- LoRA로 frozen VLM 한계를 보완하고 classification head로 이산 행동을 안정화한 점은 연구 기여로 정리할 가치가 있음
- 하지만 오프라인 PM/DA 중심의 성능만으로는 설득력이 부족함
- 다음 단계는 성능 수치보다 먼저 측정 체계를 강화하는 것


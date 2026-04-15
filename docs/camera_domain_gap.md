# Memory: Camera Domain Gap Analysis

**Timestamp**: 2026-02-28 12:05
**Topic**: 학습용 카메라와 안정화된 추론 카메라 간의 심각한 도메인 격차 문제

## Issue Summary
* 20260129 에피소드 등 학습 데이터에 사용된 카메라는 파랗고 물빠진 색감(Mean RGB ~ [110, 137, 132])을 가지며, 실제 안정화된 로봇 카메라는 따뜻하고 명확한 색감과 어안 왜곡(Fisheye)을 가짐.
* 이 치명적 도메인 차이로 인해 VLM이 실제 주행 중 "본 적 없는" 환경으로 혼동하여 환각(Hallucination) 및 조향 오차가 발생함을 입증함.
* 16비트 모델 학습 정밀도의 문제가 아님. 완전히 데이터 센서 도메인 변화의 문제.

## Required Action (미팅 안건 내용)
* 기존 데이터의 폐기 혹은 `color_jitter`를 대체할 전면적인 Color-Matching 수식 재조정 필요.
* 향후 안정화된 로봇 카메라로 신규 주행 H5 데이터를 새롭게 수집하여 모델을 `exp07` 이후 버전으로 처음부터 다시 학습할 것 요망.

> **상세 리포트 참조**: `docs/camera_domain_gap_analysis_20260228.md`

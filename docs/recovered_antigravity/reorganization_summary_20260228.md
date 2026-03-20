# Project Reorganization Summary

Recovery source:
- `~/.gemini/antigravity/brain/accd1c60-4566-4ff1-9056-f4ec90296219/REORGANIZATION_SUMMARY.md`

Recovery note:
- 이 문서는 2026-02-28 시점의 구조 개편 메모입니다.
- 당시 경로명 일부는 현재 구조와 다를 수 있습니다.

작성일: 2026-02-28

## 개편 의도

프로젝트 구조를 체계화하고 스크립트 호환성을 확보하기 위해 디렉토리 역할을 분리했다.

## 당시 정리 원칙

- `scripts/`
  - 실행 가능한 bash 스크립트
- `tools/`
  - 분석, 검증, 모니터링용 Python 유틸리티
- `logs/`
  - 학습 로그, PID, 상세 기록
- `docs/`
  - 프로젝트 문서와 보고서
- `analysis/results/`
  - 실험 결과물

## 주요 작업 내용

- `train_v3_*`, `setup_*` 등 스크립트를 `scripts/` 로 이동
- 실행 위치와 무관하게 루트를 찾도록 `ROOT_DIR` 패턴 도입
- `logs/` 디렉토리 자동 생성 패턴 적용
- 분석용 스크립트 다수를 `tools/` 로 통합
- 루트의 산재한 JSON 결과물을 `analysis/results/` 로 이동
- `v3-exp07-lora` 명칭을 `RoboVLM-Nav` 로 반영
- 루트 문서를 `docs/` 하위로 이동

## 유지보수 팁

- 새 학습 스크립트는 `ROOT_DIR` 패턴을 재사용
- 일시적 분석 코드는 `tools/` 에 위치
- 핵심 로직은 당시 기준 `Mobile_VLA/` 또는 `RoboVLMs_upstream/` 의 적절한 서브디렉토리에 배치

## 상태

- 문서 원문 기준 상태는 완료
- 현재 저장소 기준으로는 이후 추가 개편과 병합이 있었으므로 역사적 기록으로 본다


# RoboVLM-Nav 디렉토리 감사 보고서

Recovery source:
- `~/.gemini/antigravity/brain/accd1c60-4566-4ff1-9056-f4ec90296219/directory_audit_20260301.md`

Recovery note:
- 당시 루트 구조를 기준으로 작성된 감사 보고서입니다.
- 현재 저장소 구조와 일부 항목은 달라졌을 수 있으므로, 역사적 구조 판단 자료로 사용합니다.

작성일: 2026-03-01

## 핵심 결론

- `third_party/RoboVLMs/` 를 canonical source로 본다
- `robovlm_nav/`, `configs/`, `scripts/`, `docs/`, `tools/` 는 정식 경로
- `RoboVLMs/`, `RoboVLMs_upstream_backup/`, `git_recovery_backup/`, `src/`, `core/`, `models/` 등은 legacy 또는 정리 후보로 분류

## RoboVLMs 버전 차이에 대한 판단

감사 당시 핵심 결론은 다음과 같았다.

- `third_party/RoboVLMs` 가 정식 최신 버전
- `RoboVLMs/` 는 V3-EXP01~03 시기의 임시 수정본
- 주요 차이는 dataset loader, datamodule, backbone LoRA 적용 위치, policy head 구현, trainer 추가 여부에 있음
- 결론적으로 `RoboVLMs/` 의 기능은 `third_party/RoboVLMs` 쪽으로 병합된 상태로 판단

## 권장 조치 요약

### 즉시 실행 가능하다고 본 항목

- `debug_*` 디렉토리 삭제
- `__pycache__` 삭제
- `config/` 삭제
- `memora/` 삭제
- `v3-exp04-lora/` 제거
- `test_images/` 를 정식 자산 경로로 이동

### 확인 후 실행 항목

- `src/` 를 legacy inference 묶음으로 이동
- `core/` 를 MCP integration 계열로 이동
- `models/` 를 분석 도구 영역으로 이동
- `whisper2/` 를 ROS2 계열로 이동
- `simpler_env_repo/` 를 `third_party` 로 정규화
- `RoboVLMs/`, `RoboVLMs_upstream_backup/` 삭제 검토

### 신중 처리 항목

- `git_recovery_backup/`
- `Robo+/`
- `result/`
- `ROS_action/`

## 거버넌스 규칙

감사 문서는 다음 불변 규칙을 제안했다.

1. 루트에 직접 `.py`, `.sh`, `.json` 생성 금지
2. `OmniDataset`, `OmniPolicy` 사용 금지
3. `Mobile_VLA/configs/` 경로 참조 금지, `configs/` 사용
4. `omni_robovlm` 대신 `robovlm_nav` 사용
5. `third_party/RoboVLMs/` 직접 수정 금지


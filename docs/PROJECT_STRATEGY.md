# 프로젝트 방향성 및 관리 전략 (Project Strategy & Management)

## 1. 개요 (Overview)
본 문서는 VLA-driving 프로젝트의 지속 가능한 발전과 효율적인 관리를 위한 전략적 로드맵을 정의합니다. `memora`에서 `menemory`로의 메모리 시스템 전환을 기점으로, 보다 체계적인 실험 관리와 데이터 중심의 모델 개선을 목표로 합니다.

## 2. 모델 고도화 전략 (VLA Refinement Strategy)
- **프롬프트 엔지니어링 (Goal-Centric Prompting):** 
  - 단순히 "바구니로 가라"는 명령 대신, 시각적 상태 변화(`until centered in frame`)를 포함한 구체적 Instruction 사용.
  - V3-EXP08에서 적용된 `center_goal` 프리셋을 표준화하여 모델의 종료 지점(End-state) 인식 능력 강화.
- **공간 인식 강화 (Spatial Grounding):**
  - "Left/Right side of the frame"과 같은 지칭어를 Instruction에 포함하여 VLM의 시각-언어 정렬(Alignment) 성능 극대화.
- **해상도 및 아키텍처:**
  - 현재 224x224 해상도의 한계를 극복하기 위해, 향후 고해상도 전략 적용 검토 (현재는 안정성 우선).

## 3. 관리 및 인프라 정책 (Management & Infrastructure)
- **메모리 시스템 통합:**
  - 레거시 `memora`를 제거하고 `menemory`를 단일 관리 도구로 사용.
  - 모든 주요 의사결정 및 실험 컨텍스트는 `menemory backup push`를 통해 Supabase에 동기화.
- **저장 공간 관리 (Disk Hygiene):**
  - 실험당 **최상위 2개 Epoch(val_loss 기준)** 및 `last.ckpt`만 유지하는 것을 원칙으로 함.
  - 주기적인 `cleanup_ckpts.py` 실행으로 디스크 풀(Full) 사태 방지.
- **디렉토리 거버넌스:**
  - `robovlm_nav/` 내부에 커스텀 코드를 격리하고, `third_party/RoboVLMs`는 본래의 소스 형태를 유지.
  - 모든 분석 리포트는 `docs/` 디렉토리에 날짜별/주제별로 정리.

## 4. 운영 프로세스 (Workflow)
1. **실험 설계:** 신규 실험 전 `configs/` 생성 및 Instruction 설계.
2. **학습 및 모니터링:** `scripts/` 내 전용 쉘 스크립트 실행 및 로그 모니터링.
3. **결과 분석:** TensorBoard 및 가중치 성능 확인 후 `docs/` 리포트 작성.
4. **동기화:** `git push` 및 `menemory backup push`로 팀원 간 컨텍스트 공유.

## 5. 향후 로드맵 (Upcoming Roadmap)
- [ ] V3-EXP08 (Center Goal) 학습 완료 및 성능 평가
- [ ] `robovlm_nav` 패키지 안정화 및 배포 구조 개선
- [ ] Jetson 하드웨어 배포용 경량화 모델(INT8/FP16) 가이드 업데이트
- [ ] 교수님 미팅용 데이터 기반 성능 분석 리포트 자동화

---
*Last updated: 2026-03-05 by Antigravity*

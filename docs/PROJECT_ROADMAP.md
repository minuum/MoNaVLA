# RoboVLM-Nav 프로젝트 로드맵 & 관리 가이드

> **최종 수정**: 2026-03-03  
> **상태**: ✅ 활성(Active)  
> **작성**: billy + Antigravity

---

## 🎯 프로젝트 개요

**RoboVLM-Nav**는 Vision-Language-Action(VLA) 모델 기반 모바일 로봇 네비게이션 시스템입니다.

- **모델 베이스**: Kosmos-2 (Microsoft) + LoRA fine-tuning
- **태스크**: 실내 장애물 회피 및 목표 지향 네비게이션 (9-class discrete action)
- **데이터셋**: 실내 basket_dataset (v2: 528 에피소드, 9,487 프레임)
- **아키텍처**: VLM backbone + LSTM Classification Head (NavPolicy)
- **배포 환경**: 로컬 서버 (billy@linux) → 원격 추론 서버 (soda@100.85.118.58)

---

## 📊 현재 최고 성능 모델

| 실험                           | 설명                                                      | Val Loss  | 비고        |
| ------------------------------ | --------------------------------------------------------- | --------- | ----------- |
| **V3-EXP07** (`v3-exp07-lora`) | 좌우통합 528ep + 역수 class_weight + LoRA(r=32) + lr=1e-5 | **0.044** | ✅ 현재 최고 |
| V3-EXP06                       | 이전 실험                                                 | -         | 비교용      |

### V3-EXP07 9-class 액션 매핑

```
0: STOP       1: FORWARD     2: BACKWARD (미사용)
3: LEFT       4: RIGHT       5: FORWARD-LEFT
6: FORWARD-RIGHT   7: BACK-LEFT (미사용)   8: BACK-RIGHT (미사용)
```

---

## 🗺️ 단기 로드맵 (2026 Q1)

### ✅ 완료
- [x] V3 분류 모델 학습 파이프라인 구축 (`NavPolicy`, `NavDataset`)
- [x] V3-EXP07 학습 완료 (val_loss=0.044, epoch 5)
- [x] 프로젝트 디렉토리 거버넌스 확립 (`docs/directory_governance.md`)
- [x] API 서버 V3 대응 (`robovlm_nav/serve/api_server_fix.py`)
- [x] 레거시 디렉토리 정리 (RoboVLMs/, config/, src/, core/, memora/ 등)
- [x] 원격 서버(soda) 모델 배포 및 인퍼런스 테스트 준비
- [x] `vla-driving` 브랜치 최신 인퍼런스 코드 & 세션 데이터 분석 완료 (`inference_session_analysis.md`)

### 🔄 진행 중
- [ ] 원격 서버(soda@100.85.118.58) 인퍼런스 테스트 완료 (15개 세션 수집됨)
- [ ] **Reactive behavior 해결**: 대상이 시야를 벗어날 시 조향이 멈추는 문제 (Object Permanence 부족) 개선 데이터 수집
- [ ] **Jetson 메모리 최적화**: Orin NX 16GB 한계 극복을 위한 `Direct Image Injection` (Base64 제거) 및 캐시 제거 적용

### 📋 단기 TODO (vla-driving 피드백 반영)
1. **인퍼런스 품질 검증 & 데이터 전략**
   - **문제 발견**: 동일 지시어("brown pot on the left")에 대해 특정 세션에서는 우편향 조향 발생, 대상 시야 손실 시 정지.
   - **대응**: Recovery/Search 시나리오 데이터 100+ 에피소드 추가 수집.
   
2. **V3-EXP08 설계** (개선 아이디어)
   - 재귀적 설정 로딩(`_load_config_recursive`) 기반 멀티 실험 관리.
   - P1: Base64 이미지 직렬화 제거하여 Jetson 메모리 오버헤드 50% 이상 감축 목표.
   - Window Size 튜닝 (8 → 4/12 비교).

3. **Jetson 배포 준비**
   - 모델 경량화 / 양자화 검토 (`tools/quantization/`)
   - JETSON_SETUP.md 업데이트

---

## 🗺️ 중장기 로드맵 (2026 Q2~)

### 아키텍처 발전 방향

```
현재:  Kosmos-2 backbone + LoRA + LSTM + Classification Head
         ↓ 검토 중
Option A: Continuous action head 재도입 (하이브리드)
Option B: 더 큰 VLM backbone (LLaVA, Qwen-VL 등)
Option C: Multi-task (Navigation + Object Detection 동시)
```

### 데이터 확장 계획
- 새 환경 데이터 수집 (실험실 바깥 복도, 외부 환경)
- B/BL/BR 클래스 보완 에피소드 수집
- 목표: 1,000+ 에피소드

### 평가 체계 정립
- PM Score (Path Merit): 경로 효율성
- DM Score (Distance Merit): 목표 도달 정확도
- 자동화된 로봇 평가 루프 구축

---

## 🛠️ 개발 워크플로

### 새 실험 추가 시

```bash
# 1. 설정 파일 생성
cp configs/mobile_vla_v3_exp07_lora.json configs/mobile_vla_v3_exp08_lora.json
# 2. 변경사항 수정 (exp_name, learning_rate 등)

# 3. 학습 실행
export PYTHONPATH="/home/billy/25-1kp/vla:/home/billy/25-1kp/vla/third_party/RoboVLMs"
python robovlm_nav/train.py --config configs/mobile_vla_v3_exp08_lora.json

# 4. 결과 push
git add configs/ logs/
git commit -m "feat: V3-EXP08 학습 설정 및 결과"
git push origin main
```

### 인퍼런스 서버 실행 (원격)

```bash
# 1. 코드 동기화 (로컬 → 원격)
rsync -avz --exclude='*.ckpt' --exclude='.git/' ... . soda@100.85.118.58:~/vla/

# 2. 원격 서버 서버 실행
ssh soda@100.85.118.58
cd ~/vla
export VLA_API_KEY="your_key"
export VLA_MODEL_NAME="v3_exp07_lora"
python robovlm_nav/serve/api_server_fix.py

# 3. 테스트
VLA_API_KEY="your_key" python scripts/test/test_inference_api.py
```

---

## 📁 디렉토리 구조 (요약)

> 전체 규칙은 `docs/directory_governance.md` 참조

```
vla/
├── robovlm_nav/          ← 핵심 패키지 (datasets, models, serve, trainer)
├── configs/              ← 학습/추론 설정 JSON
├── scripts/              ← 학습 실행 .sh, 유틸리티
├── third_party/RoboVLMs/ ← upstream (절대 직접 수정 금지)
├── tools/                ← 일회성 분석/양자화 도구
├── docs/                 ← 모든 문서 (이 파일 포함)
├── menemory/             ← AI 세션 메모리 CLI (독립 저장소)
└── .agent/               ← AI 에이전트 스킬, 워크플로
```

---

## 🔧 AI Agent(Antigravity) 활용 가이드

### 세션 시작 시 참조 문서 (순서대로)
1. `docs/PROJECT_ROADMAP.md` ← **이 문서** (현재 상태, 방향성)
2. `docs/directory_governance.md` (파일 배치 규칙)
3. `.agent/skills/directory-governance/SKILL.md` (파일 생성 전 체크리스트)

### Menemory 활용
- 세션 메모리: `menemory/` 독립 저장소 (`github.com/minuum/menemory`)
- `memora/`는 **레거시** → 삭제됨
- 세션 히스토리: `menemory/.menemory/sessions/` (gitignore됨)

### 연구 노트 작성 가이드
- 실험 결과: `docs/reports/v3_experiments_summary.md` 에 누적
- 미팅 노트: `docs/meeting_[날짜]/` 하위에 작성
- 코드 변경 이유는 커밋 메시지 + `docs/` 리포트로 보존

---

## 📞 연락 및 협업

- **主 개발자**: billy (billy@dev)
- **원격 서버**: soda@100.85.118.58 (추론/테스트 전용)
- **GitHub**: `origin` (주 저장소), `vla-driving` (Jetson 배포용)
- **Menemory**: `github.com/minuum/menemory` (세션 메모리 독립 저장소)

---

*이 문서는 프로젝트의 현재 상태와 방향성을 요약합니다. 새로운 실험이나 방향 전환이 있을 때 업데이트해주세요.*

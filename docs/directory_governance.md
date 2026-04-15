# RoboVLM-Nav 디렉토리 거버넌스 (Directory Governance)

> **최종 수정**: 2026-03-03  
> **상태**: ✅ 활성(Active)  
> **목적**: 프로젝트 디렉토리 구조의 일관성을 유지하고, AI Agent(Antigravity 포함)와 개발자 모두가 반드시 준수해야 할 파일 생성/배치 규격

---

## 🏗️ 공식 디렉토리 구조 (Canonical Structure)

```
/home/billy/25-1kp/vla/                 ← PROJECT ROOT
│
├── robovlm_nav/                        ← [핵심 패키지] RoboVLM-Nav 메인 코드
│   ├── datasets/                       #   - nav_dataset.py (NavDataset)
│   ├── models/                         #   - nav_policy.py (NavPolicy, NavPolicyRegression)
│   ├── serve/                          #   - inference_server*.py, inference_pipeline.py
│   └── train.py                        #   - 학습 진입점 (robovlms 네임스페이스 주입)
│
├── configs/                            ← [설정] 모든 학습/추론 JSON 설정 파일
│   ├── mobile_vla_v3_exp*.json         #   - V3 실험 설정
│   └── mobile_vla_v2_*.json            #   - V2 레거시 설정
│
├── scripts/                            ← [실행 스크립트] 학습/배포/유틸 쉘 스크립트
│   ├── train_v3_exp*.sh                #   - 학습 실행 스크립트
│   ├── sync/                           #   - Jetson 동기화 스크립트
│   └── cleanup_checkpoints.py         #   - 체크포인트 정리
│
├── third_party/RoboVLMs/               ← [서드파티] 원본 RoboVLMs 라이브러리 (주요 의존성)
│   └── robovlms/                       #   절대 직접 수정 금지. robovlm_nav/train.py에서 inject
│
├── tools/                              ← [도구] 일회성 분석/변환/양자화 스크립트
│   ├── quantization/                   #   - TensorRT, ONNX 변환
│   └── finetune_lora_20251106.py
│
├── docs/                               ← [문서] 모든 마크다운 문서
│   ├── directory_governance.md         #   ← 이 파일 (must-read)
│   ├── archives/                       #   - 레거시/구형 문서 보관
│   └── *.md
│
├── checkpoints/                        ← [체크포인트] 학습된 모델 파일
│   └── RoboVLMs/                       #   - 대용량 파일, .gitignore 처리
│
├── runs/                               ← [학습 로그] PyTorch Lightning 출력
│   └── [실험명]/                       #   - .gitignore 처리
│
├── logs/                               ← [로그] 실행 로그 텍스트 파일
│
├── analysis/                           ← [분석] 분석 결과, 시각화 스크립트
│
├── assets/                             ← [에셋] 이미지, 데이터 요약 JSON 등
│
├── tests/                              ← [테스트] 유닛/통합 테스트
│
├── docker/                             ← [도커] Dockerfile, docker-compose 파일
│
├── ros2_client/                        ← [ROS2] 로봇 ROS2 클라이언트 코드
│
├── .agent/                             ← [AI 에이전트] 스킬, 워크플로, 설정
│   ├── skills/
│   └── workflows/
│
└── [아래는 정리 대상 또는 Legacy 영역]
    ├── ROS_action/                     ← [LEGACY] 데이터셋 원본 보관 (30GB+, 이동 불가)
    ├── RoboVLMs/                       ← [LEGACY] third_party와 다른 버전 (병합 예정)
    ├── RoboVLMs_upstream_backup/       ← [LEGACY] 업스트림 백업 (삭제 예정)
    └── Robo+/                          ← [LEGACY] 이전 프로젝트 자료 (2.8GB)
```

---

## 📏 파일 배치 규칙 (Placement Rules)

| 파일 유형                  | 올바른 위치         | 절대 금지 위치                   |
| -------------------------- | ------------------- | -------------------------------- |
| 학습/추론 핵심 Python 코드 | `robovlm_nav/`      | 루트 `/`                         |
| JSON 설정 파일             | `configs/`          | `config/`, `Mobile_VLA/configs/` |
| 학습 실행 `.sh` 스크립트   | `scripts/`          | 루트 `/`, `third_party/`         |
| 일회성 분석/변환 스크립트  | `tools/`            | 루트 `/`, `scripts/`             |
| 마크다운 문서              | `docs/`             | 루트 `/` (거버넌스 문서 제외)    |
| 체크포인트 `.ckpt/.pt`     | `checkpoints/`      | 루트 `/`, `v3-exp04-lora/`       |
| 테스트 스크립트            | `tests/`            | 루트 `/`, `scripts/`             |
| Dockerfile                 | `docker/`           | 루트 `/`                         |
| 학습 로그/TensorBoard      | `runs/` (자동 생성) | 변경 불가                        |

---

## 🤖 AI Agent(Antigravity) 전용 규칙

### 파일 생성 시 반드시 확인할 체크리스트

```
[ ] 1. 배치 위치가 위 표의 규칙을 따르는가?
[ ] 2. 루트(/) 에 직접 .py / .sh / .json 파일을 생성하는가? → 금지
[ ] 3. configs/ 파일의 type 필드가 NavDataset / NavPolicy 를 사용하는가?
[ ] 4. 새 학습 스크립트의 PYTHONPATH 가 올바르게 설정되었는가?
         export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/third_party/RoboVLMs"
[ ] 5. third_party/RoboVLMs/ 를 직접 수정하는 대신 robovlm_nav/train.py 의 setattr 로 주입하는가?
[ ] 6. 50MB 이상 파일은 .gitignore 또는 Git LFS 대상인가?
[ ] 7. 임시 스크립트는 /tmp/ 에 저장하고 커밋하지 않는가?
```

### 명명 규칙 (Naming Convention)

- **Python 모듈**: `snake_case.py`
- **설정 파일**: `mobile_vla_[버전]_[실험명].json` (예: `mobile_vla_v3_exp07_lora.json`)
- **학습 스크립트**: `train_[버전]_[실험명].sh` (예: `train_v3_exp07_lora.sh`)
- **체크포인트**: `[실험명]_epoch[N].ckpt`
- **클래스**: `NavDataset`, `NavPolicy`, `NavPolicyRegression` (Omni 접두사 사용 금지)

---

## 🔄 RoboVLMs 버전 관계도

```
third_party/RoboVLMs/    ← ✅ 정식(canonical) 버전. 가장 최신 수정 포함
    ↓ diff 비교 완료
RoboVLMs/                ← ⚠️  5개 파일 차이 (아래 참고). 병합 후 삭제 예정
RoboVLMs_upstream_backup/← ❌  업스트림 원본 백업. 더 오래된 버전. 삭제 예정
```

### third_party vs RoboVLMs 주요 차이점 (2026-03-01 기준)

| 파일                       | third_party (최신)            | RoboVLMs (구형)                 |
| -------------------------- | ----------------------------- | ------------------------------- |
| `mobile_vla_h5_dataset.py` | Color Jitter/Random Crop 증강 | episode_filter, history_dropout |
| `base_backbone.py`         | LoRA 대상: `self.backbone`    | LoRA 대상: `self.model`         |
| `mobile_vla_policy.py`     | loss_velocity 계산            | loss_arm 계산                   |
| `base_trainer.py`          | MobileVLATrainer 포함         | 없음                            |
| `hybrid_action_head.py`    | ✅ 존재                        | ❌ 없음                          |
| `mobile_vla_trainer.py`    | ✅ 존재                        | ❌ 없음                          |

> **결론**: `third_party/RoboVLMs`가 정식 버전. `RoboVLMs/`는 V3-EXP01~03 실험 기간 임시 수정본.

---

## 🧹 정리 대상 디렉토리 현황

| 디렉토리                    | 크기  | 상태                                         | 권장 조치                                                     |
| --------------------------- | ----- | -------------------------------------------- | ------------------------------------------------------------- |
| `Robo+/`                    | 2.8GB | 이전 프로젝트 (TensorRT 실험 등)             | `docs/archives/Robo+_MobileVLA/`에 .md 보존, 나머지 삭제 후보 |
| `RoboVLMs/`                 | 7MB   | third_party와 5개 파일 차이 있는 구형 버전   | 병합 완료 후 삭제                                             |
| `RoboVLMs_upstream_backup/` | 18MB  | 업스트림 원본 백업                           | 삭제 예정                                                     |
| `git_recovery_backup/`      | 7GB   | Git 복구용 백업                              | 확인 후 삭제 예정                                             |
| `v3-exp04-lora/`            | 8MB   | 체크포인트 1개 (`merged_v3_exp04_best.ckpt`) | `checkpoints/` 로 이동 예정                                   |
| `memora/`                   | -     | **삭제 완료** (menemory로 통합)              | ✅ 완료                                                        |
| `menemory/`                 | 1.7MB | AI 세션 메모리 CLI (독립 git 저장소)         | 유지 (github.com/minuum/menemory)                             |
| `config/`                   | 352KB | README.md + scripts/만 있음 (JSON 없음)      | 삭제 or 병합 예정                                             |
| `models/`                   | 188KB | enhanced/medium_term 하위 분류               | `tools/` 또는 `analysis/` 로 정리                             |
| `src/`                      | 240KB | inference 관련 Python 파일들                 | `robovlm_nav/` 또는 `tools/`로 통합 예정                      |
| `core/`                     | 104KB | integration/mcp/mpc 하위                     | `src/` 또는 `robovlm_nav/`로 통합 대상                        |
| `debug_*/`                  | ~15MB | 디버그 이미지 파일들 (jpg)                   | 삭제 예정                                                     |
| `test_images/`              | 1.7MB | 테스트 이미지                                | `assets/` 로 이동 예정                                        |
| `result/`                   | 5.6GB | 분석 결과물                                  | 내용 확인 후 정리 필요                                        |
| `simpler_env_repo/`         | 23MB  | SimplerEnv 외부 레포 클론                    | `third_party/` 로 이동 예정                                   |
| `whisper2/`                 | 344KB | ROS2 + Whisper 음성인식 코드                 | `ros2_client/` 또는 `tools/` 통합                             |
| `Model_ws/`                 | 68KB  | 분류 불명                                    | 내용 확인 후 조치                                             |
| `ros2_client/`              | 12KB  | vla_api_client.py 1개                        | `tools/` 또는 `robovlm_nav/serve/` 통합                       |

---

## ⚡ 빠른 참조 (Quick Reference)

### 새 실험 추가 시 체크리스트
1. `configs/mobile_vla_v3_exp[NN]_[name].json` 생성
2. `scripts/train_v3_exp[NN]_[name].sh` 생성
3. `configs/*.json` 내의 `type` 필드: `NavDataset`, `NavPolicy` 사용
4. `robovlm_nav/train.py` 는 수정 없이 재사용

### 추론 서버 설정 시
- 설정 파일 경로: `configs/` 기준 (절대경로 사용 권장)  
  `CONFIG="/home/billy/25-1kp/vla/configs/mobile_vla_v3_exp07_lora.json"`
- PYTHONPATH 설정 필수:  
  `export PYTHONPATH="/home/billy/25-1kp/vla:/home/billy/25-1kp/vla/third_party/RoboVLMs"`

---

---

## 📋 관련 문서

- `docs/PROJECT_ROADMAP.md` — 프로젝트 방향성 & 로드맵 (최신 상태 요약)
- `docs/directory_governance.md` — **이 문서** (구조 규칙)
- `.agent/skills/directory-governance/SKILL.md` — AI Agent용 요약 체크리스트

*이 문서는 AI Agent(Antigravity)와 billy가 공동으로 관리합니다. 구조 변경 시 반드시 이 문서를 먼저 업데이트하세요.*

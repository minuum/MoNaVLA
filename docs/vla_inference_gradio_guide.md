# MoNaVLA Gradio Inference Dashboard 가이드

> **명령어:** `vla-inference-gradio` (별칭: `mona-inference-gradio`)
> **스크립트:** `scripts/gradio_inference_dashboard.py`
> **서버 역할:** Billy (Model Server) 전용

---

## 목차

1. [시스템 구성](#시스템-구성)
2. [사전 준비](#사전-준비)
3. [실행 방법](#실행-방법)
4. [인터페이스 설명](#인터페이스-설명)
5. [자주 발생하는 오류](#자주-발생하는-오류)
6. [V4 모델 체크포인트 경로](#v4-모델-체크포인트-경로)

---

## 시스템 구성

```
[Jetson Nano]  ←── ROS2 토픽 ───→  [Billy GPU 서버]
  카메라 발행                          API 서버 (FastAPI)
  로봇 제어                            Gradio 대시보드
                                       Kosmos-2 + LoRA
```

- **Jetson IP (Tailscale):** `$JETSON_TAILSCALE_IP`
- **Billy IP (Tailscale):** `$BILLY_TAILSCALE_IP`
- **API 서버 포트:** `8000`
- **Gradio 포트:** `7860`

---

## 사전 준비

### 1. 환경 변수 확인

```bash
# Billy 서버에서
vla-env   # 또는 mona-env

# 필수 환경 변수:
# VLA_PROJECT_DIR=/home/billy/25-1kp/MoNaVLA
# VLA_API_SERVER=http://localhost:8000
# VLA_API_KEY=...
# JETSON_TAILSCALE_IP=100.x.x.x
```

### 2. API 서버 시작 (Gradio 실행 전 필수)

```bash
vla-start    # API 서버 시작
vla-status   # 서버 상태 확인
vla-health   # Health check
```

### 3. 의존성 확인

```bash
pip install gradio requests opencv-python pillow
```

---

## 실행 방법

### 빠른 실행 (alias 사용)

```bash
# .bashrc에 vla-aliases가 로드된 경우
vla-inference-gradio

# 또는
mona-inference-gradio
```

> **참고:** alias가 없으면 `.vla_aliases`를 `source`하거나 아래 직접 실행.

### 직접 실행

```bash
cd /home/billy/25-1kp/MoNaVLA
python3 scripts/gradio_inference_dashboard.py
```

### 체크포인트 지정 실행

```bash
# V4 모델 사용 예시
python3 scripts/gradio_inference_dashboard.py \
  --checkpoint runs/v4_nav/kosmos/mobile_vla_v4_exp01/2026-03-13/v4-exp01-mobile-v3/epoch_epoch=00-val_loss=X.XXX.ckpt
```

### 브라우저 접속

```
http://localhost:7860
# 또는 외부에서: http://<BILLY_TAILSCALE_IP>:7860
```

---

## 인터페이스 설명

| 탭 | 설명 |
|----|------|
| **Live Inference** | 실시간 카메라 이미지 + 행동 예측 |
| **Batch Test** | H5 데이터셋 배치 평가 (PM/DM 지표) |
| **Config** | API 서버 주소, 모델 경로 동적 변경 |

### 행동 클래스 (9개)

| 인덱스 | 행동 | 설명 |
|--------|------|------|
| 0 | `stop` | 정지 |
| 1 | `forward` | 전진 |
| 2 | `backward` | 후진 |
| 3 | `turn_left` | 좌회전 |
| 4 | `turn_right` | 우회전 |
| 5 | `slide_left` | 좌측 이동 |
| 6 | `slide_right` | 우측 이동 |
| 7 | `turn_left_forward` | 전진 좌회전 |
| 8 | `turn_right_forward` | 전진 우회전 |

---

## 자주 발생하는 오류

### `Connection refused` (API 서버 미실행)

```bash
vla-start   # API 서버 먼저 시작
vla-health  # 헬스체크 확인
```

### `CUDA out of memory`

```bash
# 다른 GPU 프로세스 확인
nvidia-smi
# 학습 중인 경우 학습 일시 중지 후 실행
```

### `Model not loaded` (체크포인트 경로 오류)

API 서버 로그 확인:
```bash
vla-logs   # 또는 mona-logs
```

---

## V4 모델 체크포인트 경로

V4 학습 완료 후 **best 체크포인트** 기본 저장 위치:

```
runs/v4_nav/kosmos/mobile_vla_v4_exp01/
└── 2026-03-13/
    └── v4-exp01-mobile-v3/
        ├── epoch_epoch=00-val_loss=X.XXX.ckpt   ← best 후보
        ├── epoch_epoch=01-val_loss=X.XXX.ckpt
        ├── last.ckpt                              ← 마지막 체크포인트
        └── ...
```

V4 설정 요약:

| 항목 | 값 |
|------|---|
| 베이스 모델 | Kosmos-2-patch14-224 |
| 시작 가중치 | V3-EXP08 (epoch 07) |
| Action Space | 9-class discrete |
| Window Size | 4 frames |
| LoRA r / alpha | 32 / 64 |
| max_epochs | 10 |

---

## Alias 설치

`.vla_aliases`에 아래 내용이 추가되어 있어야 합니다:

```bash
# Gradio 추론 대시보드
alias vla-inference-gradio='cd $VLA_PROJECT_DIR && python3 scripts/gradio_inference_dashboard.py'
alias mona-inference-gradio='vla-inference-gradio'
```

설치 확인:
```bash
grep -i "gradio" ~/.bashrc $VLA_PROJECT_DIR/.vla_aliases 2>/dev/null
```

재설치:
```bash
cd $VLA_PROJECT_DIR && bash scripts/install_vla_aliases.sh
```

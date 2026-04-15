# RoboVLMs 코드 분석 및 수정 내역

## 📚 원본 레포지토리 정보

### GitHub 원본
- **URL**: https://github.com/Robot-VLAs/RoboVLMs
- **논문**: "Towards Generalist Robot Policies: What Matters in Building Vision-Language-Action Models"
- **저자**: Xinghang Li et al. (Tsinghua, ByteDance, CASIA, SJTU, NUS)
- **지원 백본**: Flamingo, Qwen, LLaVA, Kosmos-2, PaliGemma 등

---

## 🗂️ 로컬 폴더 구조 분석

### RoboVLMs (원본 백업)
```
origin: git@github.com-vla:minuum/vla.git
branch: feature/bsp-analysis-clean

역할: 원본 참조용 (수정 금지)
상태: 2024-10-30 시점의 fork
```

### RoboVLMs_upstream (수정본 - 실제 사용)
```
origin: minuum/RoboVLMs.git (private fork)
upstream: https://github.com/Robot-VLAs/RoboVLMs (원본)
branch: main

역할: Mobile VLA 프로젝트를 위해 수정된 코드
상태: 원본 + 커스텀 수정
```

### 결론
- **RoboVLMs**: minuum/vla 레포의 일부로 포함된 fork (분석 브랜치)
- **RoboVLMs_upstream**: Robot-VLAs/RoboVLMs의 fork + 커스텀 수정

---

## 🔧 수정된 파일 목록 (원본 대비)

### 1. 데이터 처리 (`robovlms/data/`)

| 파일 | 수정 내용 | 이유 |
|:---|:---|:---|
| `__init__.py` | MobileVLA 데이터셋 import 추가 | 새 데이터셋 등록 |
| `mobile_vla_action_dataset.py` | **신규** | ROS action 데이터 처리 |
| `mobile_vla_h5_dataset.py` | **신규** | H5 format 데이터셋 |
| `base_action_prediction_dataset.py` | 약간 수정 | 호환성 |
| `data_utils.py` | Mobile VLA 유틸 추가 | 2D action 처리 |

### 2. 모델 구조 (`robovlms/model/`)

| 파일 | 수정 내용 | 이유 |
|:---|:---|:---|
| `backbone/base_backbone.py` | **+328줄** | Kosmos-2 호환, action_token 수정 |
| `policy_head/mobile_vla_policy.py` | **신규** | 2D LSTM Action Head |
| `policy_head/hybrid_action_head.py` | **신규** | 방향+크기 분리 헤드 |
| `vlm_builder.py` | VLM 빌더 수정 | Kosmos-2 지원 강화 |

### 3. 학습 (`robovlms/train/`)

| 파일 | 수정 내용 | 이유 |
|:---|:---|:---|
| `mobile_vla_trainer.py` | **신규** | Mobile VLA 전용 트레이너 |
| `base_trainer.py` | 확장 | Mobile 태스크 지원 |

### 4. 유틸리티

| 파일 | 수정 내용 | 이유 |
|:---|:---|:---|
| `utils/lora_utils.py` | 신규 | LoRA 관련 유틸 |
| `jetson_vla_test.py` | 신규 | Jetson 배포 테스트 |

---

## 🏗️ 핵심 구조적 선택

### 선택 1: 백본 - Kosmos-2

**원본 지원 백본**:
- Flamingo ✅
- LLaVA ✅
- Qwen ⚠️
- Kosmos-2 ✅ (선택)
- PaliGemma ⚠️
- MoonDream ⚠️

**Kosmos-2 선택 이유**:
1. Grounding 능력 (이미지-텍스트 매칭)
2. 상대적으로 가벼움 (55M params)
3. HuggingFace에서 쉽게 접근 가능
4. RoboVLMs에서 "Fully tested" 표시

### 선택 2: Action Head - LSTM Decoder

**원본 지원 Policy Head**:
```
robovlms/model/policy_head/
├── base_policy.py       # MLPTanhHead 등
├── lstm_dec_pol.py      # LSTM Decoder
├── gpt_dec_pol.py       # GPT-style Decoder
└── diffusion_policy.py  # Diffusion Policy
```

**LSTM Decoder 선택 이유**:
1. 시계열 action 예측에 적합
2. 단순하고 안정적
3. 메모리 효율적 (Jetson 배포 고려)
4. RoboFlamingo에서 검증된 구조

### 선택 3: Action Space - Continuous

**원본 지원 Action Space**:
- Discrete (tokenization) - RT-2 스타일
- Continuous (regression) - 선택

**Continuous 선택 이유**:
1. 2D velocity (linear_x, linear_y)에 자연스러움
2. 이산화 시 정밀도 손실 우려
3. 단순한 태스크에 복잡한 tokenization 불필요

### 선택 4: Frozen VLM + LoRA

**원본 지원 Fine-tuning 방식**:
- Full Fine-tuning
- Frozen VLM + Action Head only
- LoRA Fine-tuning

**Frozen VLM 선택 이유**:
1. 제한된 데이터(500 에피소드)에서 효과적
2. 웹 사전 지식(left/right 개념) 보존
3. RoboFlamingo 논문에서 검증
4. LoRA 실험 결과 catastrophic forgetting 발생

---

## 🔄 코드 수정 상세

### base_backbone.py 주요 수정

#### 1. action_token 초기화 (핵심!)
```python
# 원본 (zeros)
self.action_token = nn.Parameter(torch.zeros(self.hidden_size))

# 수정 (Xavier)
std = (2.0 / (self.hidden_size + self.hidden_size)) ** 0.5
self.action_token = nn.Parameter(torch.randn(self.hidden_size) * std)
```
**이유**: zeros 초기화는 VLM self-attention에서 정보 전달 안 됨

#### 2. Kosmos-2 action_token_mask 처리
```python
# 추가된 코드
if action_token_mask.sum() == 0:
    # action_token_mask가 모두 False인 경우 처리
    action_hs = output_hs[:, -self.latent_num:]
```
**이유**: Kosmos-2의 특수 토큰 구조 호환

### mobile_vla_h5_dataset.py 주요 기능

```python
# abs_action 옵션
if self.abs_action:
    actions_tensor[:, 1] = torch.abs(actions_tensor[:, 1])
```
**이유**: 방향 제거로 태스크 단순화

---

## 📊 abs_action 성능 비교

### 실험 설계
| 설정 | abs_action=False | abs_action=True |
|:---|:---:|:---:|
| 학습 대상 | linear_y 전체 | \|linear_y\| (크기만) |
| 방향 결정 | 모델 예측 | 언어에서 추출 |
| 태스크 복잡도 | 높음 | 낮음 |

### 예상 결과 (학습 완료 후 확인)
| 지표 | abs_action=False | abs_action=True |
|:---|:---:|:---:|
| train_loss | 0.034 | ~0.05 |
| 방향 정확도 | 50% | **100%** (언어 추출) |
| MAE | 0.72 | **<0.35** (예상) |

### 결론
`abs_action=True`로 **태스크 분리**가 효과적
- 모델: 크기(magnitude) 학습
- 규칙: 방향(direction) 추출

---

## ✅ 진행 사항 정리

### 완료
- [x] RoboVLMs 원본 확인 및 문서화
- [x] 수정 내역 분석
- [x] 구조적 선택 근거 정리
- [x] abs_action 구현 및 학습 시작

### 진행 중
- [ ] abs_action 학습 완료 (Epoch 2/10)
- [ ] 성능 비교 분석

### 대기
- [ ] OpenVLA style 학습 (27 epochs)
- [ ] Hybrid head 통합
- [ ] 실제 로봇 테스트

---

## 📁 파일 구조 요약

```
RoboVLMs_upstream/robovlms/
├── data/
│   ├── mobile_vla_h5_dataset.py     # [신규] H5 데이터셋 + abs_action
│   └── mobile_vla_action_dataset.py # [신규] ROS action 데이터셋
├── model/
│   ├── backbone/
│   │   └── base_backbone.py         # [수정] action_token Xavier, Kosmos-2 호환
│   └── policy_head/
│       ├── mobile_vla_policy.py     # [신규] 2D LSTM Action Head
│       └── hybrid_action_head.py    # [신규] 방향+크기 분리
└── train/
    └── mobile_vla_trainer.py        # [신규] Mobile VLA 트레이너
```

---

작성일: 2025-12-09

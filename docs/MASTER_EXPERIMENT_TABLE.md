# 전체 실험 케이스 마스터 테이블

**작성일**: 2025-12-10 02:06  
**최종 업데이트**: 2025-12-10 11:54  
**총 케이스**: 16개 (조합 가능)  
**완료**: 6개 (37.5%)  
**진행 중**: 1개 (Case 9)

---

## 전체 케이스 통합 테이블

| Case | Data | Chunk | Strategy | 실험명 | Config 파일 | Checkpoint 위치 | 학습 상태 | Val Loss | Train Loss | Epochs | 비고 |
|:---:|:---:|:---:|:---:|:---|:---|:---|:---:|:---:|:---:|:---:|:---|
| **1** | L+R | 10 | baseline | frozen_lora_leftright_20251204 | Mobile_VLA/configs/...json | runs/.../frozen_lora_leftright_20251204/ | 완료 | 0.027 | ~0.027 | 10 | Baseline |
| **2** | L+R | 10 | fixed | kosmos2_fixed_20251209 | Mobile_VLA/configs/...json | runs/.../kosmos2_fixed_20251209/ | 완료 | 0.048 | ~0.034 | 10 | 성능 악화 |
| **3** | L+R | 10 | aug_abs | kosmos2_aug_abs_20251209 | Mobile_VLA/configs/...json | runs/.../kosmos2_aug_abs_20251209/ | 완료 | 0.050 | 0.044 | 10 | abs_action |
| **4** | R only | 10 | baseline | right_only_20251207 | Mobile_VLA/configs/...json | runs/.../right_only_20251207/ | 완료 | 0.016 | ~0.001 | 10 | 비교 기준 |
| **5** | L+R | 1 | baseline | no_chunk_20251209 | Mobile_VLA/configs/...json | runs/.../no_chunk_20251209/ | 완료 | **0.000532** | ~0.0001 | 7 (중단) | **최고 성능** |
| **6** | L+R | 10 | abs | - | 미생성 | - | 미수행 | - | - | - | abs_action only |
| **7** | L+R | 1 | fixed | - | 미생성 | - | 미수행 | - | - | - | 낮은 우선순위 |
| **8** | L+R | 1 | abs | no_chunk_abs_20251210 | Mobile_VLA/configs/...json | runs/.../no_chunk_abs_20251210/ | 완료 | 0.00243 | ~0.00005 | 5 | **2등** |
| **9** | L+R | 1 | aug_abs | no_chunk_aug_abs_20251210 | Mobile_VLA/configs/...json | runs/.../no_chunk_aug_abs_20251210/ | **진행 중** | - | - | - | **Tier 1, PID 1836576** |
| **10** | R only | 10 | fixed | - | 미생성 | - | 미수행 | - | - | - | 낮은 우선순위 |
| **11** | R only | 10 | abs | - | 미생성 | - | 미수행 | - | - | - | |
| **12** | R only | 10 | aug_abs | - | 미생성 | - | 미수행 | - | - | - | |
| **13** | R only | 1 | baseline | - | 미생성 | - | 미수행 | - | - | - | 참고용 |
| **14** | R only | 1 | fixed | - | 미생성 | - | 미수행 | - | - | - | |
| **15** | R only | 1 | abs | - | 미생성 | - | 미수행 | - | - | - | |
| **16** | R only | 1 | aug_abs | - | 미생성 | - | 미수행 | - | - | - | |

---

## 케이스별 상세 정보

### Case 1: Baseline (완료)

**실험명**: `mobile_vla_kosmos2_frozen_lora_leftright_20251204`

**설정**:
- Data: Left+Right 500 episodes
- fwd_pred_next_n: 10
- Strategy: Baseline (특수 전략 없음)

**결과**:
- Val Loss: 0.027
- Train Loss: 0.027
- 문제: 방향 구분 실패

**파일**:
- Config: `Mobile_VLA/configs/mobile_vla_kosmos2_frozen_lora_leftright_20251204.json`
- Checkpoint: `runs/mobile_vla_kosmos2_frozen_lora_leftright_20251204/`
- Log: `logs/train_*_20251204_*.log`

---

### Case 2: Xavier Init (완료)

**실험명**: `mobile_vla_kosmos2_fixed_20251209`

**설정**:
- Data: Left+Right 500 episodes
- fwd_pred_next_n: 10
- Strategy: Xavier initialization 수정

**결과**:
- Val Loss: 0.048 (악화)
- Train Loss: 0.034

**파일**:
- Config: `Mobile_VLA/configs/mobile_vla_kosmos2_fixed_20251209.json`
- Checkpoint: `runs/mobile_vla_kosmos2_fixed_20251209/`

---

### Case 3: Aug + Abs Action (완료)

**실험명**: `mobile_vla_kosmos2_aug_abs_20251209`

**설정**:
- Data: Left+Right 500 episodes (증강)
- fwd_pred_next_n: 10
- Strategy: abs_action + data augmentation

**결과**:
- Val Loss: 0.050
- Train Loss: 0.044
- Epochs: 10 완료

**파일**:
- Config: `Mobile_VLA/configs/mobile_vla_kosmos2_aug_abs_20251209.json`
- Checkpoint: `runs/mobile_vla_kosmos2_aug_abs_20251209/`
  - `epoch_epoch=06-val_loss=val_loss=0.050.ckpt`
  - `epoch_epoch=08-val_loss=val_loss=0.050.ckpt`
  - `epoch_epoch=09-val_loss=val_loss=0.050.ckpt`
- Log: `logs/train_aug_abs_20251209_111725.log`

---

### Case 4: Right Only (완료)

**실험명**: `mobile_vla_kosmos2_right_only_20251207`

**설정**:
- Data: Right 250 episodes
- fwd_pred_next_n: 10
- Strategy: Baseline

**결과**:
- Val Loss: 0.016
- Train Loss: ~0.001
- 문제: 일반화 부족

**파일**:
- Config: `Mobile_VLA/configs/mobile_vla_kosmos2_right_only_20251207.json`
- Checkpoint: `runs/mobile_vla_kosmos2_right_only_20251207/`

---

### Case 5: No Chunk (완료) ⭐

**실험명**: `mobile_vla_no_chunk_20251209`

**설정**:
- Data: Left+Right 500 episodes
- fwd_pred_next_n: 1
- Strategy: Baseline

**결과**:
- Val Loss: **0.000532** (최고)
- Train Loss: ~0.0001
- Epochs: 7 (SIGTERM 중단, Epoch 4 최적)

**파일**:
- Config: `Mobile_VLA/configs/mobile_vla_no_chunk_20251209.json`
- Checkpoint: `runs/mobile_vla_no_chunk_20251209/`
  - `epoch_epoch=03-val_loss=val_loss=0.001.ckpt`
  - `epoch_epoch=04-val_loss=val_loss=0.001.ckpt` ⭐ 최적
  - `epoch_epoch=05-val_loss=val_loss=0.001.ckpt`
  - `last.ckpt`
- Log: `logs/train_no_chunk_20251209_160112.log`

---

### Case 6-16: 미수행 케이스

**공통 사항**:
- Config 파일 미생성
- 학습 미수행
- 예상 결과는 변수 효과 분석 기반

---

## 성능 순위 (완료된 케이스)

| 순위 | Case | Val Loss | 상대 성능 |
|:---:|:---:|:---:|:---|
| **1** | Case 5 | 0.000532 | 기준 (최고) |
| 2 | Case 4 | 0.016 | 30배 높음 |
| 3 | Case 1 | 0.027 | 50배 높음 |
| 4 | Case 2 | 0.048 | 90배 높음 |
| 5 | Case 3 | 0.050 | 94배 높음 |

---

## 데이터셋 정보

**위치**: `ROS_action/mobile_vla_dataset/`

**총 에피소드**: 500개
- Left 방향: 250개 (`*left*.h5`)
- Right 방향: 250개 (`*right*.h5`)

**필터 패턴**:
- Left+Right: `episode_20251*.h5` (500개)
- Right only: `*right*.h5` (250개)

**각 에피소드 구조**:
```python
{
  'images': (T, 720, 1280, 3),  # RGB 이미지
  'actions': (T, 3),              # [linear_x, linear_y, angular_z]
  'language_instruction': (T,),   # 언어 명령
  'action_event_types': (T,)
}
```

---

## Config 파일 템플릿

**기본 경로**: `Mobile_VLA/configs/`

**필수 설정 항목**:
```json
{
  "exp_name": "mobile_vla_[실험명]",
  "model": "kosmos",
  "fwd_pred_next_n": 1 or 10,
  "window_size": 8,
  "batch_size": 1,
  "learning_rate": 0.0001,
  "max_epochs": 10,
  "train_dataset": {
    "episode_pattern": "episode_20251*.h5" or "*right*.h5"
  }
}
```

---

## Checkpoint 저장 위치 패턴

```
runs/[실험명]/kosmos/mobile_vla_finetune/[날짜]/[실험명]/
  ├── epoch_epoch=XX-val_loss=val_loss=X.XXX.ckpt
  ├── last.ckpt
  └── [실험명]/
      └── version_0/
          ├── hparams.yaml
          └── events.out.tfevents.*
```

---

## 학습 로그 위치

```
logs/train_[실험타입]_[날짜]_[시간].log
```

**예시**:
- `logs/train_no_chunk_20251209_160112.log`
- `logs/train_aug_abs_20251209_111725.log`
- `logs/train_right_only_20251207_004831.log`

---

## 다음 실험 우선순위

### Tier 1: 필수 실험

**Case 8**: L+R + No Chunk + Abs Action
- 예상 효과: 최고 성능 + 방향 정확도 보장
- Config 생성 필요: `mobile_vla_no_chunk_abs_20251210.json`
- 소요 시간: 4 epochs (~4-5시간)

**Case 9**: L+R + No Chunk + Aug+Abs
- 예상 효과: 데이터 증강 + 최고 전략
- Config 생성 필요: `mobile_vla_no_chunk_aug_abs_20251210.json`
- 소요 시간: 4 epochs (~4-5시간)

### Tier 2: 참고 실험

**Case 13**: R only + No Chunk + Baseline
- 목적: 단순화 극대화 효과 확인
- 예상: Val Loss ~0.0001
- 한계: 일반화 부족

### Tier 3: 낮은 우선순위

Case 7, 10-12, 14-16: 효과 미미할 것으로 예상

---

**문서 작성**: 2025-12-10 02:06  
**최종 업데이트**: 실험 완료 시마다 갱신  
**관리자**: 연구팀

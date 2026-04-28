# Plan: Overfit Debug + base_backbone + Recognition Proof
작성일: 2026-04-28

---

## 현재 상황 요약

- Exp32/35/36 모두 422/422 FORWARD collapse, val_loss ≈ 6.535
- **이상**: 8-class 균일 예측 CE = ln(8) = 2.08인데 실측 6.535 → loss 계산 어딘가 틀렸을 가능성
- **가설 A**: backbone frozen 상태에서 features가 거의 동일 → head가 majority class(FORWARD)만 예측
- **가설 B**: val_loss 자체가 잘못 계산됨 (fwd_pred_next_n 불일치, attention mask 오동작 등)

---

## Item 1: Tiny Overfit Debug (TODO 6)

### 목표
"action head가 left action을 전혀 배울 수 없는가?"를 확인. 이게 배울 수 없다면 → loss/head 버그. 배울 수 있다면 → backbone feature가 문제.

### 접근 (Exp37: 1-episode overfit)

| 항목 | 설정 |
|---|---|
| 데이터 | `left_left` 3개 에피소드 (가장 순도 높음) |
| train/val | train 전체 (overfit용, val없이) |
| backbone | frozen (head-only, exp21 계열 그대로) |
| epochs | 30 |
| fwd_pred_next_n | 1 |
| 그라운딩 aux | 완전 비활성화 (bbox_weight=0, coarse_weight=0) |

### 수집할 수치
1. epoch별 `train_loss` — 2.08 아래로 내려가는가?
2. 마지막 epoch PM/DM eval — LEFT logit이 FORWARD보다 높아지는가?
3. gradient norm (action head linear layer) — 0이 아닌가?

### 판정 기준

| 결과 | 의미 | 다음 행동 |
|---|---|---|
| train_loss → 0 (overfit 성공) | head는 정상, backbone feature 문제 | Exp38: backbone unfreeze (last4 + LR 낮춤) |
| train_loss ↓ but stops > 2.0 | partial learning, feature 비슷하지만 분리 가능 | 더 작은 subset or 더 많은 epochs |
| train_loss stays ≈ 6.5 | loss 계산 자체 버그 | loss 코드 직접 디버그 |

### 수정 파일
- `configs/mobile_vla_v5_exp37_overfit_left3ep_30ep.json` (신규)

### 코드 변경 없음 (config만 추가)

---

## Item 2: base_backbone.py 커밋 여부 결정

### 변경 내용
`third_party/RoboVLMs/robovlms/model/backbone/base_backbone.py`에 2개 메서드 추가:
- `_get_text_decoder_layers()` — text decoder layer 목록 반환
- `_resolve_lora_target_modules()` — last-N LoRA target 계산

### 선택지

**A. 커밋 (현행 유지)**
- 장점: 이미 동작, Exp35/36에 검증됨
- 단점: 금지 규칙("RoboVLMs 수정 금지") 위반 형식
- 현실: 이 repo는 upstream 기여 없는 local fork → 실질적 문제 없음

**B. robovlm_nav 안으로 이동 (mixin 패턴)**
- `robovlm_nav/models/backbone/nav_backbone_mixin.py` 생성
- `BaseRoboVLM` 상속 후 두 메서드 추가
- base_backbone.py revert
- 단점: BaseRoboVLM 인스턴스 교체 필요 (다른 코드 영향)

**추천: A** — local fork이고 이미 검증됨. CLAUDE.md 규칙은 "upstream 변경 없이 local 실험용 수정만" 의미로 해석.

### 커밋 메시지 초안
```
feat: add last-N LoRA resolver to base_backbone (local patch)

_get_text_decoder_layers() and _resolve_lora_target_modules()
enable lora_decoder_layers config for Exp35/36.
```

---

## Item 3: Recognition Proof (TODO 1)

### 현재 상태
- `docs/v5/bbox_truth_initial18.json` 18개 프레임 → 전부 `pending` 상태
- 스크립트: `scripts/analysis/evaluate_v5_bbox_truth.py` 완성됨
- 단, human review (bbox 좌표 입력) 없이는 IoU 계산 불가

### 접근
1. 먼저 현재 스크립트로 실행해서 어떤 출력이 나오는지 확인
2. 18개 프레임 이미지를 직접 열어서 basket bbox 좌표 레이블링
3. evaluate 재실행 → detection_recall / mean_iou 출력

### 필요한 것
- 사용자가 직접 이미지를 보고 bbox 입력해야 함 (Claude 불가)
- OR: 기존 grounding 모델(Pure HF Kosmos-2)로 자동 bbox 예측 → evaluate

**추천: 자동 grounding 예측 먼저 실행** (Exp10에서 grounding은 IoU 0.87 달성한 바 있음)

---

## 실행 순서

- [ ] **Item 1**: Exp37 config 생성 + 학습 실행 (tmux v5train)
- [ ] **Item 1**: 학습 완료 후 PM eval 실행, 수치 기록
- [ ] **Item 2**: A 선택 시 base_backbone.py + 관련 파일 커밋
- [ ] **Item 3**: grounding 자동 예측 스크립트 실행

---

## 변경될 파일

| 파일 | 변경 내용 |
|---|---|
| `configs/mobile_vla_v5_exp37_overfit_left3ep_30ep.json` | 신규 생성 |
| `third_party/RoboVLMs/.../base_backbone.py` | 커밋 (수정 없음, 현행 반영) |
| `robovlm_nav/` 관련 수정본들 | 커밋 |

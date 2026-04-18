# Plan: Exp11 - Option B (Google-Robot Backbone + 8-class)
작성일: 2026-04-16

## 1. 목표
- 해결하려는 문제: Exp04의 Google-Robot 백본 성능을 유지하면서 8-class 액션 공간(ROT_L/ROT_R 포함)으로 확장한다.
- 기대 결과: 8-class 학습 설정을 안정적으로 구성하고, PM/DM 기준에서 Exp04와 Exp09 대비 의미 있는 비교가 가능해진다.
- 이번 문서 단계:
  - [x] 리서치만 완료
  - [x] 구현 전 승인 대기
  - [ ] 승인 후 구현 예정

> 방향 확정 (2026-04-16): Exp04 백본 + Exp09 액션 공간 통합. 아직 아무도 안 해본 조합.

## 2. 배경 / 현재 상태
- 현재 동작: Exp04는 6-class Google-Robot 기반으로 가장 낮은 `val_loss=0.776`을 기록했다.
- 문제 증상: 현재 최선 모델은 6-class라서 `ROT_LEFT`, `ROT_RIGHT`를 직접 학습하지 못한다.
- 관련 실험/이전 작업:
  - Exp04: Google-Robot pretrain, 6-class, 현재 최선
  - Exp09: 8-class 액션 공간 실험
  - Exp11: Exp04 백본과 Exp09 액션 공간의 통합 시도
- 참고 문서 / 커밋 / 이슈:
  - `configs/mobile_vla_v5_exp04_google_robot.json`
  - `docs/v5/exp09/report.md`
  - `configs/mobile_vla_v5_exp11_google_robot_8cls.json`

## 3. 리서치 요약
### 3.1 확인한 코드 / 데이터 / 문서
- 파일:
  - `robovlm_nav/datasets/nav_h5_dataset_impl.py`
  - `configs/mobile_vla_v5_exp04_google_robot.json`
  - `configs/mobile_vla_v5_exp11_google_robot_8cls.json`
  - `robovlm_nav/serve/inference_server.py`
- 확인한 핵심 동작:
  - `num_classes == 6`일 때만 6-class 병합 매핑이 적용된다.
  - `num_classes == 8`이면 기존 0~7 레이블이 그대로 유지된다.
  - V5 데이터셋에는 `center_straight`, `left_straight`, `right_straight` 및 곡선 경로 타입이 섞여 있다.
- 기존 패턴 / 제약:
  - Exp04는 Google-Robot 백본을 그대로 유지해야 한다.
  - `center_straight`는 정보량이 낮고 FORWARD bias를 심화시킨다.
  - ROT_L/R는 희귀 클래스라 class weight 보정이 필요하다.

### 3.2 핵심 근거
- 근거 1: 8-class는 코드 수정 없이 데이터셋 레이어에서 이미 지원된다.
- 근거 2: `left_straight`, `right_straight`에는 각 에피소드 첫 프레임의 ROT 신호가 포함되어 있다.
- 근거 3: `center_straight`만 제외하면 130개 에피소드에서 ROT_L/R 각 20프레임을 확보할 수 있다.

```python
if self.num_classes == 6:
    mapping = {0: 0, 1: 1, 2: 2, 4: 2, 3: 3, 5: 3, 6: 2, 7: 3}
    cls_labels = [mapping.get(int(l), 0) for l in cls_labels]
# num_classes == 8이면 이 블록 스킵 -> 0~7 그대로 사용
```

### 3.3 데이터 구조 확정
#### 에피소드 타입별 실제 분포

| 타입 | ep수 | 프레임 | 주요 액션 |
|------|------|--------|---------|
| center_straight | 20 | 280 | FWD 100% - 제외 |
| left_straight | 20 | 360 | ROT_R 1프레임 + FWD 나머지 |
| right_straight | 20 | 360 | ROT_L 1프레임 + FWD 나머지 |
| center_left | 15 | 270 | FWD+L/FWD+R 위주 |
| center_right | 15 | 270 | FWD+L/FWD+R 위주 |
| left_left | 15 | 277 | FWD+L/LEFT 위주 |
| left_right | 15 | 285 | FWD+R 위주 |
| right_left | 15 | 283 | FWD+L 위주 |
| right_right | 15 | 241 | FWD+R/RIGHT 위주 |

#### ROT의 의미

```text
left_straight  에피소드: [ROT_R, FWD, FWD, FWD, ...]
right_straight 에피소드: [ROT_L, FWD, FWD, FWD, ...]
center_straight 에피소드: [FWD, FWD, FWD, ...]
```

- ROT = 첫 장면에서 바스켓 위치를 보고 정렬 회전하는 신호
- 에피소드당 정확히 1프레임만 등장
- `exclude_path_types = ["center_straight"]`로 확정
- 총 130ep 사용: 90 non-straight + 20 left_straight + 20 right_straight

#### 실제 클래스 분포 (130ep 기준)

| 클래스 | 프레임 | 비율 | weight |
|--------|--------|------|--------|
| 0 STOP | 0 | 0% | 1.0 |
| 1 FORWARD | ~1,620 | ~65% | 0.5 |
| 2 LEFT | 60 | ~2.4% | 10.0 |
| 3 RIGHT | 46 | ~1.9% | 10.0 |
| 4 FWD+L | 255 | ~10.2% | 4.0 |
| 5 FWD+R | 270 | ~10.8% | 4.0 |
| 6 ROT_L | 20 | ~0.8% | 50.0 |
| 7 ROT_R | 20 | ~0.8% | 50.0 |

## 4. 제안 변경 사항
### 4.1 변경 개요
- 무엇을 바꾸는가:
  - Exp04 parent를 기반으로 하는 Exp11 8-class config를 사용한다.
  - `window_size`, `num_classes`, `class_weights`, `exclude_path_types`를 재설정한다.
- 무엇은 바꾸지 않는가:
  - `nav_h5_dataset_impl.py`의 8-class 지원 로직은 수정하지 않는다.
  - Google-Robot pretrained backbone 자체는 바꾸지 않는다.

### 4.2 변경 파일
1. `configs/mobile_vla_v5_exp11_google_robot_8cls.json`
   - `num_classes: 8`
   - `window_size: 8`
   - `learning_rate: 5e-5`
   - `max_epochs: 20`
   - `class_weights: [1.0, 0.5, 10.0, 10.0, 4.0, 4.0, 50.0, 50.0]`
   - `exclude_path_types: ["center_straight"]`
2. 코드 수정 없음
   - 8-class 지원 코드는 이미 존재하므로 config만 추가한다.

### 4.3 구현 방식
1. Exp04 parent config를 기준으로 Exp11 전용 override 작성
2. 데이터셋 로딩이 8-class로 정상 동작하는지 확인
3. 학습 후 PM/DM 기준으로 Exp04, Exp09와 비교

```json
{
  "parent": "configs/mobile_vla_v5_exp04_google_robot.json",
  "exp_name": "v5-exp11-google-robot-8cls",
  "task_name": "mobile_vla_v5_exp11",
  "num_classes": 8,
  "window_size": 8,
  "learning_rate": 5e-5,
  "max_epochs": 20
}
```

### 4.4 핵심 비교

| 항목 | Exp04 | Exp09 | Exp11 |
|------|-------|-------|-------|
| 백본 | Google-Robot pretrain | V4 ckpt | Google-Robot |
| num_classes | 6 | 8 | 8 |
| window_size | 6 | 8 | 8 |
| data_dir | v5_data_bak (54ep) | mobile_vla_dataset_v5 (150ep) | mobile_vla_dataset_v5 |
| exclude_straight | 전체 straight 제외 | 미적용 | center_straight만 제외 |
| learning_rate | 1e-4 | 2e-5 | 5e-5 |
| max_epochs | 30 | 5 | 20 |

## 5. 검증 계획
- 검증 명령:
  - 데이터셋 클래스 분포 출력
  - Exp11 config 로딩 확인
  - 학습 후 PM/DM 평가 스크립트 실행
- 성공 기준:
  - 8-class 데이터 로딩이 정상 동작할 것
  - ROT_L/R가 학습 대상에 포함될 것
  - Exp04 대비 심각한 성능 붕괴 없이 비교 가능한 결과가 나올 것
- 수동 확인 항목:
  - 학습 로그에서 클래스 편향 확인
  - PM/DM 결과에서 FORWARD bias 지속 여부 확인
  - ROT_L/R 예측이 실제로 등장하는지 확인

## 6. 리스크 / 트레이드오프
| 리스크 | 원인 | 대응 |
|--------|------|------|
| ROT_L/ROT_R 학습 안 됨 | 희귀 클래스 분포 | 학습 전 클래스 분포 재확인, weight 유지 |
| window_size=8 OOM | 시퀀스 길이 증가 | batch_size 축소 또는 window_size=6 재검토 |
| val_loss 악화 | 8-class가 더 어려운 문제 | epoch 증가 또는 lr 조정 |
| FORWARD 과다 출력 | class_weight 부족 | FORWARD weight를 추가 조정 |

## 7. 롤백 / 대안
- 롤백 방법:
  - Exp11이 실패하면 Exp04 설정으로 복귀해 baseline 유지
- 대안 A:
  - window_size를 6으로 낮춰 메모리 안정성을 우선 확보
- 대안 B:
  - FORWARD weight를 더 낮추고 ROT_L/R weight를 추가 상향

## 8. 작업 순서 가이드 (DO NOT EXECUTE YET)
1. 데이터셋 클래스 분포 재확인
2. `configs/mobile_vla_v5_exp11_google_robot_8cls.json` 검토
3. 학습 실행
4. PM/DM 검증 및 Exp04, Exp09와 비교

## 9. 완료 체크리스트
- [x] 리서치 완료
- [x] 사용자 피드백 반영
- [x] 구현 승인 획득
- [x] 구현 완료
- [x] 검증 완료 (2026-04-16)
- [ ] 결과 문서화

## 9-1. 검증 결과 요약 (2026-04-16)

### eval 버그 수정 내역
- **Bug 1**: `parse_logits` t=-1 vs `parse_gt` t=0 시간 불일치 → `parse_logits(t=0)`으로 수정
- **Bug 2**: `load_val_dataset()` window_size/train_split 하드코딩 → CLI 변수 사용
- **Bug 3**: `parse_gt` `ac[0, -1, 0]` → `ac[0, 0, 0]` (ROT는 에피소드 첫 프레임에만 존재)

### PM/DM 결과 (epoch=14, val_loss=1.010)

| val set | PM | FORWARD | RIGHT | FWD+L | FWD+R | LEFT | TURN_L |
|---------|-----|---------|-------|-------|-------|------|--------|
| exclude_center_straight (203 seq) | 58.62% | 87.8% | 50% | 50% | 36.7% | 0% | 0% |
| full 150ep (181 seq) | 65.19% | 93.7% | 50% | 50% | 38.6% | 0% | 0% |

### 미해결 문제 → Exp12로 이어짐
- LEFT=0%: 단일 프레임 시각적으로 LEFT/RIGHT 구분 불가 (basket이 양쪽 모두 화면 중앙)
- 원인: instruction이 에피소드 전체 고정 → FORWARD frame 97%에도 "Navigate to the left" 붙어서 모델이 "left instruction → FORWARD" 학습
- TURN_L/R 전혀 예측 안 됨 (20 frames × 14 epochs 부족, 하지만 one-shot 특성상 허용)

---

# Exp12: Action-Aware Instruction (per-frame 정렬)
작성일: 2026-04-17

## 목표
LEFT=0% 해결. instruction을 에피소드 단위(path_type)에서 프레임 단위(action_aware)로 전환.

## 핵심 분석
- `action_aware_train` preset 이미 존재하나 `target_idx = window_size = 8` 사용 → frame 8(FORWARD) 기준 instruction 생성 → t=0 GT와 불일치
- 수정: `target_idx = 0` → t=0 action과 instruction 정렬

## 변경 파일
1. `robovlm_nav/datasets/nav_h5_dataset_impl.py` line ~221
   - `target_idx = min(self.window_size, len(actions) - 1)` → `target_idx = 0`
2. `configs/mobile_vla_v5_exp12_action_instr.json`
   - parent: exp11 config
   - `instruction_preset: "action_aware_train"` (train)
   - instruction_override 제거

## 승인 상태
- [x] 방향 승인 (사용자: "B ㄱㄱ", 2026-04-17)
- [x] 구현 완료
- [x] Oracle 테스트 결과: 모델이 instruction text 완전히 무시 → 학습 의미 없음 → 폐기

## Exp12 폐기 이유
- Oracle 테스트 (Exp11 + GT instruction): GT instruction 주입해도 LEFT=0% 동일
- Exp01 (pure HF Kosmos-2) oracle 테스트도 동일 결과
- 근본 원인: `MobileVLAClassificationDecoder`가 action token hidden states만 사용, instruction text token은 transformer attention으로 이론상 접근 가능하나 실제로 무시됨
- 결론: per-frame instruction 정렬만으로는 효과 없음, architecture 수정 필요 → Exp13

---

# Exp13: Instruction-Conditioned Action Head (Architecture B)
작성일: 2026-04-17

## 목표
action head에 instruction embedding을 명시적으로 연결 (additive conditioning).
Oracle test에서 확인된 "instruction 무시" 문제를 architecture 레벨에서 해결.

## 핵심 원인 분석 (리서치 결과)

### 실제 forward 경로 (발견)
```
forward_action → forward_continuous (action_space 기본값="continuous")
  → Kosmos-2 LM (output_hidden_states=True)
  → output.hidden_states[-1] 에서 action token 위치 추출
  → action_hs shape: (bs, ws=8, latent=1, embed_dim=2048)
  → MobileVLAClassificationDecoder.forward(tok_seq=action_hs)
    → rearrange → (bs, ws, 2048)
    → LSTM(input=2048, hidden=1024, layers=4)
    → logits: (bs, ws, fwd_pred_next_n, num_classes)
```

### instruction이 무시되는 이유
- action token(1개 learnable vector)은 transformer를 통해 instruction tokens에 attend 가능
- 하지만 image tokens(64개)가 압도적 → action token이 instruction보다 image에 집중
- Oracle test 확인: GT instruction 주입 시에도 예측 불변 (Exp11 + Exp01 모두)

### 해결 전략
- word embedding에서 instruction embedding 직접 추출
- `instr_proj`: Linear(2048 → 2048)
- LSTM input에 additive conditioning: `tok_seq = tok_seq + instr_feat`
- `third_party/RoboVLMs` 수정 불필요 (subclass + kwargs 패턴)

## 변경 파일 목록

### 1. `robovlm_nav/models/nav_robokosmos.py` (NEW)
```python
class NavRoboKosMos(RoboKosMos):
    def forward_continuous(self, vision_x, lang_x, attention_mask=None, **kwargs):
        # instruction embedding: word embedding → mean pool → (bs, 2048)
        if lang_x is not None:
            instr_embeds = self.word_embedding(lang_x)  # (bs, text_len, 2048)
            self._instr_emb_cache = instr_embeds.mean(dim=1).detach()
        else:
            self._instr_emb_cache = None
        return super().forward_continuous(vision_x, lang_x, attention_mask=attention_mask, **kwargs)

    def _forward_action_head(self, action_tokens, action_labels, action_mask, mode="train", **kwargs):
        instr_emb = getattr(self, '_instr_emb_cache', None)
        if instr_emb is not None:
            kwargs['instruction_emb'] = instr_emb
        return super()._forward_action_head(action_tokens, action_labels, action_mask, mode=mode, **kwargs)
```

### 2. `robovlm_nav/models/policy_head/nav_policy_impl.py` (MODIFY)
`MobileVLAClassificationDecoder.__init__` 추가:
```python
instr_in_features = kwargs.get('instr_in_features', None)
if instr_in_features is not None:
    self.instr_proj = nn.Linear(instr_in_features, in_features * latent)
else:
    self.instr_proj = None
```

`MobileVLAClassificationDecoder.forward` 수정 (LSTM 직전):
```python
instruction_emb = kwargs.get('instruction_emb', None)
if instruction_emb is not None and self.instr_proj is not None:
    instr_feat = self.instr_proj(instruction_emb.to(tok_seq.dtype))  # (bs, in_features)
    instr_feat = instr_feat.unsqueeze(1).expand_as(tok_seq)           # (bs, ws, in_features)
    tok_seq = tok_seq + instr_feat
```

### 3. `robovlm_nav/train.py` (MODIFY)
```python
from robovlm_nav.models.nav_robokosmos import NavRoboKosMos
setattr(robovlms.model.backbone, "RoboVLM-Nav", NavRoboKosMos)
setattr(robovlms.model.backbone, "RoboKosMos", NavRoboKosMos)
```

### 4. `scripts/test_v5_pm_dm.py` (MODIFY)
동일하게 `NavRoboKosMos` 주입.

### 5. `configs/mobile_vla_v5_exp13_instr_cond.json` (NEW)
```json
{
    "parent": "configs/mobile_vla_v5_exp12_action_instr.json",
    "exp_name": "v5-exp13-instr-cond",
    "task_name": "mobile_vla_v5_exp13",
    "act_head": {
        "type": "MobileVLAClassificationDecoder",
        "num_classes": 8,
        "action_dim": 8,
        "hidden_size": 1024,
        "class_weights": [1.0, 0.5, 10.0, 10.0, 4.0, 4.0, 50.0, 50.0],
        "instr_in_features": 2048
    }
}
```

## 핵심 설계 결정
- **word embedding 추출**: LM hidden states 대신 입력 단계의 word embedding 사용 → 구현 단순, 추가 forward pass 불필요
- **detach**: instruction embedding은 detach → `instr_proj`만 학습, word embedding gradient path 분리
- **additive conditioning**: concatenation 대비 파라미터 증가 최소화 (Linear 2048→2048 하나만 추가)
- **backward 호환**: `instr_proj=None`이면 기존 동작 그대로 (Exp11과 동일)

## 승인 상태
- [x] 방향 승인 (사용자: "2" / "B로 ㄱㄱ", 2026-04-17)
- [x] 구현 완료 (2026-04-17)
- [x] 학습 중단 (2026-04-17, epoch=6에서 수동 kill)
- [x] 검증 완료 (PM 15% — FWD+L collapse, Exp11 대비 퇴보)

## 검증 결과 (2026-04-17)
PM/DM eval (epoch=6, val_loss=1.947):
- PM 15% (15/100)
- FORWARD=0%, LEFT=0%, RIGHT=0%, FWD+L=100%, FWD+R=0%
- 모델이 FWD+L로 collapse (instr_proj이 constant bias 학습)
- 근본 원인: word embedding mean은 instruction별로 큰 차이 없음 → 텍스트 구별 불가
- 결론: Architecture-level text conditioning만으로는 shortcut learning 해결 불가

---

# Exp14: BBox-based Navigation (Grounding → Action)
작성일: 2026-04-17

## 1. 목표
- 해결하려는 문제: path_type 분류가 아니라 **"basket 위치 → 행동"** 이라는 물리 규칙 기반 네비게이션으로 재정의
- 핵심 관점 전환:
  - 기존: "9개 path_type을 다 맞히기"
  - 신규: "basket이 어디 있는지 보고 그쪽으로 가기"
- 이번 문서 단계:
  - [x] 리서치 완료
  - [ ] 구현 전 승인 대기
  - [ ] 승인 후 구현 예정

## 2. 배경 / 현재 상태
- Exp11~13 모두 LEFT=0% 또는 FWD+L collapse
- 공통 원인: 텍스트 instruction이 shortcut learning으로 무시됨
- Pure Kosmos-2 테스트(9 path HTML) 결과:
  - `left_left`: "far left of the image" ✅
  - `right_right`: "far right of the image" ✅
  - foundation에 좌/우 구별 능력 존재
- Exp10 BBox grounding: IoU 0.87, match 92% — 이미 공간 인식 성공

## 3. 리서치 요약
### 3.1 확인한 자원
- `runs/v5_nav/kosmos/mobile_vla_v5_bbox/2026-04-15/v5-exp10-track2-bbox/epoch_epoch=epoch=07-val_loss=val_loss=0.012.ckpt`
- `ROS_action/v5_data_bak/v5_grounding.json` (50ep 부분 grounding 결과 있음)
- `scripts/run_v5_grounding.py` — pure HF Kosmos-2로 grounding 실행하는 레퍼런스
- `docs/v5/pure_backbone_9paths/` — pure 백본 9 path 확인 페이지

### 3.2 재정의된 문제 공식
```
basket_x < 0.35  → LEFT 또는 FWD+L
0.35 ~ 0.65     → FORWARD
basket_x > 0.65  → RIGHT 또는 FWD+R
basket_size 큼  → STOP (근접)
```

### 3.3 왜 이 접근이 유력한가
1. Foundation(pure Kosmos-2)에 공간 인식 능력 있음 — 9-paths HTML 증거
2. Exp10 grounding이 이미 고정확도 — 재사용 가능
3. 텍스트 무시해도 공간 좌표는 물리적으로 결정됨 — shortcut learning 우회
4. 교수님 Step 1 기준 직접 매핑:
   - 곡선 이미지: basket이 좌/우 치우침 → 곡선 action 자동 산출

## 4. 제안 변경 사항
### 4.1 단계별 전략

**Step 0 (최소 노력, 즉각 검증)**
- Pure HF Kosmos-2 grounding 결과 → rule-based action 매핑 → PM 측정
- 학습 0, 아키텍처 변경 0
- 결과에 따라 다음 단계 결정

**Step 1 (Step 0 부족 시)**
- BBox(x, y, w, h) + history → 작은 MLP/LSTM → action
- Kosmos 이미지 feature 없이 BBox만으로 학습

**Step 2 (Step 1도 부족 시)**
- Exp04 Kosmos feature + BBox projection → 기존 action head
- Exp13 `instr_proj` 대신 `bbox_proj` 사용

### 4.2 Step 0 변경 파일
1. `scripts/test_v5_bbox_nav_step0.py` (신규)
   - pure HF Kosmos-2 load
   - 9 path_type × N episode × 첫/중/끝 프레임 grounding
   - basket BBox 추출 (basket 키워드 entity 우선, 없으면 최대 크기)
   - rule-based action 예측
   - GT action과 비교 → per-path PM + confusion matrix
2. `docs/v5/bbox_nav_step0/index.html` (자동 생성)
   - 각 frame 이미지 + BBox 오버레이 + 예측/GT 표시
3. `docs/index.html` 수정
   - Hero 영역에 "BBox Nav Step 0" 버튼 추가

### 4.3 Rule-based 매핑 (Step 0 초기안)
```python
def bbox_to_action(cx, cy, w, h):
    area = w * h
    if area > 0.4:        # basket 화면 비율 > 40% → 근접
        return STOP
    if cx < 0.35:
        return FWD+L if 0.15 <= cx < 0.35 else LEFT
    if cx > 0.65:
        return FWD+R if 0.65 < cx <= 0.85 else RIGHT
    return FORWARD
```
- 경계값은 초기 추정, 실제 데이터로 튜닝 가능

## 5. 검증 계획
- Step 0 결과물:
  - `docs/v5/bbox_nav_step0/index.html` — 시각적 검증
  - PM per path_type 표
  - 전체 PM 숫자
- 성공 기준:
  - Step 0 PM > 50% → rule-based만으로 실용적 baseline
  - per-path PM에서 left_* 계열 > 30% → shortcut 해결됨
- 실패 기준:
  - PM < 30% → basket grounding 자체 부정확, Exp10 체크포인트 사용 필요

## 6. 리스크 / 트레이드오프
| 리스크 | 원인 | 대응 |
|--------|------|------|
| Pure Kosmos-2가 basket 놓침 | 첫 프레임에 basket 너무 작음 | Exp10 ckpt 사용, 중간/끝 프레임도 샘플 |
| Rule 경계값 부적절 | heuristic | 데이터 기반 튜닝 또는 learned version |
| STOP 과다 예측 | area threshold 과대 | threshold 조정 또는 제거 |

## 7. 작업 순서 가이드 (DO NOT EXECUTE YET)
1. Step 0 스크립트 작성 (pure Kosmos-2)
2. 9 path × 첫/중/끝 프레임 실행
3. PM 측정 + HTML 생성
4. 메인 index.html에 링크 추가
5. 결과 보고 → Step 1 진행 여부 판단

## 8. 승인 상태
- [ ] 방향 승인 대기

---

# Attention Weight Analysis: Causal Evidence for Text-Ignore Hypothesis
작성일: 2026-04-17

## 목표
- `TEXT_IGNORE_ROOTCAUSE_20260424.md` §6 반문 2의 "잔여 약점"(attention 미측정) 해결
- 가설: Kosmos-2 LM에서 action token(1개)이 image tokens(64개)에 과도 attend, text tokens에는 미미 attend

## 승인 상태
- [x] 리서치 완료 (2026-04-17)
- [x] 구현 승인 (사용자: "1로 가봐 페이즈 다 해봐도 되고")
- [x] 구현 완료 (2026-04-18)

## 핵심 설계 (확정)
- RoboVLMs 수정 0 — monkey-patch로 `output_attentions=True` 주입
- 토큰 레이아웃 실측: `image_embeds(0:64) + text_embeds(64:256) + action(256)`, seq=257
- Metric: last-layer action row attention의 region-wise ratio + top-K position

## 핵심 결과
- Exp11 (학습 후): image `91.7%` / text **`0.000%`** / 3 instruction bit-level 동일 attention
- Exp13 (학습 후): image `85.8%` / text **`0.000%`** — `instr_proj` 추가도 LM 단계 무시를 못 깨뜨림
- **Pure Kosmos-2 (학습 전)**: image `77.3%` / text **`22.7%`** — foundation은 정상적으로 text에 attend
- Cross-attentions: `None` (Kosmos decoder-only)
- → "learned collapse of instruction attention path" causal chain 완성 (before/after)

## Phase 진행
- [x] Phase 1: Hook + capture 확인
- [x] Phase 2: Exp11/Exp13 × 좌/우/전진 metric
- [x] Phase 3: per-layer + top-K + text-region per-position + **Pure Kosmos-2 대조** (before/after 22.7% → 0%)
- [x] Phase 4: TEXT_IGNORE_ROOTCAUSE §1/§4.1/§6/§7/§8/§9, PROF_UPDATE §7-1, index.html hero 반영

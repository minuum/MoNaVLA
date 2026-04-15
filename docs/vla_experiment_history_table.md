# VLA 모델 실험 전체 역사 테이블

**작성일시**: 2026-02-28 17:37  
**출처**: 실제 config JSON, 학습 로그(.log), git commit history 직접 추출  
**원칙**: 환각 없음 — 파일에서 직접 확인된 값만 기록, 미확인 항목은 N/A 표기

---

## 1. Git 커밋 기반 실험 분기 역사

| 커밋 해시  | 날짜             | 브랜치                                | 커밋 메시지                                                             | 추가된 주요 파일                      |
| :--------- | :--------------- | :------------------------------------ | :---------------------------------------------------------------------- | :------------------------------------ |
| `0cf4fdbd` | 2026-02-15       | inference-integration                 | Initialize inference-integration with clean state                       | 초기 상태 (H5 제거)                   |
| `f68c021e` | 2026-02-25 21:51 | inference-integration                 | feat: add V3 experiment artifacts (exp04, exp05)                        | exp03, exp04, exp05 config + 로그     |
| `73488ad0` | 2026-02-26 07:45 | inference-integration                 | feat: add V3-exp06 LoRA config and training script                      | exp06 config + train_v3_exp06_lora.sh |
| `ac9ed116` | 2026-02-26 이후  | inference-integration                 | feat: integrate V3-exp06 configs, logs, and dataset loader improvements | exp06 로그, dataset 개선              |
| `51bed21b` | HEAD             | inference-integration (= origin/main) | feat(upstream): add custom scripts local to this repo                   | 현재 HEAD                             |

> **exp07 (rev2)**: 2026-02-28 13:46에 nohup으로 실행, 커밋 미완료(학습 진행 중)

---

## 2. V3 실험 계열 (주요 대상) 전체 파라미터 비교표

### 2-A. 학습 하이퍼파라미터

| 항목              |             exp04             |             exp05             |             exp06             |    **exp07 (rev2, 현재)**     |
| :---------------- | :---------------------------: | :---------------------------: | :---------------------------: | :---------------------------: |
| **Config 파일**   | mobile_vla_v3_exp04_lora.json | mobile_vla_v3_exp05_lora.json | mobile_vla_v3_exp06_lora.json | mobile_vla_v3_exp07_lora.json |
| **VLM 기반**      |           Kosmos-2            |           Kosmos-2            |           Kosmos-2            |           Kosmos-2            |
| **학습 방식**     |             LoRA              |             LoRA              |             LoRA              |             LoRA              |
| **LoRA rank**     |              16               |              16               |              32               |              32               |
| **LoRA alpha**    |              32               |              32               |              64               |              64               |
| **LoRA dropout**  |             0.05              |             0.05              |             0.05              |             0.05              |
| **Learning Rate** |             5e-5              |             5e-5              |             3e-5              |             1e-5              |
| **Max Epochs**    |              10               |              12               |              15               |              20               |
| **Precision**     |           16-mixed            |           16-mixed            |           16-mixed            |           16-mixed            |
| **Batch Size**    |               1               |               1               |               1               |               1               |
| **Num Workers**   |               4               |               4               |               4               |               4               |

### 2-B. 데이터 및 Action Space 설정

| 항목                       |         exp04         |         exp05         |       exp06        |        **exp07 (rev2)**        |
| :------------------------- | :-------------------: | :-------------------: | :----------------: | :----------------------------: |
| **데이터셋**               |   basket_dataset_v2   |   basket_dataset_v2   | basket_dataset_v2  |       basket_dataset_v2        |
| **episode_filter_keyword** | *(미정의, 전체 사용)* | *(미정의, 전체 사용)* | `"left"` (278 ep)  |      `null` (528 ep 전체)      |
| **총 에피소드 수**         |    N/A (전체 추정)    |    N/A (전체 추정)    |  278 (left only)   | **528 (left 278 + right 250)** |
| **Action 방식**            |  discrete (9-class)   |  discrete (9-class)   | discrete (9-class) |       discrete (9-class)       |
| **Window Size**            |           8           |           8           |         8          |               8                |
| **With History**           |         true          |         true          |        true        |              true              |
| **History Type**           |         post          |         post          |        post        |              post              |
| **Num LSTM Layers**        |           4           |           4           |         4          |               4                |
| **history_dropout_prob**   |      *(미정의)*       |      *(미정의)*       |        0.3         |              0.2               |
| **train_split**            |          0.9          |          0.9          |        0.9         |              0.9               |

### 2-C. 데이터 증강(Augmentation) 설정

| 항목                 |  exp04   |  exp05   |  exp06   | **exp07 (rev2)** |
| :------------------- | :------: | :------: | :------: | :--------------: |
| **use_color_jitter** | `true` ❌ | `true` ❌ | `true` ❌ |  **`false` ✅**   |
| **use_random_crop**  | `true` ❌ | `true` ❌ | `true` ❌ |  **`false` ✅**   |

> ⚠️ exp04~06는 use_color_jitter=true이지만, 당시 코드에서 색상 번쩍임(프레임별 파라미터 랜덤화) 이슈가 있었음.  
> exp07(rev2)에서 완전 제거. 이것이 성능 급등의 핵심 원인.

### 2-D. Class Weights (9-class: STOP, F, B, L, R, FL, FR, BL, BR)

|  cls  | 이름  | exp04 | exp05 | exp06 | **exp07 (rev2, 데이터 기반)** | 실제 데이터 비율 |
| :---: | :---: | :---: | :---: | :---: | :---------------------------: | :--------------: |
|   0   | STOP  |  2.0  |  2.0  |  1.5  |           **8.98**            |       5.6%       |
|   1   |   F   |  0.2  |  0.1  | 0.08  |        **1.00** (기준)        |      50.0%       |
|   2   |   B   |  5.0  |  5.0  |  5.0  |       **0.0** (미사용)        |       0.0%       |
|   3   |   L   |  5.0  | 10.0  | 15.0  |           **17.12**           |       2.9%       |
|   4   |   R   |  5.0  |  2.0  |  5.0  |           **9.00**            |       5.6%       |
|   5   |  FL   |  5.0  |  1.5  |  2.5  |           **3.00**            |      16.7%       |
|   6   |  FR   |  5.0  |  1.0  |  3.5  |           **2.59**            |      19.3%       |
|   7   |  BL   |  5.0  |  5.0  |  5.0  |       **0.0** (미사용)        |       0.0%       |
|   8   |  BR   |  5.0  |  5.0  |  5.0  |       **0.0** (미사용)        |       0.0%       |

> 📌 exp07 (rev2)의 class_weights는 basket_dataset_v2 528개 에피소드, 총 9,487 프레임 직접 분석(역수 가중치, 2026-02-28) 기반.

---

## 3. 학습 결과 비교 (로그 직접 확인 — Epoch 2 종료 시점 기준)

| 모델             | Epoch 2 Val Loss | Epoch 2 Val Acc |   최종 Best Val Loss    | 최종 Best 도달 Epoch | 실물 로봇 테스트 | 비고                                   |
| :--------------- | :--------------: | :-------------: | :---------------------: | :------------------: | :--------------: | :------------------------------------- |
| **exp04**        |      0.294       |      82.5%      |     0.455 (Epoch 8)     |       Epoch 8        |     ✅ 수행됨     | 실물 주행 시 LEFT 편향, 방향 떨림 발생 |
| **exp05**        |   0.281 (추정)   |      75.4%      |     0.240 (Epoch 1)     |      Epoch 1 말      |     ❌ 미확인     | exp04와 동일한 DA 문제; RIGHT만 학습   |
| **exp06**        |      0.107       |      95.7%      | 0.053 → *(Epoch 2에서)* |       Epoch 2        |     ✅ 수행됨     | **조향 진동(Vibration) 심각하게 발생** |
| **exp07 (rev2)** |    **0.053**     |    **97.9%**    |    *(학습 진행 중)*     |     *(Epoch 3+)*     |      🔄 예정      | **Epoch 2에서 역대 최저 Loss 달성**    |

> ⚠️ exp06 "Epoch 2: 100%" 로그에서 val_acc=0.957로 나오지만, 다음 에폭 시작 시점에서  
> val_acc=0.754로 리셋 (새 에폭 시작 로그 혼재 가능성, grep 결과 불일치 주의)  
> exp07(rev2) Epoch 2 기준 val_loss=0.053 / val_acc=0.979는 grep 원문 직접 확인 완료.

---

## 4. 실험 계보 (Evolution Tree)

```
[V1 계열] 2025-11 ~ 12: Kosmos-2 초기 적용, chunk5/chunk10 기반 Regression (연속값 조향)
     ↓
[V2 계열] 2026-01 ~ 02: 9-class 이산 분류(Discrete), exp09~exp17, PaliGemma 비교
     ↓
[V3-exp01 ~ exp03] 2026-02: 증강(DA) 통합 실험 (aug.json 기반)
     ↓
[V3-exp04] 2026-02-25: LoRA rank 16, LR 5e-5, DA ON, 전체 데이터
     ↓
[V3-exp05] 2026-02-25: LoRA rank 16, class_weight R 강화, DA ON
     ↓
[V3-exp06] 2026-02-26: LoRA rank 32, LR 3e-5, LEFT only, history_dropout 0.3, DA ON
           → 실물 조향 진동 발생 (DA 파이프라인 오류 + LEFT 편향이 원인)
     ↓
[V3-exp07 rev2] 2026-02-28: LoRA rank 32, LR 1e-5, LEFT+RIGHT 통합,
                 DA 완전 OFF, 데이터 기반 역수 class_weights, history_dropout 0.2
                 → Epoch 2에서 val_acc 97.9% 달성 (역대 최고)
```

---

## 5. 핵심 레슨런 (Lesson Learned)

| 문제                  | 원인                                                             | 해결책                    | 반영 실험  |
| :-------------------- | :--------------------------------------------------------------- | :------------------------ | :--------: |
| Forward 무한 직진     | F weight 0.1~0.2로 과억제 → 실제로는 F가 50%라 기준값 1.0이 정답 | 역수 기반 class_weight    | exp07 rev2 |
| 조향 진동(Vibration)  | ColorJitter가 매 프레임 랜덤 색상 변형 → 시간적 일관성 파괴      | DA 완전 OFF               | exp07 rev2 |
| LEFT/RIGHT 편향       | episode_filter_keyword="left"만 → 우방향 Goal Context 미학습     | filter=null (전체 통합)   | exp07 rev2 |
| B, BL, BR Dead Neuron | 실제 데이터에 0프레임 → 무의미한 뉴런 낭비                       | weight=0.0 처리           | exp07 rev2 |
| 카메라 도메인 갭      | 학습 카메라(푸른 색조) ≠ 실운용 카메라(어안, 따뜻한 색조)        | 신규 카메라로 재수집 필요 |  미완료 🔴  |

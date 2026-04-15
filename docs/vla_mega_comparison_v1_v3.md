# VLA 모델 전체 히스토리 통합 비교표 (V1 ~ V3 MEGA TABLE)

**작성일시**: 2026-02-28  
**작성원칙**: V1부터 V3까지의 모든 실험을 통합 비교. `FT` 대신 실제 설정에 따라 `Frozen Backbone + Head Tuning` 또는 `LoRA` 여부를 명확히 표기. 해당하지 않는 항목은 `해당없음(N/A)`으로 표기.

---

## 📊 V1 ~ V3 통합 파라미터 및 성능 비교표

|  세대  | 모델/실험명            | 조향 방식 (Approach) | 학습 방법 (Backbone / Head) | LoRA 파라미터 (r / α) | LR (학습률) | 윈도우 (Window) | 데이터 필터 (Filter) | 데이터 증강 (DA: Color/Crop) | Class Weights (F/L/R)    | 최고성능 (Val Loss/Acc) | 설정 출처 (Config)                       |
| :----: | :--------------------- | :------------------- | :-------------------------- | :-------------------- | :---------- | :-------------: | :------------------- | :--------------------------: | :----------------------- | :---------------------- | :--------------------------------------- |
| **V1** | **chunk5_20251217**    | Regression           | **Frozen** / Head Only      | 해당없음              | 1e-4        |        8        | 전체                 |           ON / ON            | 해당없음                 | Loss: 0.455             | `mobile_vla_chunk5_20251217.json`        |
| **V1** | **chunk10_20251217**   | Regression           | **Frozen** / Head Only      | 해당없음              | 1e-4        |        8        | 전체                 |           ON / ON            | 해당없음                 | 해당없음                | `mobile_vla_chunk10_20251217.json`       |
| **V2** | **v2_9cls**            | Classification       | **Frozen** / Head Only      | 해당없음              | 1e-4        |        8        | 전체                 |           ON / ON            | 해당없음                 | 해당없음                | `mobile_vla_v2_classification_9cls.json` |
| **V2** | **exp11_discrete**     | Classification       | **Frozen** / Head Only      | 해당없음              | 1e-4        |        8        | 전체                 |           ON / ON            | 해당없음                 | 해당없음                | `mobile_vla_exp11_discrete.json`         |
| **V2** | **exp16_win6_k1**      | Classification       | **Frozen** / Head Only      | 해당없음              | 1e-4        |        6        | 전체                 |           ON / ON            | 해당없음                 | 해당없음                | `mobile_vla_exp16_win6_k1.json`          |
| **V2** | **exp17_win8_k1**      | Classification       | **Frozen** / Head Only      | 해당없음              | 1e-4        |        8        | 전체                 |           ON / ON            | 해당없음                 | 85.0% 추정              | `mobile_vla_exp17_win8_k1.json`          |
| **V2** | **exp_v2_17 (basket)** | Classification       | **Frozen** / Head Only      | 해당없음              | 1e-4        |        8        | basket_v2            |           ON / ON            | 해당없음                 | Global PM: 99.17%       | `mobile_vla_exp_v2_17.json`              |
| **V3** | **exp01_aug**          | Classification       | **LoRA** / Head Only        | 16 / 32               | 5e-5        |        8        | 전체                 |           ON / ON            | 해당없음                 | 해당없음                | `mobile_vla_v3_exp01_aug.json`           |
| **V3** | **exp02_baseline**     | Classification       | **LoRA** / Head Only        | 16 / 32               | 5e-5        |        8        | 전체                 |           ON / ON            | 해당없음                 | 해당없음                | `mobile_vla_v3_exp02_baseline.json`      |
| **V3** | **exp03_weighted**     | Classification       | **LoRA** / Head Only        | 16 / 32               | 5e-5        |        8        | 전체                 |           ON / ON            | F:0.1, L:5.0             | 해당없음                | `mobile_vla_v3_exp03_weighted.json`      |
| **V3** | **exp04_lora**         | Classification       | **LoRA** / Head Only        | 16 / 32               | 5e-5        |        8        | 전체                 |           ON / ON            | F:0.2, L:5.0, R:5.0      | Loss: 0.294 / 82.5%     | `mobile_vla_v3_exp04_lora.json`          |
| **V3** | **exp05_lora**         | Classification       | **LoRA** / Head Only        | 16 / 32               | 5e-5        |        8        | 전체                 |           ON / ON            | F:0.1, L:10.0, R:2.0     | Loss: 0.240 / 84.6%     | `mobile_vla_v3_exp05_lora.json`          |
| **V3** | **exp06_lora**         | Classification       | **LoRA** / Head Only        | 32 / 64               | 3e-5        |        8        | **left**             |           ON / ON            | F:0.08, L:15.0           | Loss: 0.107 / 95.7%     | `mobile_vla_v3_exp06_lora.json`          |
| **V3** | **exp07_lora (rev2)**  | Classification       | **LoRA** / Head Only        | **32 / 64**           | **1e-5**    |        8        | **전체 (L+R)**       |        **OFF / OFF**         | **F:1.0, L:17.1, R:9.0** | **Loss: 0.053 / 97.9%** | `mobile_vla_v3_exp07_lora.json`          |

---

## 🔍 학습 방식 진화 분석 (Backbone & Head)

1. **V1 ~ V2 (Frozen Backbone + Head Tuning)**
   - 설정 파일 내 `freeze_backbone: true` 및 `use_lora: false` 확인됨.
   - VLM(백본)의 가중치는 전혀 업데이트하지 않고, 마지막 **Action Head(MLP 또는 LSTM)**만 학습한 방식임.
   - 계산 비용은 낮으나, 백본의 특징 추출 능력(Feature Extraction)이 특정 도메인에 최적화되지 못하는 한계가 있음.

2. **V3 (LoRA + Head Tuning)**
   - 설정 파일 내 `freeze_backbone: true` 임에도 불구하고, `use_lora: true`를 통해 백본의 일부 파라미터(LoRA Adapter)가 액션 헤드와 함께 학습됨.
   - **V3 초기(exp01~05)**: Rank 16을 사용하여 가볍게 튜닝.
   - **V3 후기(exp06~07)**: Rank 32로 상향하여 백본이 액션 명령(Goal Context)을 더 잘 이해하도록 유도.
   - 모든 V3 실험에서 백본 자체(Raw Weights)는 Frozen 상태를 유지하며 LoRA 어댑터와 헤드만 학습함.

3. **데이터 증강 및 가중치 최적화**
   - **exp07 rev2**는 전 세대를 통틀어 **"Backbone(LoRA) + Head"** 조합에 더해 증강 노이즈를 완전 제거(`OFF`)하고 실측 데이터 기반 가중치를 적용한 유일한 모델임.

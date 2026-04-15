# Unified Regression Win12 Experiment Logs

본 문서는 디스크 공간 확보를 위해 `runs/unified_regression_win12` 디렉토리 내의 체크포인트를 정리하기 전, 각 실험의 성능 지표를 기록한 문서입니다.

## 🏆 Top 3 Best Checkpoints (남겨둔 모델)

| Rank | Experiment | Epoch | Validation Loss | Path |
| :--- | :--- | :--- | :--- | :--- |
| 1 | EXP17 (Win8 / K1) | 09 | **0.0013** | `runs/unified_regression_win12/kosmos/mobile_vla_exp17_win8_k1/2026-02-10/exp17_win8_k1/epoch=epoch=09-val_loss=val_loss=0.0013.ckpt` |
| 2 | EXP17 (Win8 / K1) | 07 | **0.0015** | `runs/unified_regression_win12/kosmos/mobile_vla_exp17_win8_k1/2026-02-10/exp17_win8_k1/epoch=epoch=07-val_loss=val_loss=0.0015.ckpt` |
| 3 | EXP17 (Win8 / K1) | 03 | **0.0016** | `runs/unified_regression_win12/kosmos/mobile_vla_exp17_win8_k1/2026-02-10/exp17_win8_k1/epoch=epoch=03-val_loss=val_loss=0.0016.ckpt` |

## 📊 실험별 요약 (삭제 전 기록)

| Experiment Name | Best/Last Epoch | Loss (Best) | Status |
| :--- | :--- | :--- | :--- |
| `mobile_vla_exp17_win8_k1` | Epoch 09 | 0.0013 | Top 1-3 확보 |
| `mobile_vla_exp12_win6_k1_resampler` | Epoch 06 | 0.0017 | 삭제됨 |
| `mobile_vla_exp16_win6_k1` | Epoch 03 | 0.0029 | 삭제됨 |
| `mobile_vla_unified_finetune_k1` | Step 2136 | N/A | 삭제됨 |
| `mobile_vla_unified_finetune_resampler`| Last | N/A | 삭제됨 |
| `mobile_vla_exp10_resampler_win16` | Last | N/A | 삭제됨 |
| `mobile_vla_exp09_resampler_latent128` | Last | N/A | 삭제됨 |
| `mobile_vla_unified_finetune` | Epoch 9 | N/A | 삭제됨 |

## 📁 보존 조치
- 모든 실험의 TensorBoard 로그(`events.out.tfevents.*`) 및 설정 파일(`.json`)은 그대로 유지하여 실험 추적성을 확보함.
- `last.ckpt` 및 비효율적인 중간 체크포인트만 삭제하여 약 80GB 이상의 공간을 확보함.

---
*Created on: 2026-02-16 04:00 (JST)*

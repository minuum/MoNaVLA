# 📝 VLA v4 Nav-Policy Training Fix Report (2026.04.02)

## 📋 Background
2026년 3월 말(03.31) 진행된 **VLA v4 Stage 3** 실험 및 `mobile_vla_v4_balanced_v2.json` 설정 기반 학습 중, 특정 조건에서 모델이 중단되는 현상이 발생함.

## 🔍 Problems Identified
1. **Batch Shape Mismatch (RuntimeError):** 
   - `NavPolicy`의 `loss` 계산 중 `flat_logits`와 `flat_labels`의 크기(80 vs 32) 불일치 발생.
   - 데이터셋 믹싱 및 마스킹 처리 과정에서의 차원 동기화 실패가 원인.
2. **Tuple Unwrapping Error (AttributeError):**
   - 모델 출력 형식이 `dict`가 아닌 `tuple`로 반환되면서 `prediction.get()` 호출 시 에러 발생.

## 🛠 Fixes Applied
1. **NavPolicy Shape Synchronization (L429-434):**
   - `robovlm_nav/models/policy_head/nav_policy_impl.py`
   - 두 텐서의 크기를 비교하여 최소값으로 자동 트리밍(Trimming)하는 방어코드 삽입.
2. **BaseTrainer Parsing Utility (L640):**
   - `third_party/RoboVLMs/robovlms/train/base_trainer.py`
   - `isinstance(prediction, tuple)` 체크 로직 추가로 데이터 언래핑 안정화.

## 📊 Comparison Table (3월 말 ~ 4월 초)
| 날짜 | 설정/체크포인트 | 상태 | 핵심 변경 |
| :--- | :--- | :--- | :--- |
| 03.31 | `balanced_v2.json` (Initial) | **Crashed** | NavPolicy 헤드 도입 (패치 전) |
| 04.02 | `hybrid_final_resume.json` | **Active** | **차원 방어 및 튜플 언래핑 패치 적용** |

## 🚀 Monitoring
- **Log Path:** `/home/billy/25-1kp/MoNaVLA/logs/train_v4_nav_policy.log`
- **Command:** `tail -f [LOG_PATH]`

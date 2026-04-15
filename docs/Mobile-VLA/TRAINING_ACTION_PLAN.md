# Mobile VLA - 현재 상태 및 해결 방안 정리

## 📊 현재 데이터셋 상태

### ✅ **발견사항 1: 텍스트 데이터 포함 여부**
- **데이터셋에 `language_instruction` 필드가 존재합니다!**
  ```python
  # H5 파일 구조
  Keys: ['action_event_types', 'actions', 'images', 'language_instruction']
  
  # 실제 텍스트 예시
  language_instruction[0] = b'Navigate around obstacles and reach the front of the beverage bottle on the left'
  ```
- **기존 `MobileVLAH5Dataset.__getitem__`은 하드코딩된 텍스트를 사용합니다**
  ```python
  # 현재 코드 (Line 173)
  language = "Navigate to the target location"  # 기본 명령 (하드코딩)
  
  # 수정 필요 → H5 파일에서 실제 읽어와야 함!
  ```

### ✅ **발견사항 2: 최신 데이터 (2025-12-03)**
- **오늘 수집된 최신 데이터**: 223개 에피소드 (`episode_20251203_*.h5`)
- **2025-11-19 이전 데이터**: 237개 에피소드 (`episode_2025111*.h5`)
- **현재 학습 Config의 패턴**: `episode_2025111*.h5` (구 데이터만 사용 중)

### ✅ **발견사항 3: 학습 구조 확인**
- **학습 스크립트**: `/home/billy/25-1kp/vla/RoboVLMs_upstream/main.py`
- **트레이너**: `MobileVLATrainer` (LoRA fine-tuning 지원)
- **모델**: Frozen Kosmos-2 Backbone + Trainable `MobileVLALSTMDecoder`
- **LoRA 설정**: r=32, alpha=16, dropout=0.1
- **학습 로그 경로**: `lora_training_log_*.txt` (루트 디렉토리에서 생성)

---

## 🔧 해결해야 할 의문점 및 액션 플랜

### 1. **언어 명령(Text) 데이터 활용**
**의문**: 데이터셋에 language_instruction이 있는데 사용되지 않고 있음

**해결 방안**:
```python
# RoboVLMs_upstream/robovlms/data/mobile_vla_h5_dataset.py
# Line 173 수정 필요
# BEFORE:
language = "Navigate to the target location"  # 기본 명령

# AFTER:
if 'language_instruction' in f:
    language = f['language_instruction'][0].decode('utf-8')
else:
    language = "Navigate to the target location"  # fallback
```

---

### 2. **최신 데이터셋 반영**
**의문**: 12월 3일 수집된 최신 데이터(223개)가 학습에 사용되지 않음

**해결 방안**:
```json
// Mobile_VLA/configs/mobile_vla_20251114_lora.json
// Line 120, 129 수정 필요
"episode_pattern": "episode_202512*.h5",  // 11월~12월 모든 데이터 포함
// OR
"episode_pattern": "episode_*.h5",  // 모든 에피소드 포함
```

---

### 3. **LoRA 학습 재개**
**의문**: 기존 로그들이 어디서 만들어졌는지, 학습이 진행 중인지 확인 필요

**로그 생성 로직 확인**:
```bash
# 로그 파일명 패턴: lora_training_log_YYYYMMDD_HHMMSS.txt
# 로그를 찾는 방법: grep "lora_training_log" 했으나 스크립트에서 직접 언급 없음
# → 학습 스크립트 내부에서 Python logging으로 생성되는 것으로 추정
```

**학습 실행 방법**:
```bash
# 방법 1: 직접 main.py 실행
cd /home/billy/25-1kp/vla/RoboVLMs_upstream
python main.py --config ../Mobile_VLA/configs/mobile_vla_20251114_lora.json

# 방법 2: 학습 진행 상태 확인 스크립트
./check_training_status.sh
```

---

### 4. **"Frozen VLM + 2DOF Action Head" 전략 검증**
**의문**: 교수님이 원하는 핵심 - VLM은 고정, Action Head만 학습

**현재 설정 확인**:
```json
// mobile_vla_20251114_lora.json의 train_setup
{
  "freeze_backbone": true,  // ✅ VLM 고정됨
  "lora_enable": true,      // ✅ LoRA 활성화
  "train_vision": false     // ✅ Vision Tower 고정
}
```
**→ 이미 올바르게 설정되어 있음!**

---

## 🚀 즉시 실행 가능한 액션

### Action 1: 데이터 로더 수정 (언어 명령 활용)
```bash
# 파일: RoboVLMs_upstream/robovlms/data/mobile_vla_h5_dataset.py
# Line 173 수정 필요
```

### Action 2: Config 업데이트 (최신 데이터 포함)
```bash
# 파일: Mobile_VLA/configs/mobile_vla_20251114_lora.json
# 새 Config 버전 생성: mobile_vla_20251203_lora.json
```

### Action 3: 학습 시작/확인
```bash
# 현재 학습 중인지 확인
./check_training_status.sh

# 학습 시작 (새 Config 사용)
cd RoboVLMs_upstream
python main.py --config ../Mobile_VLA/configs/mobile_vla_20251203_lora.json
```

---

## 📝 추가 확인 필요 사항
1. **Actions 차원 확인**: `actions: (18, 3)` → 3차원인데 왜? (linear_x, linear_y, angular_z?)
2. **Action Normalization**: 데이터셋 수집 시 이미 [-1, 1]로 정규화되었는지?
3. **학습 Checkpoint**: `runs/mobile_vla_lora_20251114/` 디렉토리에 체크포인트가 있는지?

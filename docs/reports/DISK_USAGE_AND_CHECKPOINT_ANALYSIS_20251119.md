# 디스크 사용량 및 체크포인트 저장 분석 (2025-11-19)

## 현재 디스크 상태

### 전체 디스크 사용량
- **총 용량**: 1.8TB
- **사용 중**: 1.7TB (98%)
- **남은 공간**: 43GB
- **사용률**: 98% ⚠️

### 주요 디렉토리별 사용량
- `.vlms/kosmos-2-patch14-224`: **25GB** (모델 파일)
- `ROS_action/mobile_vla_dataset`: **5.8GB** (학습 데이터)
- `runs/mobile_vla_lora_20251114`: **428KB** (학습 로그, 체크포인트 없음)

---

## 체크포인트 저장 설정 분석

### 현재 설정 (RoboVLMs 기본값)
```python
ModelCheckpoint(
    dirpath=configs["output_dir"], 
    save_top_k=-1,        # 모든 체크포인트 저장 (무제한)
    every_n_epochs=1      # 매 epoch마다 저장
)
```

### 실제 체크포인트 크기 (측정값)
- **체크포인트당 실제 크기**: **6.9GB** (예상보다 훨씬 큼!)
- **현재 저장된 체크포인트**: **47개**
- **현재 사용 중인 공간**: **321GB** ⚠️

### 저장 예상량
- **20 epoch 완료 시**: 20개 체크포인트 = **138GB**
- **현재 남은 공간**: 43GB
- **필요한 공간**: 138GB
- **부족한 공간**: **89.7GB** ⚠️⚠️

---

## 문제점

1. **디스크 공간 부족 (심각)**
   - 98% 사용 중으로 여유 공간 부족
   - **체크포인트만 321GB 사용 중** (전체 디스크의 18%)
   - 체크포인트 저장 실패 (Epoch 16에서 발생)

2. **체크포인트 저장 정책 비효율적 (매우 심각)**
   - `save_top_k=-1`: 모든 체크포인트 저장 (무제한)
   - `every_n_epochs=1`: 매 epoch마다 저장
   - **47개 체크포인트 저장** (불필요한 중복 저장)
   - 각 체크포인트가 6.9GB로 예상보다 3.5배 큼

3. **학습 완료 후 체크포인트 저장 실패**
   - Epoch 16까지 완료했지만 최종 체크포인트 저장 실패
   - Epoch 17-19 체크포인트는 저장됨 (이전 체크포인트 삭제 후)

---

## 권장 해결 방안

### 옵션 1: 체크포인트 저장 빈도 감소 (권장)
```python
ModelCheckpoint(
    dirpath=configs["output_dir"],
    save_top_k=3,           # 최고 성능 3개만 저장
    every_n_epochs=5,       # 5 epoch마다 저장
    monitor="val_loss",     # val_loss 기준으로 최고 성능 선택
    mode="min"
)
```
- **예상 저장량**: 3개 × 6.9GB = **20.7GB**
- **장점**: 디스크 공간 절약, 최고 성능 모델만 보존
- **공간 절약**: 321GB → 20.7GB (약 300GB 절약!)

### 옵션 2: 최종 모델만 저장 (최소 공간)
```python
ModelCheckpoint(
    dirpath=configs["output_dir"],
    save_top_k=1,           # 최고 성능 1개만 저장
    every_n_epochs=1,       # 매 epoch마다 체크 (최고 성능 갱신 시 저장)
    monitor="val_loss",
    mode="min"
)
```
- **예상 저장량**: 1개 × 6.9GB = **6.9GB**
- **장점**: 최소 공간 사용
- **공간 절약**: 321GB → 6.9GB (약 314GB 절약!)

### 옵션 3: 주기적 저장 + 최종 저장 (균형)
```python
ModelCheckpoint(
    dirpath=configs["output_dir"],
    save_top_k=2,           # 최고 성능 2개 저장
    every_n_epochs=5,       # 5 epoch마다 체크
    monitor="val_loss",
    mode="min",
    save_last=True          # 마지막 epoch 모델도 저장
)
```
- **예상 저장량**: 3개 × 6.9GB = **20.7GB**
- **장점**: 최고 성능 + 최종 모델 보존
- **공간 절약**: 321GB → 20.7GB (약 300GB 절약!)

---

## 즉시 조치 사항 (긴급!)

### 1. 디스크 공간 확보 (최우선 - 즉시 실행)
**현재 상황**: 47개 체크포인트가 321GB 사용 중

**권장 조치**:
```bash
# 최고 성능 체크포인트만 남기고 나머지 삭제
# 예: epoch=16 (최종), epoch=15, epoch=14 등 최근 3-5개만 보존
```

**예상 절약 공간**: 321GB → 20.7GB (약 300GB 절약!)

### 2. 체크포인트 설정 변경 (필수)
- `save_top_k=-1` → `save_top_k=3` (최고 성능 3개만)
- `every_n_epochs=1` → `every_n_epochs=5` (5 epoch마다)
- `monitor="val_loss"` 추가 (성능 기준)
- `mode="min"` 추가 (loss 최소화)

### 3. 학습 재개 시
- 디스크 공간 확보 후 재시작
- 변경된 체크포인트 설정 적용
- Epoch 16부터 재개 (resume 기능 사용)

---

## 체크포인트 저장 주기 권장안

### 학습 단계별 저장 전략
- **초기 (Epoch 1-5)**: 5 epoch마다 저장 (빠른 변화)
- **중기 (Epoch 6-15)**: 5 epoch마다 저장 (안정화)
- **후기 (Epoch 16-20)**: 매 epoch 저장 (최종 최적화)

### 최적 설정
```python
ModelCheckpoint(
    dirpath=configs["output_dir"],
    save_top_k=3,              # 최고 성능 3개만 보존
    every_n_epochs=1,          # 매 epoch 체크 (최고 성능 갱신 시 저장)
    monitor="val_loss",        # validation loss 기준
    mode="min",                # loss 최소화
    save_last=True,            # 마지막 epoch도 저장
    filename="epoch_{epoch:02d}-val_loss={val_loss:.3f}"
)
```

**예상 저장량**: 최대 4개 (최고 3개 + 마지막 1개) = **7.8GB**

---

## 다음 단계

1. ✅ 디스크 사용량 파악 완료
2. ✅ 체크포인트 저장 주기 분석 완료
3. ⏳ 체크포인트 설정 변경 필요
4. ⏳ 디스크 공간 확보 필요
5. ⏳ 학습 재개 또는 결과 분석


# 데이터셋 색상 보정 계획

**작성일**: 2025-12-17  
**목표**: 전체 데이터셋의 Cyan/Blue tint 제거 (Red 채널 보정)

---

## 🎯 문제 정의

### 현재 상태
```
평균 RGB: (128, 132, 135)
Red < Green < Blue
→ Cyan/Blue tint (차가운 톤)
```

### 목표 상태
```
목표 RGB: (132, 132, 132) 또는 중성 회색
Red ≈ Green ≈ Blue
→ 중성 톤
```

---

## 🔧 보정 방법 옵션

### Option 1: Red 채널 Global Offset (가장 간단)

**방법**:
```python
Red_new = Red + offset
offset = Green_avg - Red_avg = 132 - 128 = +4
```

**장점**:
- ✅ 매우 간단
- ✅ 빠른 처리
- ✅ 일관성 유지

**단점**:
- ⚠️ 모든 프레임에 동일한 값
- ⚠️ 개별 프레임 특성 무시
- ⚠️ 밝은 영역 oversaturation 가능 (255 초과)

**적용 예시**:
```python
# 전체 프레임에 Red +4
img[:,:,2] = np.clip(img[:,:,2] + 4, 0, 255)
```

---

### Option 2: White Balance 자동 보정 (추천)

**방법**: Gray World Assumption
```python
# 각 채널을 평균이 같아지도록 조정
avg_gray = (Red_avg + Green_avg + Blue_avg) / 3
scale_r = avg_gray / Red_avg
scale_g = avg_gray / Green_avg  
scale_b = avg_gray / Blue_avg

Red_new = Red * scale_r
Green_new = Green * scale_g
Blue_new = Blue * scale_b
```

**장점**:
- ✅ 표준 화이트 밸런스 기법
- ✅ 전체 색상 균형 유지
- ✅ 자연스러운 결과
- ✅ 프레임별 적용 가능

**단점**:
- ⚠️ 계산 복잡
- ⚠️ 일부 프레임에서 과보정 가능

**적용 예시**:
```python
avg_gray = np.mean([r_mean, g_mean, b_mean])
img[:,:,0] = np.clip(img[:,:,0] * (avg_gray / b_mean), 0, 255)
img[:,:,1] = np.clip(img[:,:,1] * (avg_gray / g_mean), 0, 255)
img[:,:,2] = np.clip(img[:,:,2] * (avg_gray / r_mean), 0, 255)
```

---

### Option 3: Adaptive Per-Frame 보정

**방법**:
```python
# 각 프레임의 RGB 평균 계산
# 프레임별로 최적 보정 계수 적용
```

**장점**:
- ✅ 프레임별 최적화
- ✅ 다양한 조명 조건 대응

**단점**:
- ⚠️ 프레임 간 일관성 저하 가능
- ⚠️ 복잡한 구현

---

### Option 4: 보정 안 함 (비교 기준)

**판단 필요**:
- 학습에 색상 편향이 영향을 주는가?
- VLA 모델이 색상에 민감한가?
- Action prediction에 색상이 중요한가?

**고려사항**:
- ✅ 데이터 원본 유지
- ⚠️ 색상 편향 학습 가능

---

## 📊 권장 접근 방법

### Phase 1: 샘플 테스트 (필수)

**목표**: 각 방법의 효과 비교

**절차**:
1. 샘플 에피소드 선택 (5-10개)
2. 각 방법으로 보정
3. 시각적 비교
4. RGB 통계 확인

**출력**:
- 원본 vs 보정 비교 이미지
- RGB 히스토그램
- 정량적 메트릭

---

### Phase 2: 전체 적용

**권장 방법**: **Option 2 (White Balance 자동 보정)**

**이유**:
- 표준 기법
- 자연스러운 결과
- 전체 색상 균형 유지

**구현**:
```python
def correct_white_balance(img):
    b, g, r = cv2.split(img)
    
    r_mean = np.mean(r)
    g_mean = np.mean(g)
    b_mean = np.mean(b)
    
    avg_gray = (r_mean + g_mean + b_mean) / 3
    
    r_corrected = np.clip(r * (avg_gray / r_mean), 0, 255).astype(np.uint8)
    g_corrected = np.clip(g * (avg_gray / g_mean), 0, 255).astype(np.uint8)
    b_corrected = np.clip(b * (avg_gray / b_mean), 0, 255).astype(np.uint8)
    
    return cv2.merge([b_corrected, g_corrected, r_corrected])
```

---

### Phase 3: 검증

**확인 사항**:
1. RGB 평균이 (X, X, X)에 가까워졌는가?
2. 시각적으로 자연스러운가?
3. 프레임 간 일관성 유지되는가?
4. Oversaturation 발생하지 않는가?

---

## 📁 파일 구조

### 보정 후 저장 방식

**Option A: 별도 디렉토리** (권장)
```
mobile_vla_dataset_corrected/
├── episode_xxx/
│   ├── frame_0000.png
│   ├── frame_0001.png
│   └── ...
└── ...

mobile_vla_dataset/  # 원본 유지
```

**장점**:
- 원본 보존
- A/B 테스트 가능
- 롤백 용이

---

### Option B: H5 파일에 직접 적용

```python
# H5 파일 수정
with h5py.File('episode.h5', 'r+') as f:
    images = f['images'][:]
    corrected = [correct_white_balance(img) for img in images]
    f['images'][:] = corrected
```

**주의**:
- 원본 백업 필수
- 데이터 손실 위험

---

## 🎯 추천 워크플로우

### Step 1: 샘플 보정 테스트

```bash
python3 test_color_correction.py \
    --sample-size 10 \
    --method white_balance \
    --output-dir correction_samples
```

**확인**:
- Before/After 이미지
- RGB 통계
- 시각적 품질

---

### Step 2: 사용자 검토

- 샘플 이미지들 확인
- 보정 방법 승인
- 파라미터 조정 필요 시

---

### Step 3: 전체 적용

```bash
python3 apply_color_correction.py \
    --source mobile_vla_dataset \
    --output mobile_vla_dataset_corrected \
    --method white_balance \
    --backup
```

**예상 시간**: 500 episodes × 18 frames ≈ 30-60분

---

### Step 4: 검증

```bash
python3 verify_correction.py \
    --corrected-dir mobile_vla_dataset_corrected
```

**확인**:
- RGB 평균: (X, X, X) 달성
- 표준편차 감소
- 시각적 품질

---

## 📊 예상 결과

### Before (현재)
```
RGB: (128, 132, 135)
R/G: 0.967
Cyan/Blue tint
```

### After (White Balance 보정)
```
RGB: (132, 132, 132) 예상
R/G: 1.000 목표
중성 톤
```

---

## ⚠️ 주의사항

### 1. 원본 백업
```bash
# 보정 전 필수!
cp -r mobile_vla_dataset mobile_vla_dataset_backup
```

### 2. H5 파일 재생성

이미지 보정 후:
```python
# PNG → H5 변환 필요
# 기존 H5 파일도 업데이트
```

### 3. 학습 영향 평가

보정 전/후 모델 성능 비교 필요:
- 보정 안한 데이터로 학습한 모델 A
- 보정한 데이터로 학습한 모델 B
- 성능 비교

---

## 🤔 중요한 질문

### 보정이 정말 필요한가?

**보정 필요한 경우**:
- ✅ 실제 배포 환경과 색상 차이가 큼
- ✅ 사람이 보기에 부자연스러움
- ✅ 학습 후 inference 시 색상 편향 발견

**보정 불필요할 수 있는 경우**:
- ✅ 모든 데이터가 동일한 편향 (일관성 있음)
- ✅ VLA 모델이 색상에 덜 민감
- ✅ 실제 카메라도 같은 설정 사용 예정

---

## 💡 최종 권장사항

### Recommended Pipeline

1. **먼저**: 샘플 10개로 White Balance 테스트
2. **확인**: 시각적 품질 및 RGB 통계
3. **결정**: 보정 적용 여부 확정
4. **적용**: 전체 500개 에피소드 보정
5. **검증**: RGB 중성화 확인
6. **백업**: 원본 데이터 보존

---

**작성일**: 2025-12-17  
**상태**: 계획 수립 완료  
**다음**: 샘플 테스트 스크립트 작성

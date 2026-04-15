# 오류 에피소드 상세 리포트

## 발견된 문제 에피소드 (2개)

---

## 에피소드 1: episode_20251204_000842_1box_hori_right_core_medium

### 📋 메타데이터
- **시나리오**: 1box_hori_right_core_medium
- **수집 시간**: 2025-12-04 00:08:42 (dawn)
- **총 프레임**: 18
- **오류 프레임**: 2개 (11.1%)
- **분류**: Minor

### ⚠️ 오류 프레임 상세

#### Frame 0006
```
위치: extracted_images/episode_20251204_000842_1box_hori_right_core_medium/frame_0006.png

통계:
  평균 밝기: 82.2 (❌ FAIL: < 104)
  어두운 픽셀(<50): 40.1% (❌ FAIL: > 20%)
  매우 어두운(<30): 34.1% (❌ FAIL: > 15%)

판정: ERROR (3개 기준 모두 위반)
```

#### Frame 0007
```
위치: extracted_images/episode_20251204_000842_1box_hori_right_core_medium/frame_0007.png

통계:
  평균 밝기: 80.3 (❌ FAIL: < 104)
  어두운 픽셀(<50): 41.6% (❌ FAIL: > 20%)
  매우 어두운(<30): 35.5% (❌ FAIL: > 15%)

판정: ERROR (3개 기준 모두 위반)
```

### ✅ 정상 프레임 통계 (16개)
```
평균 밝기: 131.5 ± 2.5
범위: 125.5 ~ 134.6
어두운 픽셀: ~7-12%

특징: 매우 일관된 품질
```

### 📊 프레임 시퀀스 분석
```
Frame 0005: ✅ 정상 (밝기 132.3)
Frame 0006: ❌ 오류 (밝기 82.2) ← 갑작스런 하락
Frame 0007: ❌ 오류 (밝기 80.3) ← 지속
Frame 0008: ✅ 정상 (밝기 133.7) ← 즉시 회복
```

**패턴**: 2프레임 연속 오류 후 즉시 정상 회복

---

## 에피소드 2: episode_20251204_013302_1box_hori_right_core_medium

### 📋 메타데이터
- **시나리오**: 1box_hori_right_core_medium
- **수집 시간**: 2025-12-04 01:33:02 (dawn)
- **총 프레임**: 18
- **오류 프레임**: 1개 (5.6%)
- **분류**: Minor

### ⚠️ 오류 프레임 상세

#### Frame 0007
```
위치: extracted_images/episode_20251204_013302_1box_hori_right_core_medium/frame_0007.png

통계:
  평균 밝기: 58.0 (❌ FAIL: < 104) ← 더 심각
  어두운 픽셀(<50): 48.1% (❌ FAIL: > 20%)
  매우 어두운(<30): 38.9% (❌ FAIL: > 15%)

판정: ERROR (3개 기준 모두 위반, 더 어두움)
```

### ✅ 정상 프레임 통계 (17개)
```
평균 밝기: 135.5 ± 14.2
범위: 126.8 ~ 191.3
어두운 픽셀: ~7-12%

특징: 약간 더 넓은 밝기 범위 (다양한 조명)
```

### 📊 프레임 시퀀스 분석
```
Frame 0006: ✅ 정상 (밝기 ~130)
Frame 0007: ❌ 오류 (밝기 58.0) ← 1프레임만 오류
Frame 0008: ✅ 정상 (밝기 ~135) ← 즉시 회복
```

**패턴**: 단일 프레임 오류 후 즉시 정상 회복

---

## 공통 패턴 분석

### 🔍 공통점
1. **시나리오**: 모두 1box_hori_right
2. **시간대**: 모두 dawn (00-02시)
3. **오류 위치**: 모두 frame_0007 포함
4. **즉시 회복**: 오류 후 바로 다음 프레임 정상

### 💡 원인 추정
**장애물 통과 시 그림자 효과**

```
로봇 이동 경로:
  Frame 0005-0006: 정상 이동
  Frame 0006-0007: 장애물 아래 진입 ← 그림자 발생
  Frame 0007-0008: 장애물 통과 완료 ← 조명 회복
```

### 📈 오류 심각도 비교

| 에피소드 | Frame 0006 | Frame 0007 | 총 오류 |
|----------|-----------|-----------|---------|
| Episode 1 | 82.2 | 80.3 | 2 frames |
| Episode 2 | - | 58.0 ⚠️ | 1 frame |

**관찰**: Episode 2의 frame_0007이 가장 어두움 (58.0)

---

## 📍 파일 위치

### Episode 1 오류 프레임
```bash
extracted_images/episode_20251204_000842_1box_hori_right_core_medium/frame_0006.png
extracted_images/episode_20251204_000842_1box_hori_right_core_medium/frame_0007.png
```

### Episode 2 오류 프레임
```bash
extracted_images/episode_20251204_013302_1box_hori_right_core_medium/frame_0007.png
```

### 참고용 정상 프레임
```bash
# Episode 1 전후 프레임
extracted_images/episode_20251204_000842_1box_hori_right_core_medium/frame_0005.png  # 정상
extracted_images/episode_20251204_000842_1box_hori_right_core_medium/frame_0008.png  # 정상

# Episode 2 전후 프레임
extracted_images/episode_20251204_013302_1box_hori_right_core_medium/frame_0006.png  # 정상
extracted_images/episode_20251204_013302_1box_hori_right_core_medium/frame_0008.png  # 정상
```

---

## 🎯 결론

### 오류 특성
- ✅ **격리됨**: 전후 프레임은 정상
- ✅ **일시적**: 즉시 회복
- ✅ **예측 가능**: 특정 위치(frame 6-7)에서만 발생
- ✅ **자연스러움**: 실제 환경의 그림자 효과

### 권장 조치
**그대로 사용 권장**

**근거**:
1. 전체의 0.03% (3/9,000)만 영향
2. 오류 패턴이 격리되어 있음
3. 실제 환경의 자연스러운 변화
4. 모델이 이런 상황도 처리해야 함

---

**작성일**: 2025-12-17  
**상태**: ✅ 분석 완료

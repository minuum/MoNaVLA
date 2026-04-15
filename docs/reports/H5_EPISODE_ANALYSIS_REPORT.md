# H5 에피소드 파일 분석 보고서

**분석 일시:** 2025-11-14  
**총 에피소드:** 136개  
**총 프레임:** 2,391개

---

## 📊 Task별 통계

### 1. `1box_hori_left_core_medium`

- **에피소드 수:** 105개
- **프레임 수:** 평균 17.5, 최소 1, 최대 18
- **Trajectory 분석:**
  - 총 Trajectory: 101개
  - 고유 Trajectory: 6개
  - **일관성 점수: 94.06%** (높을수록 일관적)

**가장 흔한 Trajectory:**
1. `SWWWWDWWWWWWWWWWWW` - 80회 (79.2%) ⭐
2. `SWWDWWWWWWDWWWWWWW` - 10회 (9.9%)
3. `SWWWDDWWWWWWWWWWWW` - 6회 (5.9%)

**분석:**
- 대부분의 에피소드(79.2%)가 동일한 trajectory를 따름
- 6가지 변형이 있지만, 주요 패턴은 일관적
- ✅ **일관성 양호**

### 2. `1box_hori_right_core_medium`

- **에피소드 수:** 31개
- **프레임 수:** 평균 18.0, 최소 18, 최대 18
- **Trajectory 분석:**
  - 총 Trajectory: 31개
  - 고유 Trajectory: 1개
  - **일관성 점수: 96.77%** (높을수록 일관적)

**가장 흔한 Trajectory:**
1. `SWWWWAWWWWWWWWWWWW` - 31회 (100%) ⭐

**분석:**
- 모든 에피소드가 완전히 동일한 trajectory
- ✅ **완벽한 일관성**

---

## 🎯 Trajectory 패턴 분석

### WASD 매핑
- **W** (Forward): `linear_x > 0.1`
- **A** (Left): `linear_y < -0.1`
- **S** (Stop): `|linear_x| < 0.1 && |linear_y| < 0.1`
- **D** (Right): `linear_y > 0.1`

### 주요 패턴

#### `1box_hori_left_core_medium` (79.2%)
```
S → W → W → W → W → D → W → W → W → W → W → W → W → W → W → W → W → W
```
- 시작: 정지(S)
- 초반: 전진(W) 4회
- 중간: 우회전(D) 1회
- 후반: 전진(W) 13회

#### `1box_hori_right_core_medium` (100%)
```
S → W → W → W → W → A → W → W → W → W → W → W → W → W → W → W → W → W
```
- 시작: 정지(S)
- 초반: 전진(W) 4회
- 중간: 좌회전(A) 1회
- 후반: 전진(W) 13회

---

## ✅ 결론

### 일관성 평가

1. **`1box_hori_right_core_medium`**: ✅ **완벽** (100% 일관)
2. **`1box_hori_left_core_medium`**: ✅ **양호** (79.2% 일관)

### 권장사항

1. **데이터 품질:**
   - 대부분의 에피소드가 일관된 trajectory를 따름
   - 학습에 사용 가능한 데이터 품질

2. **개선 가능 영역:**
   - `1box_hori_left_core_medium`의 6가지 변형 중 일부는 노이즈일 수 있음
   - 주요 패턴(79.2%)에 집중하는 것이 좋음

3. **학습 전략:**
   - 일관된 trajectory가 많으므로 학습 효과 기대
   - 데이터 증강 시 주요 패턴 중심으로 진행

---

## 📁 생성된 파일

- `h5_episode_analysis.png` - 전체 통계 시각화
- `h5_trajectory_analysis.png` - Trajectory 패턴 시각화
- `h5_episode_stats.json` - 상세 통계 데이터

---

**분석 스크립트:** `analyze_h5_episodes.py`


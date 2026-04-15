# 데이터 분포 분석 결과

## 발견: 심각한 데이터 불균형 🔴

### 분석 결과
```
총 Episodes: 250
```

### 시나리오별 분포
```bash
$ ls ROS_action/mobile_vla_dataset/episode_*.h5 | grep -c "left"
250

$ ls ROS_action/mobile_vla_dataset/episode_*.h5 | grep -c "right"  
0
```

**결론**: 
- ❌ **모든 250 episodes가 "left"만 존재**
- ❌ **"right" 데이터 0개**
- 🔴 **완전한 불균형 상태**

### 영향 분석

#### 1. 학습 편향
- 모델이 **왼쪽 회피만** 학습
- 오른쪽 회피 전혀 학습 못 함
- → 실제 환경에서 오른쪽 박스 만나면 실패 가능성 높음

#### 2. 일반화 불가
```
학습 데이터: 왼쪽만 250개
테스트: 오른쪽 박스 등장?
→ Zero-shot (본 적 없음)
```

#### 3. Loss 0.013의 재해석
```
✅ 왼쪽 박스 회피는 매우 잘 학습됨 (Loss 0.013)
❌ 하지만 오른쪽은 아예 못 함 (데이터 없음)
```

## 해결 방안

### 즉시 필요
1. **Right 데이터 250개 수집** 🔥
   - 동일한 trajectory
   - 박스만 오른쪽으로
   - 같은 환경/조명

2. **균형 재학습**
   - 250 left + 250 right = 500 total
   - Train: 400 (200+200)
   - Val: 100 (50+50)

### 예상 효과
```
Before: 250 left only
After: 250 left + 250 right

예상 성능:
- 좌측 회피: 유지 (Loss ~0.013)
- 우측 회피: 새로 학습 (Loss ~0.015 예상)
- 일반화: 크게 향상
```

## 교수님 지적 반영
> "1box left vs 1box right vs 1box left+right"
> "250 + 250을 같은 guide로"

**정확한 지적이었습니다!**
- 현재 left만 있음
- Right 추가 수집 필수
- 균형 맞춰야 의미 있는 연구

## 우선순위
**🔥 Critical**: Right 데이터 수집이 가장 급함

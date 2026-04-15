# Right 데이터 수집 가이드

## 목표
250 episodes (오른쪽 박스) 수집

## 수집 조건 (Left와 동일하게)
- 환경: 동일
- 로봇 시작 위치: 동일
- 목표물 위치: 동일
- **박스 위치만**: 왼쪽 → 오른쪽

## 파일명 규칙
```
episode_YYYYMMDD_HHMMSS_1box_hori_right_core_medium.h5
                                 ^^^^^
                                 변경!
```

## 수집 절차
1. 로봇 초기화
2. 박스를 오른쪽에 배치
3. 데이터 수집 시작
4. 250 episodes 수집
5. 검증: `ls *.h5 | grep right | wc -l`

## 균형 확인
- Left: 250
- Right: 250
- Total: 500 ✅

## 재학습 계획
```json
{
  "episode_pattern": "episode_20251*.h5",
  "train_split": 0.8
}
```
- Train: 400 (200L + 200R)
- Val: 100 (50L + 50R)

# 데이터 증가 원인 분석

**작성일**: 2025-12-09  
**모델**: No Chunk (mobile_vla_no_chunk_20251209)

---

## 요약

데이터가 250개에서 500개로 증가한 것은 **데이터 증강(augmentation)이 아닌 필터링 조건 차이**입니다.

---

## 설정 비교

### Case 4 (right_only)

```json
// Mobile_VLA/configs/mobile_vla_kosmos2_right_only_20251207.json
"train_dataset": {
    "episode_pattern": "*right*.h5",
    "train_split": 0.8
}
```

**결과**: 250개 에피소드 (right 방향만)

### No Chunk

```json
// Mobile_VLA/configs/mobile_vla_no_chunk_20251209.json
"train_dataset": {
    "episode_pattern": "episode_20251*.h5",
    "train_split": 0.8
}
```

**결과**: 500개 에피소드 (left + right 모두)

---

## 실제 파일 현황

```bash
$ ls ROS_action/mobile_vla_dataset/ | wc -l
전체: 500개
├── *left*.h5:  250개
└── *right*.h5: 250개
```

---

## 결론

| 항목 | Case 4 | No Chunk |
|:---|:---|:---|
| episode_pattern | `*right*.h5` | `episode_20251*.h5` |
| 매칭 파일 수 | 250개 | 500개 |
| 데이터 분포 | Right 방향만 | Left + Right 모두 |
| 증가 방법 | - | **필터링 조건 확장** |

**핵심**: 데이터 증강이 아니라 **episode_pattern 필터 조건**을 변경하여 전체 데이터를 사용한 것입니다.

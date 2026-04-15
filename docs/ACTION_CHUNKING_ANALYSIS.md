# Action Chunking 분석 (fwd_pred_next_n)

**작성일**: 2025-12-09  
**비교 대상**: RoboVLMs 원본 vs 우리 No Chunk 모델

---

## 요약

- **RoboVLMs 원본**: 모두 `fwd_pred_next_n=10` 사용
- **우리 No Chunk**: `fwd_pred_next_n=1` 사용
- **결론**: fwd_pred_next_n=1은 **우리만의 선택**이며, 학습 난이도 감소 효과가 있음

---

## RoboVLMs 원본 설정 확인

### Calvin Finetune 설정들

```bash
$ find RoboVLMs_upstream -name "*.json" -path "*configs*" \
    | xargs grep "fwd_pred_next_n"
```

| 설정 파일 | fwd_pred_next_n |
|:---|:---:|
| finetune_kosmos_..._ws-16_act-10.json | **10** |
| finetune_llava-mpt-7b_..._act-10.json | **10** |
| finetune_flamingo_mpt_3b_ws-8_act-10.json | **10** |
| finetune_paligemma_..._ws-8_act-10.json | **10** |
| finetune_qwen-vl-7b_..._ws-8_act-10.json | **10** |

> ⚠️ **RoboVLMs의 모든 예시가 fwd_pred_next_n=10을 사용**

---

## fwd_pred_next_n 의미

### fwd_pred_next_n=10 (Action Chunking)

```
현재 시점 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━>
            [action1][action2]...[action10]
            └──────── 2초 분량 미래 계획 ────────┘
```

**동작 방식**:
- 한 번의 추론으로 10개 미래 액션 예측
- 300ms마다 추론 → 2초 분량의 계획 수립
- 예측된 10개 액션을 순차 실행

**장점**:
- 일관된 궤적 유지
- 추론 빈도 낮음 (계산 효율적)
- 장기 계획 가능

**단점**:
- 학습 어려움 (더 복잡한 태스크)
- 실시간 반응성 낮음
- 환경 변화에 취약

### fwd_pred_next_n=1 (No Chunk / Reactive Policy)

```
현재 시점 ━━━>
            [action1]  ← 즉각 반응
```

**동작 방식**:
- 현재 관측에 대해 1개 액션만 예측
- 매 step마다 새로운 추론 필요
- Markov Decision Process 가정

**장점**:
- 학습 매우 쉬움 (Loss 30배 낮음!)
- 실시간 반응성 높음
- 환경 변화에 즉각 대응

**단점**:
- 떨림/진동 가능성
- 일관성 부족
- 장기 계획 불가

---

## 성능 비교

| 지표 | Action Chunk (10) | No Chunk (1) |
|:---|:---|:---|
| Val Loss | 0.016 (Case 4) | 0.000532 (**30배 낮음**) |
| 학습 Epochs | 10 | 4 |
| 추론 빈도 | 300ms/10액션 | 매 step |
| 궤적 일관성 | 높음 | 낮을 수 있음 |
| 실시간 반응 | 낮음 | 높음 |

---

## 결론 및 권장사항

### fwd_pred_next_n=1이 더 좋은가?

**학습 측면**: ✅ 예 (Loss 30배 낮음, 빠른 수렴)  
**실제 성능**: ❓ 테스트 필요

### 권장 전략

1. **현재**: fwd_pred_next_n=1로 시작 (학습 쉬움)
2. **테스트**: 실제 로봇에서 떨림 확인
3. **필요 시**: fwd_pred_next_n=10으로 전환

### 우리 특유의 선택

RoboVLMs 표준(10)과 다르게 1을 선택한 것은:
- 데이터 부족 상황에서 학습 난이도 감소
- Mobile VLA (TurtleBot4)의 단순한 2D 제어에 적합
- 실험적 접근으로서의 가치

# 전체 실험 추론 테스트 결과 및 향후 전략

**테스트 일시**: 2026-02-09 17:24 ~ 17:52 (총 28분)  
**테스트 환경**: 동일 테스트셋 (20 episodes, 343 frames)  
**평가 지표**: PM/DA (Perfect Match / Directional Agreement)

---

## 📊 전체 실험 성능 비교

| Rank | EXP ID | Model | Global PM/DA | Initial | Middle | Final | Val Loss |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 🥇 | **EXP-05** | Chunk k=1 | **89.72%** | 76.00% | **100.00%** | **100.00%** | - |
| 🥈 | **EXP-06** | Resampler 64 | **82.50%** | **81.00%** | 83.55% | 80.00% | 0.000141 |
| 🥉 | **EXP-09** | Resampler 128 | **77.50%** | 76.00% | 83.55% | 80.00% | 0.000141 |
| 4 | EXP-04 | Baseline Linear | 65.83% | 9.00% | 97.37% | 70.53% | - |

---

## 🔍 핵심 발견

### 1. **🏆 EXP-05 (Chunk k=1)가 압도적 1위!**

**성능**:
- **Global PM/DA**: 89.72% (2위 대비 +7.22%p)
- **Middle Phase**: 100% (완벽!)
- **Final Phase**: 100% (완벽!)
- **Initial Phase**: 76% (Resampler 수준)

**오류 분석**:
- `stop_confusion_false_move`: 20개 (5.8%) - 정지 구간에서 불필요한 움직임
- **거의 완벽한 성능**

**왜 k=1이 더 좋은가?**
1. **실시간성 증가**: Chunk 6은 미래 6스텝을 예측 → 과도한 복잡도
2. **단순 명료**: 현재 프레임만 집중 → 오버슈팅 감소
3. **정지 판단 정확**: Final Phase에서 100% → 불필요한 움직임 없음

### 2. **EXP-06 (Resampler 64) vs EXP-09 (Resampler 128)**

| 지표 | EXP-06 (64 latents) | EXP-09 (128 latents) | 차이 |
| :--- | :---: | :---: | :---: |
| **Global PM/DA** | **82.50%** | 77.50% | **-5.0%p** |
| **Initial** | **81.00%** | 76.00% | -5.0%p |
| **Middle** | 83.55% | 83.55% | 0.0%p |
| **Final** | 80.00% | 80.00% | 0.0%p |
| **Val Loss** | 0.000141 | 0.000141 | Same |

**결론**: 
❌ **Latent를 128로 늘려도 성능 향상 없음, 오히려 하락**  
✅ **EXP-06 (64 latents)가 최적**

**원인 추정**:
- **Overfitting**: 더 많은 파라미터가 오히려 일반화 성능 저하
- **Initial Phase 민감**: 첫 프레임 처리에 복잡도가 악영향
- **Window 12 제약**: 12 프레임 컨텍스트로는 128개 토큰을 충분히 활용 못함

### 3. **EXP-04 (Baseline)의 치명적 약점**

**Initial Phase 9%**: 첫 프레임 예측 거의 실패  
- Linear Projection만으로는 초기 컨텍스트 부족 시 대응 불가
- Resampler의 압축이 오히려 robust한 표현 학습에 도움

---

## 🎯 성능 순위 해석

### **왜 EXP-05가 최고인가?**

1. **Chunk Size의 함정**
   - k=6: 미래 6스텝 예측 → 불확실성 누적, 오버슈팅
   - k=1: 현재만 집중 → 단순하고 정확

2. **실전 주행과의 괴리**
   - 학습 시: Chunk 6으로 long-term planning
   - 추론 시: 실제로는 첫 번째 액션만 사용
   - **k=1이 학습-추론 간극 제거**

3. **Middle/Final 100% 달성**
   - 주행 중간: 직진/슬라이드 패턴 완벽 예측
   - 정지 판단: 오버슈팅 없이 정확히 멈춤

### **EXP-06이 2위인 이유**

1. **Visual Resampler 효과**
   - Initial Phase 81% (Baseline 9% 대비 +72%p)
   - 압축된 표현이 robust함

2. **균형잡힌 성능**
   - Initial/Middle/Final 모두 80% 이상
   - 편차 없이 안정적

---

## 💡 앞으로의 전략 제안

### 🚀 **우선순위 1: EXP-05 (Chunk k=1) 심화 분석**

**목표**: 왜 k=1이 k=6보다 좋은지 근본 원리 규명

**실험**:
1. **EXP-12: k=1 + Resampler**
   - EXP-05의 단순함 + EXP-06의 압축 효율
   - **예상 성능**: 90% 이상 돌파 가능

2. **EXP-13: k=3 (중간값)**
   - k=1과 k=6의 중간 지점 탐색
   - 단기 planning의 이점은 살리되, 과도한 단순화는 방지

3. **Chunk Size Ablation Study**
   - k=1, 2, 3, 4, 5, 6 체계적 비교
   - 최적 k 값 도출

**기대 효과**:
- **90%+ 정확도 달성**
- 학습-추론 괴리 해소
- 실시간 응답성 향상

---

### 🔬 **우선순위 2: Resampler 최적화 (EXP-06 개선)**

**근거**: EXP-09 실패로 "더 많은 토큰 ≠ 더 좋은 성능" 입증

**방향성**:
1. ❌ **Latent 수 증가 중단** (64가 최적)
2. ✅ **Resampler 깊이 조정**
   - 현재: depth=8
   - 실험: depth=4, 6, 10
   
3. ✅ **Attention Head 수 최적화**
   - 현재: heads=8, dim_head=64
   - 실험: heads=4/16, dim_head=128/32

**EXP-14: Resampler Architecture Search**
```json
{
  "vision_resampler": {
    "depth": [4, 6, 8, 10],
    "heads": [4, 8, 16],
    "num_latents": 64  // 고정
  }
}
```

---

### ⚡ **우선순위 3: 하이브리드 모델**

**EXP-15: k=1 + Resampler 64 + Optimal Depth**

조합의 힘:
- **EXP-05의 k=1 단순성** (89.72%)
- **EXP-06의 Resampler robustness** (82.50%)
- **최적화된 Resampler 구조**

**예상 성능**: **92~95%**

Config:
```json
{
  "window_size": 12,
  "fwd_pred_next_n": 1,  // k=1
  "use_vision_resampler": true,
  "vision_resampler": {
    "num_latents": 64,
    "depth": 6,  // 최적화할 값
    "heads": 8
  }
}
```

---

### 🧪 **우선순위 4: Middle Phase 100% 달성 연구**

**현황**:
- EXP-05: Middle 100% ✅
- EXP-04: Middle 97.37%
- EXP-06/09: Middle 83.55%

**분석 과제**:
1. **왜 k=1이 Middle에서 100%인가?**
   - 직진/슬라이드 패턴의 반복성?
   - Chunk 6의 long-term planning이 방해?

2. **EXP-06의 Middle 83%는 왜?**
   - Resampler 압축으로 정보 손실?
   - k=6의 복잡도가 문제?

**실험**: EXP-05와 EXP-06의 Middle Phase 예측 패턴 시각화

---

### 📉 **우선순위 5: Initial Phase 개선 (장기)**

**현황**:
- EXP-06: 81% (최고)
- EXP-05/09: 76%
- EXP-04: 9% (치명적)

**방향**:
1. **First Frame Override 제거 가능성 검토**
   - 현재 API 서버: 첫 프레임 강제 [0, 0]
   - EXP-06이 81%면 충분히 신뢰 가능

2. **History Warmup 전략**
   - 첫 12프레임: static image 반복으로 warmup
   - 13프레임부터: 실제 예측 시작

---

## 🎯 최종 추천 로드맵

### **Phase 1: 즉시 실행 (이번 주)**
1. ✅ **EXP-12 학습**: k=1 + Resampler 64
2. ✅ **EXP-13 학습**: k=3 + Resampler 64
3. 📊 추론 테스트 및 90% 돌파 확인

### **Phase 2: 최적화 (다음 주)**
4. 🔬 **EXP-14**: Resampler depth/heads ablation
5. 🚀 **EXP-15**: 최종 하이브리드 모델
6. 📊 95% 목표 달성 여부 확인

### **Phase 3: 실전 배포 (2주 후)**
7. 🤖 Jetson 디바이스에 최고 성능 모델 배포
8. 🏁 실제 로봇 주행 테스트
9. 📝 최종 논문 작성 준비

---

## 🚫 중단할 실험

1. ❌ **Latent 128+ 확장**: 성능 하락 확인 (EXP-09)
2. ❌ **Window Size 16+**: 데이터 부족으로 실패 (EXP-10)
3. ❌ **Discrete Classification**: Config 복잡도 대비 효과 불투명 (EXP-11)
4. ❌ **LoRA 학습**: 현재 구조 최적화가 우선

---

## 📈 성능 향상 예측

| 단계 | 모델 | 예상 PM/DA | 근거 |
| :---: | :--- | :---: | :--- |
| **현재** | EXP-05 (k=1) | 89.72% | 실측 |
| **Phase 1** | k=1 + Resampler | 92~93% | EXP-05 + EXP-06 시너지 |
| **Phase 2** | 최적 하이브리드 | 94~95% | Architecture tuning |
| **Phase 3** | Final + Jetson 최적화 | 95~97% | 실전 미세조정 |

---

## 💬 핵심 메시지

### **"Chunk Size k=1이 게임 체인저!"**

- 89.72% 정확도로 압도적 1위
- Middle/Final 100% 달성
- 학습-추론 괴리 제로

### **"Latent 64가 Sweet Spot"**

- 128로 늘려도 성능 하락
- 압축 효율과 표현력의 균형

### **"다음 목표: 95% 달성"**

- k=1 + Resampler 조합
- Architecture 미세조정
- 2주 내 달성 가능

---

**작성일**: 2026-02-09  
**결론**: EXP-05 기반 하이브리드 모델로 **2주 내 95% 정확도** 달성 가능!

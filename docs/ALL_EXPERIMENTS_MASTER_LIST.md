# 전체 실험 마스터 리스트 (EXP-01 ~ EXP-17)

**작성일**: 2026-02-09  
**목적**: 모든 실험의 상태, 특징, 성능 종합 정리

---

## 📋 전체 실험 현황표

| EXP | 실험명 | Window | Chunk | Visual | 학습 완료 | 추론 테스트 | PM/DA | Status | 비고 |
| :---: | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **01** | Basket Chunk5 | - | 5 | Linear | ✅ | ❌ | - | 🗃️ **Archive** | 초기 실험 |
| **02** | Basket Chunk10 | - | 10 | Linear | ✅ | ❌ | - | 🗃️ **Archive** | 초기 실험 |
| **03** | Basket Left Only | - | - | Linear | ✅ | ❌ | - | 🗃️ **Archive** | Left-only dataset |
| **04** | Unified Baseline | 12 | 6 | Linear | ✅ | ✅ | **65.83%** | 🥉 **Baseline** | Initial 9% 치명적 |
| **05** | Chunk k=1 | 12 | **1** | Linear | ✅ | ✅ | **89.72%** | 🥇 **Winner** | Middle/Final 100% |
| **06** | Visual Resampler | 12 | 6 | **Resampler 64** | ✅ | ✅ | **82.50%** | 🥈 **2nd Best** | Initial 81% 우수 |
| **07** | INT8 QLoRA | 12 | 6 | Resampler 64 | ❌ | ❌ | - | ❌ **Canceled** | Quantization 복잡도 |
| **08** | LoRA Fine-tune | 12 | 6 | Resampler 64 | ❌ | ❌ | - | ❌ **Canceled** | 구조 최적화 우선 |
| **09** | Resampler Latent 128 | 12 | 6 | **Resampler 128** | ✅ | ✅ | **77.50%** | ❌ **Failed** | EXP-06 대비 -5%p |
| **10** | Window 16 | **16** | 6 | Resampler 64 | ✅ | ❌ | - | ❌ **Failed** | 데이터 부족 (1 step/epoch) |
| **11** | Discrete Classification | 12 | 6 | Resampler 64 | ❌ | ❌ | - | ❌ **Failed** | KeyError: 'n_bin' |
| **12** | k=1 + Resampler | 12 | **1** | Resampler 64 | ❌ | ❌ | - | ⏳ **Training** | Hybrid, W12 context |
| **13** | k=3 Mid-range | 12 | **3** | Resampler 64 | ❌ | ❌ | - | 📅 **Planned** | Balance test |
| **14** | Resampler Depth Ablation | 12 | 6 | Resampler 64 | ❌ | ❌ | - | 📅 **Planned** | depth=4,6,8,10 |
| **15** | Final Optimized | 12 | 1 | Resampler (tuned) | ❌ | ❌ | - | 📅 **Planned** | 95% 목표 |
| **16** | Window 6 + k=1 | **6** | **1** | Linear | ✅ | ✅ | **89.72%** | 🥇 **Joint 1st** | Window 6 효율성 증명 |
| **17** | Window 8 + k=1 | **8** | **1** | Linear | ✅ | ✅ | **94.72%** | 🥇 **Champion** | CALVIN cfg 최적화 증명 |
| **12-B** | **W6 + k=1 + Res** | **6** | **1** | **Resampler 64** | ✅ | ✅ | **88.89%** | 🥈 **Joint 2nd** | Hybrid (Resampler 효과 입증) |

---

## 🏆 성능 순위 (추론 테스트 완료)

| 🥇 | **17** | **Window 8/k=1** | **94.72%** | **83.0%** | **100.0%** | **100.0%** | **Best Sequence Modeling** |
| 🥈 | **05** | Chunk k=1 | **89.72%** | 76% | 100% | 100% | 기초 최적화 모델 |
| 🥈 | **16** | Window 6/k=1 | **89.72%** | 76% | 100% | 100% | 효율적 모델 |
| 🥈 | **12** | **W6 Hybrid** | **88.89%** | **81.0%** | 100% | 77.89% | Resampler 시각효과 |
| 🥉 | **06** | Resampler 64 | **82.50%** | 81% | 83.55% | 80% | Robust initial |
| 🥉 | **09** | Resampler 128 | **77.50%** | 76% | 83.55% | 80% | Overfitting |
| 4 | **04** | Baseline | **65.83%** | **9%** | 97.37% | 70.53% | Initial 취약 |

---

## 🔬 실험 그룹별 분류

### **그룹 A: 초기 탐색 (EXP-01~03)** 🗃️
- **목적**: 기본 학습 가능성 검증
- **결과**: 학습은 성공, 체계적 평가 없음
- **상태**: Archive (참고용)

### **그룹 B: Baseline 구축 (EXP-04)** 🥉
- **목적**: 표준 성능 측정
- **결과**: 65.83% PM/DA
- **문제**: Initial Phase 9% (치명적)
- **상태**: Baseline reference

### **그룹 C: Chunk Size 최적화 (EXP-05)** 🥇
- **목적**: 학습-추론 괴리 해소
- **결과**: **89.72%** (압도적 1위!)
- **발견**: Chunk 1이 Episode 18에 최적
- **상태**: **Current Best**

### **그룹 D: Visual Encoding 개선 (EXP-06, 09)** 🥈
- **목적**: Resampler 효과 검증
- **EXP-06 결과**: 82.50% (Initial 81% 우수)
- **EXP-09 결과**: 77.50% (실패, Latent 128 과다)
- **발견**: Latent 64가 Sweet Spot
- **상태**: EXP-06 유효, EXP-09 폐기

### **그룹 E: 실패 실험들 (EXP-07, 08, 10, 11)** ❌
- **EXP-07**: Quantization 복잡도로 취소
- **EXP-08**: LoRA는 구조 최적화 후로 연기
- **EXP-10**: Window 16은 데이터 부족으로 실패
- **EXP-11**: Discrete는 Config 오류로 실패
- **상태**: 모두 중단/실패

### **그룹 F: 미래 계획 (EXP-12~15)** 📅
- **EXP-12**: k=1 + Resampler (하이브리드)
- **EXP-13**: k=3 (중간값 탐색)
- **EXP-14**: Resampler depth ablation
- **EXP-15**: Final optimized (95% 목표)
- **상태**: 계획 단계 (우선순위 재조정)

### **그룹 G: Window 최적화 (EXP-16~17)** ⏳
- **EXP-16**: Window 6 + Chunk 1
- **EXP-17**: Window 8 + Chunk 1 ⭐
- **목적**: VLA 모델 분석 기반 최적화
- **상태**: **즉시 실행 준비 완료**

---

## 📊 주요 발견 요약

### **발견 1: Chunk k=1의 우월성**
```
EXP-05 (k=1): 89.72%
EXP-04 (k=6): 65.83%
→ +23.89%p 향상!
```
**이유**: 학습-추론 일치, 데이터 최대 활용

### **발견 2: Resampler의 Initial Phase 효과**
```
EXP-06 (Resampler): Initial 81%
EXP-04 (Linear): Initial 9%
→ +72%p 향상!
```
**이유**: 압축된 표현이 robust

### **발견 3: Latent 64가 최적**
```
EXP-06 (64): 82.50%
EXP-09 (128): 77.50%
→ -5.0%p 하락
```
**이유**: 과도한 파라미터는 overfitting

### **발견 4: Window 12는 과도**
```
현재: Window 12 / Episode 18 = 67%
CALVIN: Window 8 / Episode 16-64 = 50-12%
→ 비율이 너무 높음
```
**이유**: 샘플 수 감소, 계산 비용 증가

---

## 🎯 다음 실험 우선순위

### **최우선 (이번 주)**
1. ⭐ **EXP-17**: Window 8 + Chunk 1
   - CALVIN 원본 설정
   - 예상: 91-93%
   
2. **EXP-16**: Window 6 + Chunk 1
   - 최소 Window 테스트
   - 예상: 90-92%

### **차순위 (다음 주)**
3. **EXP-12**: Chunk 1 + Resampler 64
   - EXP-05 + EXP-06 하이브리드
   - 예상: 92-94%

4. **Window-Chunk Grid Search**
   - (W=6,8,10) × (k=1) 체계적 비교
   - 최적 조합 도출

---

## 💾 학습 완료 체크포인트 위치

### **EXP-04 (Baseline)**
```
runs/unified_regression_win12/.../epoch=9-step=600.ckpt
```

### **EXP-05 (k=1, Winner!)**
```
runs/unified_regression_win12/.../unified_reg_win12_k1_20260205/epoch=5-step=2136.ckpt
```

### **EXP-06 (Resampler)**
```
runs/unified_regression_win12/.../unified_reg_win12_k6_resampler_20260205/last.ckpt
```

### **EXP-09 (Latent 128)**
```
runs/unified_regression_win12/.../exp09_resampler_latent128/last.ckpt
```

---

## 📈 성능 향상 로드맵

```
EXP-04 (Baseline): 65.83%
         ↓ +23.89%p (Chunk 1)
EXP-05 (k=1): 89.72%  ← 현재 최고
         ↓ +2-3%p (Window 8)
EXP-17 (예상): 91-93%
         ↓ +1-2%p (Resampler)
EXP-12 (예상): 92-94%
         ↓ +1-2%p (Fine-tuning)
Final (목표): 95%+
```

---

## 🚀 즉시 실행 항목

1. ✅ EXP-16, 17 Config 생성
2. ✅ 순차 학습 스크립트 작성
3. ⏳ 학습 시작 (예상 소요: 각 1시간)
4. ⏳ 추론 테스트 (예상 소요: 각 10분)
5. ⏳ 결과 분석 및 다음 단계 결정

---

**작성 완료**: 2026-02-09  
**현재 최고**: EXP-05 (89.72%)  
**다음 목표**: EXP-17 (91-93%)  
**최종 목표**: 95%+

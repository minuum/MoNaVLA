# Frozen vs LoRA: 논문 사례 조사

**작성일**: 2025-12-06  
**목적**: 교수님 미팅 준비 - VLM Frozen vs Fine-tuning 비교

---

## 📚 주요 논문 요약

### 1. RT-2 (Robotics Transformer 2) - Google DeepMind

**접근 방식**: **Co-Fine-tuning (Frozen 기반)**

**핵심 특징**:
- Pre-trained VLM (PaLM-E, PaLI-X) 기반
- VLM은 web-scale 데이터로 사전 학습 후 **"frozen" 상태 유지**
- Robotics 데이터로 **co-fine-tuning** (action-oriented adaptation)
- Action을 **text tokens**로 표현하여 VLM의 언어 이해 활용

**장점**:
- ✅ **Emergent capabilities**: 새로운 명령어 이해
- ✅ **Zero-shot generalization**: 학습하지 않은 객체/환경에서 작동
- ✅ **Reasoning**: 도구 선택, 쓰레기 판별 등
- ✅ Web knowledge 활용

**데이터 요구량**:
- Pre-training: Web-scale (수백만~수십억 이미지)
- Fine-tuning: Robotics demonstrations (상대적으로 적음)

**결론**: **Frozen VLM + Minimal Fine-tuning**이 효과적

---

### 2. OpenVLA - Stanford

**접근 방식**: **Full Fine-tuning + LoRA 옵션**

**핵심 특징**:
- 7B parameter VLA model (Llama 2 + DINOv2 + SigLIP)
- Open X-Embodiment dataset (970K demonstrations)
- **3가지 Fine-tuning 방법 제공**:
  1. **LoRA**: Parameter-efficient (A100 1개, 27GB)
  2. **Full Fine-tuning**: 모든 7.5B params (A100 8개)
  3. **OFT (Optimized Fine-Tuning)**: 최신 권장 (25-50x faster)

**성능 비교**:
- LoRA: 효율적, 성능 유사
- Full Fine-tuning: 최고 성능 (분포 차이 클 때)
- OFT: 76.5% → 97.1% success rate

**데이터 요구량**:
- Pre-training: 970K demonstrations
- Fine-tuning: Minimal (수백~수천)

**결론**: **LoRA가 효율적**, Full은 성능 극대화

---

### 3. RoboFlamingo - TU Darmstadt

**접근 방식**: **Frozen VLM + Lightweight Policy Head**

**핵심 특징**:
- OpenFlamingo VLM을 **완전히 frozen**
- **Policy head만 학습** (imitation learning)
- VLM: Vision-language comprehension
- Policy head: Sequential history + low-level control

**장점**:
- ✅ **Data efficiency**: 매우 적은 demonstration 필요
- ✅ **Zero-shot generalization**: 새로운 객체/명령어
- ✅ **Cost-effective**: Single GPU 학습 가능
- ✅ **Open-loop control**: 저성능 플랫폼 배포 가능

**성능**:
- CALVIN benchmark: State-of-the-art
- 기존 방법 대비 큰 성능 향상

**데이터 요구량**:
- Pre-training: VLM 사전 학습 (frozen)
- Fine-tuning: **매우 적음** (수십~수백)

**결론**: **Frozen VLM이 가장 효율적**, 우리 상황과 가장 유사

---

### 4. PaLM-E - Google Research

**접근 방식**: **Frozen vs Fine-tuning 모두 실험**

**핵심 특징**:
- Embodied multimodal language model
- **2가지 variant 비교**:
  1. **Frozen LLM + Trained Encoders**: Input encoders만 학습
  2. **Full Fine-tuning**: 모든 params 학습

**결과**:
- **Fine-tuning이 일반적으로 더 좋은 성능**
- Frozen: 효율적, general representation 유지
- Fine-tuning: Task-specific adaptation 우수

**특이사항**:
- OK-VQA benchmark: Fine-tuning 없이도 SOTA
- General language proficiency 유지

**데이터 요구량**:
- Pre-training: Large-scale language + vision + embodied data
- Fine-tuning: Task-specific (다양)

**결론**: **Fine-tuning이 성능 우수**, Frozen은 효율성 우수

---

## 📊 비교 요약표

| 모델 | 접근 방식 | VLM 상태 | 데이터 효율성 | 성능 | 계산 비용 |
|:---|:---|:---|:---:|:---:|:---:|
| **RT-2** | Co-Fine-tuning | Frozen → Fine-tuned | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **OpenVLA (LoRA)** | LoRA | Partially Frozen | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **OpenVLA (Full)** | Full Fine-tuning | Trainable | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **RoboFlamingo** | Frozen + Policy | **Fully Frozen** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **PaLM-E (Frozen)** | Frozen + Encoders | Frozen LLM | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **PaLM-E (Full)** | Full Fine-tuning | Trainable | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |

---

## 🎯 우리 프로젝트에 적용

### 우리 상황:
- **데이터**: 500 episodes (매우 제한적)
- **태스크**: Mobile navigation (7DOF → 2DOF)
- **목표**: 빠른 프로토타입, 효율적 학습

### 추천 접근 방식: **Frozen VLM + Action Head (RoboFlamingo 방식)**

**이유**:
1. ✅ **데이터 효율성**: 500 episodes로 충분
2. ✅ **계산 효율성**: Single GPU 학습 가능
3. ✅ **일반화**: VLM의 사전 지식 활용
4. ✅ **빠른 실험**: Policy head만 학습

### 대안: **LoRA (OpenVLA 방식)**

**언제 사용**:
- Frozen만으로 성능 부족할 때
- 데이터 1,000+ episodes 확보 시
- VLM adaptation 필요할 때

---

## 📝 교수님 미팅 포인트

### 1. **Frozen이 우리에게 적합한 이유**
- 데이터 제한적 (500 episodes)
- Mobile task는 manipulation보다 단순
- VLM의 spatial reasoning 활용 가능

### 2. **Context Vector 비교의 의미**
- Frozen: VLM의 원본 representation 유지
- LoRA: Task-specific adaptation
- 유사도 높으면 → Frozen으로 충분
- 유사도 낮으면 → LoRA 필요

### 3. **예상 결과**
- Context similarity: **높을 것** (0.8+)
  - 이유: Mobile task가 VLM 사전 지식과 align
- Performance: **비슷할 것**
  - 이유: Action head가 핵심 역할

### 4. **다음 단계**
1. Frozen baseline 분석 완료 ✅
2. LoRA 학습 (데이터 추가 수집 고려)
3. Context vector 비교
4. 성능 비교 (RMSE, Success rate)

---

## 📚 참고 문헌

1. **RT-2**: Brohan et al., "RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control", 2023
2. **OpenVLA**: Kim et al., "OpenVLA: An Open-Source Vision-Language-Action Model", 2024
3. **RoboFlamingo**: Li et al., "Vision-Language Foundation Models as Effective Robot Imitators", 2023
4. **PaLM-E**: Driess et al., "PaLM-E: An Embodied Multimodal Language Model", 2023

---

**결론**: **Frozen VLM + Action Head 접근이 우리 상황에 최적**. RoboFlamingo 사례가 가장 유사하며, 데이터 효율성과 성능의 균형이 우수함.

# VLA에서 Frozen VLM + Instruction Grounding 해결 사례 분석

**작성일**: 2026-01-11  
**목적**: LEFT/RIGHT 문제 해결 방법 조사

---

## 🔍 핵심 발견: Frozen VLM은 실패, LoRA가 해결책

### 우리 문제 요약
- **Frozen VLM** (Kosmos-2 scratch 또는 RoboVLMs pretrained)
- **LEFT vs RIGHT 차이**: 0.000 (완전 실패)
- **원인**: Text embedding이 frozen되어 instruction 구분 불가

---

## ✅ VLA 분야 해결 사례

### 1. InstructVLA: Two-Stage + LoRA 접근법

**논문**: InstructVLA (arXiv)  
**핵심 전략**: **Action Expert Frozen + VLM LoRA Fine-tuning**

#### Two-Stage Training

```
Stage 1: Action Pretraining
  ├─ "Action Expert" 학습
  ├─ VLM에서 action 생성 학습
  └─ Action LoRA adapter만 학습

Stage 2: VLA Instruction Tuning (VLA-IT)
  ├─ Action Expert FROZEN ❄️
  ├─ Language LoRA adapter 추가
  ├─ MoE (Mixture-of-Experts) 모듈 학습
  └─ VLM의 multimodal reasoning 재활성화
```

**성과**:
- ✅ Catastrophic forgetting 방지
- ✅ Complex instruction 처리 가능
- ✅ MoE 모듈: 220M params만 학습 (메모리 효율적)

**핵심**: 
> "Once the action expert is proficient, further adaptation of the LLM backbone with **new language LoRA** enables InstructVLA to handle more complex instructions without compromising action skills"

---

### 2. OpenVLA: LoRA Fine-tuning의 대성공

**모델**: OpenVLA (7B params, Stanford/UC Berkeley/TRI/Google DeepMind)  
**데이터**: 970K robot trajectories (Open X-Embodiment)

#### LoRA Fine-tuning 결과

| 방법 | LIBERO Success Rate | Real ALOHA Success Rate |
|------|---------------------|------------------------|
| Original OpenVLA | 76.5% | - |
| **OpenVLA + LoRA (OFT)** | **97.1%** | - |
| **OpenVLA + LoRA (OFT+)** | **~97%** | **+15%** vs others |

**개선 사항**:
- ✅ **Language grounding 크게 향상**
- ✅ Multi-object task에서 from-scratch보다 우수
- ✅ Instruction tuning으로 92% 성능 향상

**Optimized Fine-Tuning (OFT) Recipe**:
```python
- Parallel decoding
- Action chunking  
- Continuous action representation
- FiLM (Feature-wise Linear Modulation)
→ 26x throughput increase
```

**핵심 결론**:
> "Fine-tuned OpenVLA policies consistently **outperform models trained from scratch**, especially in multi-task scenarios that require **grounding language to complex behaviors**"

---

### 3. RT-2: VLM Co-Fine-tuning 전략

**모델**: RT-2 (Vision-Language-Action Models Transfer Web Knowledge)  
**전략**: **VLM backbone co-fine-tuning**

- Pretrained VLM backbone 사용
- Web-scale vision-language data + robot trajectory data로 co-fine-tuning
- Broad internet knowledge를 robotic control로 transfer

**성과**:
- ✅ Web knowledge를 robot control에 활용
- ✅ OpenVLA가 RT-2-X (55B params)를 outperform (7B로!)

---

## 📊 성공 사례 공통점

| 항목 | 성공 사례 | 우리 현재 |
|------|----------|----------|
| **VLM 상태** | LoRA fine-tuning ✅ | Frozen ❌ |
| **Text Embedding** | 학습됨 ✅ | 고정됨 ❌ |
| **Instruction Grounding** | 성공 ✅ | 실패 ❌ |
| **메모리 효율** | LoRA (220M) ✅ | N/A |

---

## 💡 해결 방안: LoRA Fine-tuning 필수

### 옵션 A: InstructVLA 방식 (Two-Stage)

```json
// Stage 1: Action Pretraining (이미 완료)
{
  "train_setup": {
    "freeze_backbone": true,
    "lora_enable": true,
    "lora_targets": ["action_head"]  // Action LoRA만
  }
}

// Stage 2: VLA Instruction Tuning
{
  "train_setup": {
    "freeze_backbone": false,  // ← Unfreeze!
    "lora_enable": true,
    "lora_targets": ["text_model", "vision_model"],  // Language LoRA 추가
    "lora_r": 16,
    "lora_alpha": 32,
    "freeze_action_expert": true  // Action Head는 frozen
  }
}
```

**예상 효과**:
- ✅ Action skills 유지
- ✅ Instruction grounding 획득
- ✅ 메모리 효율적 (LoRA adapters만)

---

### 옵션 B: OpenVLA 방식 (Direct LoRA Fine-tuning)

```json
{
  "train_setup": {
    "freeze_backbone": false,  // ← VLM unfreeze
    "lora_enable": true,
    "lora_r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.1,
    "lora_targets": ["q_proj", "v_proj", "k_proj", "o_proj"]  // Attention layers
  }
}
```

**OpenVLA OFT+ Recipe**:
- Parallel decoding
- Action chunking
- Continuous action representation
- FiLM module

**예상 성과** (OpenVLA 기준):
- 76.5% → 97.1% success rate
- +92% instruction grounding improvement

---

## 🎯 권장 전략

### **즉시 구현**: LoRA Fine-tuning

```python
# Mobile_VLA/configs/mobile_vla_lora.json

{
  "train_setup": {
    "freeze_backbone": false,       // ← 핵심!
    "lora_enable": true,
    "lora_r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.1,
    "lora_bias": "none",
    "lora_targets": [
      "q_proj",   // Query projection
      "v_proj",   // Value projection  
      "k_proj",   // Key projection
      "o_proj"    // Output projection
    ]
  },
  "pretrained_vlm_path": "pretrained_ckpts/checkpoints/kosmos_ph_google-robot-post-train.pt",
  "load_vlm_only": true
}
```

**메모리 예상**:
- VLM frozen: 1.66B params (고정)
- LoRA adapters: ~220M params (학습)
- Action Head: 12.7M params (학습)
- **Total trainable**: ~233M params (전체의 14%)

---

## 📚 참고 논문

1. **InstructVLA** (arXiv)
   - Two-stage training with frozen action export
   - Language LoRA + Action LoRA decoupling
   - MoE adaptation framework

2. **OpenVLA** (Stanford et al.)
   - 7B model outperforms 55B RT-2-X
   - LoRA fine-tuning: 76.5% → 97.1%
   - OFT+ recipe for high-frequency control

3. **RT-2** (Google DeepMind)
   - VLM co-fine-tuning strategy
   - Web knowledge transfer to robotics

---

## 🔬 실험 계획

### Phase 1: LoRA Fine-tuning 구현

1. LoRA config 작성
2. Pretrained VLM + LoRA로 재학습
3. LEFT/RIGHT ablation test

**예상 결과**:
- Instruction 차이: 0.000 → **> 0.05** ✅
- Success rate: 대폭 향상

### Phase 2: OFT+ Recipe 적용

1. Parallel decoding 구현
2. Action chunking 최적화
3. FiLM module 추가

---

## 결론

> **Frozen VLM = Instruction Grounding 불가능**  
> **LoRA Fine-tuning = 필수 해결책**

**핵심 교훈**:
1. VLA 분야에서 frozen VLM은 실패 사례
2. 모든 성공 사례는 **LoRA 또는 VLM fine-tuning** 사용
3. "No fine-tuning"은 불가능 → **"Efficient fine-tuning (LoRA)"**로 전환

**다음 단계**: LoRA config 작성 및 재학습 시작! 🚀

# 🔍 정확한 모델 구조 파악 - Frozen vs LoRA

**작성일**: 2025-12-04 02:54  
**핵심**: Mobile-VLA, RoboVLMs, Kosmos-2, Frozen, LoRA 모두 다름!

---

## 📊 **핵심 개념 정리**

### **1. Backbone (VLM)**
```
Microsoft Kosmos-2 (원본)
├── Vision Encoder (ViT)
├── Language Model
└── Multimodal Connector

이걸 기반으로:
→ RoboKosMos (RoboVLMs의 Kosmos-2 버전)
→ Mobile-VLA (우리가 만든 것)
```

### **2. RoboVLMs vs Mobile-VLA**
```
RoboVLMs (원본):
- Backbone: Kosmos-2
- Policy Head: LSTMDecoder (7DOF)
- 학습 방식: Full Fine-tuning (VLM도 학습)
- 데이터: OXE-magic-soup (Manipulator)

Mobile-VLA (우리):
- Backbone: Kosmos-2 (처음에는 Microsoft 원본)
- Policy Head: MobileVLALSTMDecoder (2DOF)
- 학습 방식: Frozen VLM + LoRA
- 데이터: 250 episodes (Mobile)
```

### **3. Frozen vs LoRA**
```
Frozen (고정):
- VLM 파라미터 업데이트 안 함
- freeze_backbone: true
- lora_enable: true/false (독립적!)

LoRA (Low-Rank Adaptation):
- VLM에 작은 adapter 추가
- VLM 원본은 안 건드리고 adapter만 학습
- lora_enable: true
- lora_r: 32, lora_alpha: 16
```

---

## 🎯 **실제 우리가 학습한 것**

### **Config 분석** (`mobile_vla_20251203_lora.json`)
```json
{
  "model_path": ".vlms/kosmos-2-patch14-224",  // Microsoft Kosmos-2 원본
  "model_load_path": null,  // ❌ RoboVLMs checkpoint 안 씀!
  
  "train_setup": {
    "freeze_backbone": true,   // ✅ VLM 고정
    "lora_enable": true,       // ✅ LoRA 활성화
    "lora_r": 32,
    "lora_alpha": 16,
    "train_vision": false      // Vision도 안 학습
  },
  
  "act_head": {
    "type": "MobileVLALSTMDecoder",  // 우리 것
    "action_dim": 2,  // 2DOF
    "hidden_size": 512
  }
}
```

### **실제 학습된 모델 구조**
```
Microsoft Kosmos-2 (Frozen + LoRA)
├── Vision Encoder (Frozen + LoRA adapters)
├── Language Model (Frozen + LoRA adapters)
├── Multimodal Connector (Frozen)
└── MobileVLALSTMDecoder (랜덤 초기화 → 학습됨)
     ├── Input: (1, 8, 1, 2048) context
     └── Output: (1, 10, 2) velocity
```

**학습된 파라미터**:
1. LoRA adapters (VLM 내부, 매우 적음)
2. MobileVLALSTMDecoder (전체, 2DOF action head)

---

## 📊 **RoboVLMs 원본 Config 비교**

### **RoboVLMs** (`kosmos_ph_oxe-pretrain.json`)
```json
{
  "train_setup": {
    "freeze_backbone": false,  // ❌ VLM도 학습!
    "lora_enable": false,      // ❌ LoRA 안 씀!
    "train_vision": true,      // ✅ Vision도 학습
    "train_text_embedding": true  // ✅ Text도 학습
  },
  
  "act_head": {
    "type": "LSTMDecoder",     // 다름!
    "action_dim": 7,           // 7DOF (Manipulator)
    "hidden_size": 1024        // 크기도 다름
  },
  
  "train_dataset": {
    "type": "OpenVLADataset",  // OXE dataset
    "data_mix": "oxe_magic_soup"  // Manipulator 데이터
  }
}
```

**RoboVLMs는 Full Fine-tuning!**
- VLM 전체 학습
- 7DOF action head
- Manipulator 데이터

---

## 🔬 **정확한 테스트 시나리오**

### **현재 완료된 것**
```
✅ Test 1: Microsoft Kosmos-2 (Frozen + LoRA) + MobileVLALSTMDecoder
   - Pretrain: 일반 이미지 (COCO)
   - VLM: Frozen + LoRA adapters
   - Action Head: 2DOF (학습됨)
   - 데이터: 250 episodes (Mobile)
   - 결과: Loss 0.013
```

### **다음 테스트 옵션들**

#### **Option A: RoboVLMs ckpt로 초기화 (동일 설정)**
```json
{
  "model_load_path": ".vlms/RoboVLMs/checkpoints/kosmos_ph_oxe-pretrain.pt",
  "freeze_backbone": true,  // 유지
  "lora_enable": true,      // 유지
  "act_head": {
    "type": "MobileVLALSTMDecoder",  // 교체!
    "action_dim": 2
  }
}
```
**의미**: Robot pretrain VLM (Frozen + LoRA) + 새 2DOF head

#### **Option B: RoboVLMs Full Fine-tune**
```json
{
  "model_load_path": ".vlms/RoboVLMs/checkpoints/kosmos_ph_oxe-pretrain.pt",
  "freeze_backbone": false,  // ❌ 변경!
  "lora_enable": false,      // ❌ 변경!
  "train_vision": true,      // ✅ 전체 학습
  "act_head": {
    "type": "MobileVLALSTMDecoder",
    "action_dim": 2
  }
}
```
**문제**: 250 episodes로 VLM 전체 Fine-tune?  
→ **Overfitting 위험! ❌**

#### **Option C: RoboVLMs의 7DOF head 그대로 사용**
```json
{
  "model_load_path": ".vlms/RoboVLMs/checkpoints/kosmos_ph_oxe-pretrain.pt",
  "freeze_backbone": true,
  "act_head": {
    "type": "LSTMDecoder",  // RoboVLMs 것
    "action_dim": 7  // 7DOF 그대로
  }
}
```
**문제**: 우리 robot은 2DOF! → 호환 안 됨

---

## 🎯 **현실적인 비교 테스트**

| Test | VLM Init | VLM Frozen | LoRA | Action Head | 데이터 | 예상 |
| :--- | :--- | :---: | :---: | :--- | :---: | :--- |
| **T1 (완료)** | Kosmos-2 | ✅ | ✅ | MobileVLA (2DOF) | 250 | Loss 0.013 |
| **T2 (가능)** | RoboVLMs | ✅ | ✅ | MobileVLA (2DOF) | 250 | Loss < 0.013? |
| **T3 (위험)** | RoboVLMs | ❌ | ❌ | MobileVLA (2DOF) | 250 | Overfitting! |

**추천**: **Test T2만 실행**  
- RoboVLMs checkpoint로 초기화
- Frozen + LoRA 유지 (동일)
- 2DOF head만 교체
- Robot pretrain 효과만 순수 비교

---

## 🔧 **정확한 Config (T2용)**

```json
{
  "exp_name": "mobile_vla_robovlms_frozen_lora_20251204",
  
  // RoboVLMs checkpoint 로드
  "model_load_path": ".vlms/RoboVLMs/checkpoints/kosmos_ph_oxe-pretrain.pt",
  "model_path": ".vlms/kosmos-2-patch14-224",
  
  "train_setup": {
    "freeze_backbone": true,  // ✅ T1과 동일
    "lora_enable": true,      // ✅ T1과 동일
    "lora_r": 32,
    "lora_alpha": 16,
    "train_vision": false  // ✅ T1과 동일
  },
  
  "act_head": {
    "type": "MobileVLALSTMDecoder",  // ✅ 우리 것
    "action_dim": 2,  // ✅ 2DOF
    "hidden_size": 512  // ✅ T1과 동일
  }
}
```

**핵심 차이점**:  
- **T1**: Kosmos-2 (일반 이미지 pretrain)
- **T2**: RoboVLMs (Robot manipulation pretrain)
- **나머지 모든 설정 동일!**

---

## 📝 **결론**

### **우리가 실제로 한 것**
```
Microsoft Kosmos-2 (Frozen + LoRA)
+ MobileVLALSTMDecoder (2DOF, 새로 학습)
→ Loss 0.013
```

### **다음 테스트**
```
RoboVLMs Kosmos-2 (Frozen + LoRA, Robot pretrain)
+ MobileVLALSTMDecoder (2DOF, 새로 학습)
→ Loss ???
```

**비교 가능**: VLM pretrain만 다름 (일반 vs Robot)  
**의미**: Robot pretrain이 Mobile에 도움되는가?

---

*이제 정확히 이해했습니다!*

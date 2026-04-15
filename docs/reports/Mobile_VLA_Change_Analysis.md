# 🔄 RoboVLMs → Mobile VLA 변경/유지/전이 상세 분석

## 🎯 변경 필요 부분 (CHANGE)

### 1. 📊 액션 공간 완전 재설계
#### ❌ 제거할 것
```python
# RoboVLMs 7D 액션 공간
action_space = {
    "arm": [x, y, z, roll, pitch, yaw],  # 6DOF 로봇 팔
    "gripper": [open/close]               # 그리퍼 제어
}
```

#### ✅ 새로 구현할 것
```python
# Mobile VLA 4D 액션 공간
action_space = {
    "linear_x": [-2.0, 2.0],     # 전진/후진 속도 (m/s)
    "linear_y": [-1.0, 1.0],     # 좌우 이동 속도 (m/s)  
    "angular_z": [-3.14, 3.14],  # 회전 속도 (rad/s)
    "action_type": [0, 1, 2, 3]  # 0:이동, 1:회전, 2:정지, 3:특수
}
```

### 2. 🗃️ 데이터 처리 파이프라인 재구성
#### ❌ 제거할 것
```python
# Calvin/Bridge 데이터 로더
class CalvinDataset:
    def __getitem__(self, idx):
        return {
            "rgb": self.episodes[idx]["rgb"],           # [T, H, W, 3]
            "action": self.episodes[idx]["action"],     # [T, 7] 
            "language": self.episodes[idx]["language"]  # "pick up the cube"
        }
```

#### ✅ 새로 구현할 것  
```python
# Mobile VLA 데이터 로더 (mobile_vla_data_collector 기반)
class MobileNavigationDataset:
    def __getitem__(self, idx):
        return {
            "images": self.episodes[idx]["images"],                    # [T, H, W, 3]
            "actions": self.episodes[idx]["actions"],                  # [T, 4]
            "action_event_types": self.episodes[idx]["action_event_types"], # [T]
            "scenario": self.episodes[idx]["scenario"],                # "1box_vert_left" 
            "language": self.korean_instructions[scenario]             # "왼쪽으로 돌아서 컵까지 가세요"
        }
```

### 3. 🧠 Policy Head 완전 재작성
#### ❌ 제거할 것
```python
# RoboVLMs BasePolicyHead
class BasePolicyHead(nn.Module):
    def __init__(self, hidden_size):
        self.arm_head = MLPTanhHead(hidden_size, 6)      # 6DOF arm actions
        self.gripper_head = MLPSigmoidHead(hidden_size, 1) # gripper actions
        
    def forward(self, features):
        arm_actions = self.arm_head(features)        # [-1, 1]^6
        gripper_actions = self.gripper_head(features) # [0, 1]
        return torch.cat([arm_actions, gripper_actions], dim=-1)
```

#### ✅ 새로 구현할 것
```python
# Mobile VLA MobilePolicyHead  
class MobilePolicyHead(nn.Module):
    def __init__(self, hidden_size):
        self.movement_head = MLPTanhHead(hidden_size, 3)    # linear_x, linear_y, angular_z
        self.action_type_head = MLPHead(hidden_size, 4)     # action type classification
        
    def forward(self, features):
        movement_actions = self.movement_head(features)     # [-1, 1]^3 → scale to actual bounds
        action_types = self.action_type_head(features)      # [4] logits
        return {
            "movement": movement_actions,
            "action_type": action_types
        }
```

### 4. 📈 손실 함수 재설계
#### ❌ 제거할 것
```python
# RoboVLMs 손실 함수
def get_loss(self, prediction):
    loss_arm_act = F.mse_loss(pred_arm, target_arm)
    loss_gripper_act = F.cross_entropy(pred_gripper, target_gripper)
    return loss_arm_act + self.arm_gripper_loss_ratio * loss_gripper_act
```

#### ✅ 새로 구현할 것
```python
# Mobile VLA 손실 함수
def get_mobile_loss(self, prediction):
    # 연속 액션 손실 (movement)
    movement_loss = F.mse_loss(pred_movement, target_movement)
    
    # 액션 타입 분류 손실
    type_loss = F.cross_entropy(pred_action_type, target_action_type)
    
    # 시나리오 일관성 손실 (새로운 기능)
    scenario_consistency_loss = self.compute_scenario_consistency(
        pred_actions, scenario_context
    )
    
    return movement_loss + 0.5 * type_loss + 0.1 * scenario_consistency_loss
```

---

## ✅ 유지할 부분 (KEEP)

### 1. 🏗️ 전체 학습 프레임워크
#### ✅ 유지할 이유
```python
# PyTorch Lightning 기반 BaseTrainer 구조는 매우 안정적
class BaseTrainer(pl.LightningModule):
    def configure_optimizers(self):      # ✅ 유지
    def training_step(self, batch):      # ✅ 유지  
    def validation_step(self, batch):    # ✅ 유지
    def _get_loss(self, prediction):     # 🔄 내용만 수정, 구조 유지
```

### 2. 🤖 VLM 백본 아키텍처
#### ✅ 유지할 이유
```python
# PaliGemma, LLaVA, Kosmos 등 백본은 강력한 시각-언어 이해 능력 보유
# 단지 출력 헤드만 mobile 용으로 교체
class RoboPaliGemma:
    def __init__(self):
        self.vision_encoder = ...        # ✅ 완전 유지
        self.language_model = ...        # ✅ 완전 유지  
        self.vision_resampler = ...      # ✅ 완전 유지
        # self.policy_head = BasePolicyHead()  ❌ 교체
        self.policy_head = MobilePolicyHead() # ✅ 새로 연결
```

### 3. 📊 데이터 전처리 유틸리티  
#### ✅ 유지할 이유
```python
# 이미지 처리, 시퀀스 패딩 등 기본 기능은 범용적
from robovlms.data.data_utils import (
    pad_sequences,           # ✅ 유지 - 시퀀스 길이 맞춤
    normalize_action,        # 🔄 수정 - 4D 액션용으로 적응
    get_tensor_chunk,        # ✅ 유지 - 청크 단위 처리
    mu_law_companding       # ✅ 유지 - 액션 압축
)
```

### 4. 🔧 학습 최적화 로직
#### ✅ 유지할 이유
```python
# 학습률 스케줄링, 옵티마이저 설정 등은 검증된 방법
def configure_optimizers(self):
    optimizer = torch.optim.AdamW(self.get_grouped_params(self.model), lr=eff_lr) # ✅ 유지
    scheduler = get_cosine_schedule_with_warmup(...)  # ✅ 유지
    return {"optimizer": optimizer, "lr_scheduler": scheduler}  # ✅ 유지
```

---

## 🔄 전이할 부분 (TRANSFER)

### 1. 💡 Calvin Sequential Task → Mobile Navigation Scenarios
#### 🎯 핵심 아이디어 전이
```python
# Calvin: "pick and place" 시퀀셜 태스크
calvin_sequence = [
    "pick up the blue block",      # Task 1
    "place it on the red plate",   # Task 2  
    "slide the drawer open"        # Task 3
]

# Mobile VLA: 시나리오별 네비게이션 시퀀스
mobile_sequence = [
    "1box_vert_left",              # 시나리오 1: 왼쪽 우회 경로
    "approach_obstacle",           # Task 1: 장애물 접근
    "avoid_left",                  # Task 2: 왼쪽으로 회피
    "reach_target"                 # Task 3: 목표 도달
]
```

#### 🔄 전이 방법
```python
# Calvin의 시퀀셜 성공률 평가 → Mobile Navigation 시나리오 성공률
class SequentialNavigationEvaluator:
    def evaluate_scenario_sequence(self, model, scenarios):
        success_rates = {}
        for scenario in ["1box_vert_left", "1box_vert_right", ...]:
            success_rate = self.test_scenario(model, scenario)
            success_rates[scenario] = success_rate
        return success_rates
```

### 2. 🧠 Vision-Language Understanding → Spatial-Language Navigation  
#### 🎯 핵심 아이디어 전이
```python
# RoboVLMs: 이미지 + 조작 명령 이해
robovlm_input = {
    "image": camera_rgb,
    "instruction": "pick up the red block on the table"
}

# Mobile VLA: 이미지 + 네비게이션 명령 이해  
mobile_vla_input = {
    "image": camera_rgb,
    "instruction": "왼쪽 경로로 돌아서 빨간 컵까지 가세요",
    "scenario_context": "1box_vert_left"  # 추가 컨텍스트
}
```

#### 🔄 전이 방법
```python
# 기존 VLM의 시각-언어 융합 메커니즘 활용
class SpatialLanguageEncoder:
    def __init__(self, vlm_backbone):
        self.vision_encoder = vlm_backbone.vision_encoder      # ✅ 직접 전이
        self.language_encoder = vlm_backbone.language_encoder  # ✅ 직접 전이
        self.spatial_fusion = MultiheadAttention(...)          # 🔄 공간 이해 강화
        
    def encode_spatial_instruction(self, image, instruction, scenario):
        vision_features = self.vision_encoder(image)           # ✅ 기존 방식
        language_features = self.language_encoder(instruction) # ✅ 기존 방식
        spatial_context = self.encode_scenario(scenario)       # 🆕 새로운 기능
        return self.spatial_fusion(vision_features, language_features, spatial_context)
```

### 3. 📊 Action Chunking → Mobile Action Sequences
#### 🎯 핵심 아이디어 전이
```python
# RoboVLMs: 조작 액션 청킹
manipulation_chunk = [
    [0.1, 0.0, -0.2, 0.0, 0.0, 0.0, 0],  # approach
    [0.0, 0.0, -0.1, 0.0, 0.0, 0.0, 1],  # grasp
    [0.0, 0.0, 0.3, 0.0, 0.0, 0.0, 1],   # lift
]

# Mobile VLA: 네비게이션 액션 시퀀스  
navigation_chunk = [
    [1.0, 0.0, 0.0, 0],    # forward
    [0.0, 0.0, 1.57, 1],   # turn_left  
    [1.0, 0.0, 0.0, 0],    # forward
    [0.0, 0.0, 0.0, 2]     # stop
]
```

#### 🔄 전이 방법
```python
# 액션 청킹 로직 재사용, 액션 공간만 변경
class MobileActionChunker:
    def __init__(self, chunk_size=8):
        self.chunk_size = chunk_size  # ✅ 기존 청킹 사이즈 유지
        
    def create_action_chunk(self, current_obs, target_scenario):
        # 🔄 4D 액션으로 청킹 로직 적용
        action_sequence = self.predict_action_sequence(current_obs, target_scenario)
        return action_sequence[:self.chunk_size]  # ✅ 기존 청킹 방식 유지
```

### 4. 📈 Multi-Task Learning → Multi-Scenario Learning
#### 🎯 핵심 아이디어 전이
```python
# RoboVLMs: 다중 태스크 학습 (pick, place, push, etc.)
multi_task_learning = {
    "pick_task_weight": 1.0,
    "place_task_weight": 1.0, 
    "push_task_weight": 0.8,
    "slide_task_weight": 0.6
}

# Mobile VLA: 다중 시나리오 학습 (8가지 컵 도달 시나리오)
multi_scenario_learning = {
    "1box_vert_left_weight": 1.0,
    "1box_vert_right_weight": 1.0,
    "1box_hori_left_weight": 1.2,    # 더 어려운 시나리오
    "1box_hori_right_weight": 1.1,
    "2box_vert_left_weight": 1.5,    # 가장 어려운 시나리오
    "2box_vert_right_weight": 1.4,
    "2box_hori_left_weight": 1.8,
    "2box_hori_right_weight": 1.6
}
```

#### 🔄 전이 방법
```python
# 기존 멀티태스크 학습 프레임워크를 시나리오별로 적용
class MultiScenarioTrainer(BaseTrainer):
    def __init__(self, configs):
        super().__init__(configs)
        # ✅ 기존 멀티태스크 학습 로직 재사용
        self.scenario_weights = configs["scenario_weights"]
        
    def training_step(self, batch, batch_idx):
        # 🔄 시나리오별 가중치 적용
        scenario = batch["scenario"]
        loss = self.compute_loss(batch)
        weighted_loss = loss * self.scenario_weights[scenario]
        return weighted_loss
```

---

## 🎯 액션 종류에 따른 구체적 변화

### 1. 🎮 액션 표현 방식 변화
#### ❌ 기존 (RoboVLMs)
```python
# 7D 연속 액션 + 이산 그리퍼
action_representation = {
    "type": "continuous + discrete",
    "arm_actions": torch.FloatTensor([x, y, z, roll, pitch, yaw]),  # 6D 연속
    "gripper_action": torch.LongTensor([0 or 1])                   # 1D 이산
}
```

#### ✅ 새로운 (Mobile VLA)
```python
# 3D 연속 액션 + 1D 이산 타입
action_representation = {
    "type": "continuous + discrete",  
    "movement_actions": torch.FloatTensor([linear_x, linear_y, angular_z]),  # 3D 연속
    "action_type": torch.LongTensor([0, 1, 2, or 3])                        # 1D 이산
}
```

### 2. 📊 액션 정규화 변화
#### ❌ 기존 정규화
```python
# RoboVLMs 액션 정규화 (-1 ~ 1 범위)
def normalize_arm_action(action):
    # 6DOF arm: 각 축마다 다른 범위
    arm_bounds = [
        [-0.5, 0.5],   # x translation
        [-0.3, 0.3],   # y translation  
        [-0.4, 0.4],   # z translation
        [-π, π],       # roll rotation
        [-π/2, π/2],   # pitch rotation
        [-π, π]        # yaw rotation
    ]
    return normalize_to_minus_one_one(action, arm_bounds)
```

#### ✅ 새로운 정규화
```python
# Mobile VLA 액션 정규화 (mobile_vla_data_collector 기준)
def normalize_mobile_action(action):
    # mobile_vla_data_collector의 WASD_TO_CONTINUOUS 기준
    mobile_bounds = [
        [-2.0, 2.0],    # linear_x (전진/후진)
        [-1.0, 1.0],    # linear_y (좌우 이동)
        [-3.14, 3.14]   # angular_z (회전)
    ]
    # action_type은 정규화 없이 원핫 인코딩
    return normalize_to_minus_one_one(action[:3], mobile_bounds)
```

### 3. 🔄 액션 예측 로직 변화
#### ❌ 기존 예측
```python
class RoboVLMPredictor:
    def predict_action(self, observation):
        # 이미지 + 언어 → 7D 액션 예측
        vlm_features = self.encode_multimodal(observation["image"], observation["text"])
        
        # 조작용 액션 예측
        arm_action = self.arm_head(vlm_features)      # 6D 연속
        gripper_action = self.gripper_head(vlm_features)  # 1D 이산
        
        return torch.cat([arm_action, gripper_action])
```

#### ✅ 새로운 예측  
```python
class MobileVLAPredictor:
    def predict_action(self, observation):
        # 이미지 + 언어 + 시나리오 → 4D 액션 예측
        multimodal_features = self.encode_multimodal(
            observation["image"], 
            observation["text"],
            observation["scenario"]  # 🆕 시나리오 컨텍스트 추가
        )
        
        # 네비게이션용 액션 예측
        movement_action = self.movement_head(multimodal_features)  # 3D 연속
        action_type = self.action_type_head(multimodal_features)   # 1D 이산
        
        return {
            "movement": movement_action,
            "action_type": torch.argmax(action_type)
        }
```

### 4. 📈 액션 학습 전략 변화
#### ❌ 기존 학습
```python
# RoboVLMs: 조작 정확도 중심 학습
def compute_manipulation_loss(pred_actions, target_actions):
    arm_loss = F.mse_loss(pred_actions[:6], target_actions[:6])
    gripper_loss = F.cross_entropy(pred_actions[6:], target_actions[6:])
    
    # 정밀한 조작을 위한 높은 가중치
    return arm_loss + 5.0 * gripper_loss  # 그리퍼 정확도 중요
```

#### ✅ 새로운 학습
```python
# Mobile VLA: 경로 효율성 + 안전성 중심 학습
def compute_navigation_loss(pred_actions, target_actions, scenario_context):
    movement_loss = F.mse_loss(pred_actions["movement"], target_actions["movement"])
    type_loss = F.cross_entropy(pred_actions["action_type"], target_actions["action_type"])
    
    # 시나리오별 안전성 가중치
    safety_weight = get_scenario_safety_weight(scenario_context)
    
    # 경로 효율성 손실 (새로운 개념)
    efficiency_loss = compute_path_efficiency_loss(pred_actions, scenario_context)
    
    return movement_loss + 2.0 * type_loss + safety_weight * efficiency_loss
```

---

## 🚀 구현 우선순위별 변경사항

### Phase 1: 데이터 레이어 변경 (즉시 필요)
1. **HDF5 → Calvin 변환기**: mobile_vla_data_collector 출력을 RoboVLMs 입력으로
2. **4D 액션 정규화**: 새로운 액션 공간에 맞는 정규화 함수
3. **시나리오 인코더**: 8가지 시나리오를 임베딩으로 변환

### Phase 2: 모델 레이어 변경 (1주차)
1. **MobilePolicyHead**: 4D 액션 전용 정책 헤드
2. **ScenarioAwareEncoder**: 시나리오 컨텍스트 융합
3. **Mobile 손실 함수**: 네비게이션 특화 손실

### Phase 3: 학습 레이어 변경 (2주차)  
1. **MultiScenarioTrainer**: 시나리오별 가중치 학습
2. **Mobile 평가 메트릭**: 네비게이션 성공률, 경로 효율성
3. **ROS 통합**: 실시간 추론 및 액션 실행

---

이 상세한 변경 분석을 통해 RoboVLMs에서 Mobile VLA로의 전환에서 **무엇을 바꾸고, 무엇을 유지하며, 무엇을 전이할지** 명확한 로드맵을 제시했습니다. mobile_vla_data_collector.py의 실용적 데이터 수집 방식과 RoboVLMs의 강력한 VLM 학습 시스템을 효과적으로 결합할 수 있을 것입니다.

# 🤖 mobile_vla_data_collector.py 기준 RoboVLMs 통합 구상

## 🎯 통합 전략 개요

mobile_vla_data_collector.py를 **핵심 축**으로 하여 RoboVLMs의 강력한 학습 시스템을 Mobile VLA에 맞게 통합하는 계획입니다. 기존의 실용적인 데이터 수집 방식을 유지하면서 최신 VLM 학습 기술을 도입합니다.

---

## 🔄 통합 아키텍처 구조도

### 1단계: 데이터 브리지 시스템
```
mobile_vla_data_collector.py 출력
           ↓
    HDF5 Episodes Dataset
           ↓
   🔄 Data Conversion Bridge
           ↓
    RoboVLMs 학습 형식
```

### 2단계: 모델 적응 시스템  
```
    RoboVLMs VLM Backbone
           ↓
   🧠 Mobile Policy Head 교체
           ↓
    4D 액션 Mobile VLA 모델
```

### 3단계: 통합 학습 시스템
```
 Mobile VLA Dataset + Mobile VLA Model
           ↓
    🚀 Mobile-specific Training
           ↓
   ROS2 실시간 추론 시스템
```

---

## 📊 mobile_vla_data_collector.py 활용 극대화

### 🎯 현재 강점 분석
```python
# mobile_vla_data_collector.py의 핵심 강점들
strengths = {
    "실시간_데이터_수집": "키보드 제어로 즉시 데이터 생성",
    "시나리오_체계화": "8가지 컵 도달 시나리오 구조화",
    "이벤트_기반_수집": "start_action, stop_action, episode_start 타임스탬프",
    "진행률_모니터링": "시나리오별 목표 대비 진행률 실시간 확인",
    "HDF5_저장": "효율적인 대용량 데이터 저장",
    "ROS_통합": "실제 로봇과 시뮬레이션 모두 지원"
}
```

### 🚀 통합 후 확장된 기능
```python
# Mobile VLA 통합 후 추가될 기능들
enhanced_features = {
    "자동_학습_파이프라인": "데이터 수집 → 자동 학습 → 모델 업데이트",
    "실시간_성능_피드백": "수집 중 모델 성능 실시간 모니터링", 
    "적응적_데이터_수집": "모델 약점 영역 우선 수집",
    "다국어_명령_지원": "한국어/영어 네비게이션 명령",
    "연속_학습_시스템": "새로운 시나리오 추가 시 자동 적응"
}
```

---

## 🔧 구체적인 통합 구현 계획

### Phase 1: 데이터 변환 브리지 (Week 1)

#### 🔄 H5toCalvin Converter 구현
```python
# /home/soda/vla/Mobile_VLA/data/processors/h5_to_calvin_converter.py
class H5toCalvinConverter:
    def __init__(self, mobile_data_dir="/home/soda/vla/ROS_action/mobile_vla_dataset/"):
        self.mobile_data_dir = Path(mobile_data_dir)
        self.scenario_map = {
            "1box_vert_left": "왼쪽으로 돌아서 박스를 지나 컵까지 가세요",
            "1box_vert_right": "오른쪽으로 돌아서 박스를 지나 컵까지 가세요",
            "1box_hori_left": "왼쪽 경로로 박스를 피해 컵까지 가세요",
            "1box_hori_right": "오른쪽 경로로 박스를 피해 컵까지 가세요",
            "2box_vert_left": "두 박스 사이 왼쪽 경로로 컵까지 가세요",
            "2box_vert_right": "두 박스 사이 오른쪽 경로로 컵까지 가세요", 
            "2box_hori_left": "두 박스를 왼쪽으로 우회해서 컵까지 가세요",
            "2box_hori_right": "두 박스를 오른쪽으로 우회해서 컵까지 가세요"
        }
    
    def convert_h5_episode(self, h5_file_path):
        """mobile_vla_data_collector.py 출력 → Calvin 형식"""
        with h5py.File(h5_file_path, 'r') as f:
            # mobile_vla_data_collector.py 형식 읽기
            images = f['images'][:]                    # [T, H, W, 3]
            actions = f['actions'][:]                  # [T, 4] (linear_x, linear_y, angular_z, type?)
            action_event_types = f['action_event_types'][:]  # [T] 이벤트 타입
            
            # 에피소드명에서 시나리오 추출
            episode_name = f.attrs['episode_name']
            scenario = self.extract_scenario(episode_name)
            
            # Calvin 형식으로 변환
            calvin_episode = {
                "rgb": images,                         # [T, H, W, 3] ✅ 그대로 사용
                "action": self.convert_4d_to_calvin_action(actions),  # [T, 7] 형식으로 변환
                "language": self.scenario_map[scenario],              # 한국어 명령
                "scenario_id": scenario,                             # 🆕 시나리오 메타데이터
                "action_events": action_event_types                   # 🆕 이벤트 타입 정보
            }
            
        return calvin_episode
    
    def convert_4d_to_calvin_action(self, mobile_actions):
        """4D Mobile 액션 → 7D Calvin 호환 액션"""
        # [linear_x, linear_y, angular_z, type] → [x, y, z, roll, pitch, yaw, gripper]
        T = mobile_actions.shape[0]
        calvin_actions = np.zeros((T, 7))
        
        # Mobile 액션을 Calvin 형식에 매핑
        calvin_actions[:, 0] = mobile_actions[:, 0]  # linear_x → x translation
        calvin_actions[:, 1] = mobile_actions[:, 1]  # linear_y → y translation  
        calvin_actions[:, 2] = 0.0                   # z translation (고정)
        calvin_actions[:, 3] = 0.0                   # roll (고정)
        calvin_actions[:, 4] = 0.0                   # pitch (고정)
        calvin_actions[:, 5] = mobile_actions[:, 2]  # angular_z → yaw rotation
        calvin_actions[:, 6] = mobile_actions[:, 3]  # action_type → gripper (재해석)
        
        return calvin_actions
```

#### 🎮 ActionSpace Adapter 구현
```python
# /home/soda/vla/Mobile_VLA/models/encoders/mobile_action_encoder.py
class MobileActionEncoder:
    def __init__(self):
        # mobile_vla_data_collector.py의 WASD_TO_CONTINUOUS 기준
        self.action_bounds = {
            "linear_x": [-2.0, 2.0],     # WASD_TO_CONTINUOUS에서 최대 1.15 사용
            "linear_y": [-2.0, 2.0],     # 여유있게 2.0으로 설정
            "angular_z": [-3.14, 3.14],  # 최대 1.15 사용, 2π까지 확장
        }
        self.action_types = {
            0: "move",      # 이동 액션
            1: "rotate",    # 회전 액션
            2: "stop",      # 정지 액션
            3: "special"    # 특수 액션 (미래 확장용)
        }
    
    def encode_mobile_action(self, mobile_action):
        """4D Mobile 액션을 VLM 이해 가능한 형태로 인코딩"""
        linear_x, linear_y, angular_z, action_type = mobile_action
        
        # 연속 액션 정규화 (-1 ~ 1)
        norm_linear_x = self.normalize_action(linear_x, self.action_bounds["linear_x"])
        norm_linear_y = self.normalize_action(linear_y, self.action_bounds["linear_y"])
        norm_angular_z = self.normalize_action(angular_z, self.action_bounds["angular_z"])
        
        # 액션 타입 원핫 인코딩
        action_type_onehot = np.zeros(4)
        action_type_onehot[int(action_type)] = 1.0
        
        return {
            "continuous": np.array([norm_linear_x, norm_linear_y, norm_angular_z]),
            "discrete": action_type_onehot,
            "raw": mobile_action
        }
```

### Phase 2: 모델 적응 (Week 2)

#### 🧠 Mobile-adapted Policy Head
```python
# /home/soda/vla/Mobile_VLA/models/policy_heads/mobile_policy_head.py
class MobilePolicyHead(nn.Module):
    def __init__(self, hidden_size=1024, dropout=0.1):
        super().__init__()
        # mobile_vla_data_collector.py의 4D 액션에 특화
        
        # 연속 액션 예측 (linear_x, linear_y, angular_z)
        self.movement_head = nn.Sequential(
            nn.Linear(hidden_size, 512),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 3),  # [linear_x, linear_y, angular_z]
            nn.Tanh()  # -1 ~ 1 범위로 정규화
        )
        
        # 액션 타입 분류 (이동/회전/정지/특수)
        self.action_type_head = nn.Sequential(
            nn.Linear(hidden_size, 512),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 4)   # [move, rotate, stop, special]
        )
        
        # 시나리오 컨텍스트 융합
        self.scenario_fusion = nn.MultiheadAttention(
            embed_dim=hidden_size, 
            num_heads=8,
            dropout=dropout
        )
        
    def forward(self, vlm_features, scenario_embedding=None):
        # 시나리오 컨텍스트가 있으면 융합
        if scenario_embedding is not None:
            fused_features, _ = self.scenario_fusion(
                vlm_features, scenario_embedding, scenario_embedding
            )
        else:
            fused_features = vlm_features
            
        # 4D 액션 예측
        movement_actions = self.movement_head(fused_features)      # [3] 연속
        action_type_logits = self.action_type_head(fused_features) # [4] 이산
        
        return {
            "movement": movement_actions,
            "action_type": action_type_logits,
            "movement_raw": self.denormalize_movement(movement_actions),
            "action_type_pred": torch.argmax(action_type_logits, dim=-1)
        }
    
    def denormalize_movement(self, normalized_actions):
        """정규화된 액션을 실제 mobile_vla_data_collector 범위로 변환"""
        # Tanh 출력 (-1~1)을 실제 액션 범위로 변환
        linear_x = normalized_actions[..., 0] * 2.0   # [-2.0, 2.0]
        linear_y = normalized_actions[..., 1] * 2.0   # [-2.0, 2.0]  
        angular_z = normalized_actions[..., 2] * 3.14 # [-π, π]
        
        return torch.stack([linear_x, linear_y, angular_z], dim=-1)
```

#### 🎯 Scenario-Aware VLM Backbone
```python
# /home/soda/vla/Mobile_VLA/models/backbones/mobile_paligemma.py
class MobilePaliGemma(nn.Module):
    def __init__(self, configs):
        super().__init__()
        # 기존 PaliGemma 백본 로드 (✅ 유지)
        self.paligemma = self.load_pretrained_paligemma(configs)
        
        # 시나리오 인코더 추가 (🆕 Mobile VLA 특화)
        self.scenario_encoder = nn.Embedding(8, self.paligemma.config.hidden_size)
        
        # Mobile Policy Head로 교체 (🔄 변경)
        self.policy_head = MobilePolicyHead(
            hidden_size=self.paligemma.config.hidden_size,
            dropout=configs.get("dropout", 0.1)
        )
        
        # 시나리오 매핑
        self.scenario_to_id = {
            "1box_vert_left": 0,   "1box_vert_right": 1,
            "1box_hori_left": 2,   "1box_hori_right": 3,
            "2box_vert_left": 4,   "2box_vert_right": 5,
            "2box_hori_left": 6,   "2box_hori_right": 7
        }
    
    def forward(self, images, instructions, scenarios=None):
        # 기존 PaliGemma 시각-언어 인코딩 (✅ 유지)
        vlm_output = self.paligemma(
            pixel_values=images,
            input_ids=instructions["input_ids"],
            attention_mask=instructions["attention_mask"]
        )
        
        # VLM 특징 추출
        vlm_features = vlm_output.last_hidden_state.mean(dim=1)  # [B, hidden_size]
        
        # 시나리오 컨텍스트 추가 (🆕 Mobile VLA 특화)
        scenario_embedding = None
        if scenarios is not None:
            scenario_ids = torch.tensor([
                self.scenario_to_id[scenario] for scenario in scenarios
            ]).to(vlm_features.device)
            scenario_embedding = self.scenario_encoder(scenario_ids)
        
        # Mobile 액션 예측 (🔄 변경)
        action_output = self.policy_head(vlm_features, scenario_embedding)
        
        return action_output
```

### Phase 3: 통합 학습 시스템 (Week 3)

#### 📚 Mobile-specific Trainer
```python
# /home/soda/vla/Mobile_VLA/training/trainers/mobile_base_trainer.py
class MobileBaseTrainer(BaseTrainer):
    def __init__(self, configs):
        super().__init__(configs)
        
        # mobile_vla_data_collector.py 시나리오별 가중치
        self.scenario_weights = {
            "1box_vert_left": 1.0,    # 기본 난이도
            "1box_vert_right": 1.0,   # 기본 난이도
            "1box_hori_left": 1.2,    # 중간 난이도
            "1box_hori_right": 1.1,   # 중간 난이도
            "2box_vert_left": 1.5,    # 고급 난이도
            "2box_vert_right": 1.4,   # 고급 난이도
            "2box_hori_left": 1.8,    # 최고 난이도
            "2box_hori_right": 1.6    # 최고 난이도
        }
        
        # Mobile 특화 손실 함수 가중치
        self.movement_loss_weight = 1.0
        self.action_type_loss_weight = 0.5
        self.scenario_consistency_weight = 0.1
        
    def _get_mobile_loss(self, prediction, target, scenario):
        """Mobile VLA 특화 손실 함수"""
        # 연속 액션 손실 (movement)
        movement_loss = F.mse_loss(
            prediction["movement"], 
            target["movement"]
        )
        
        # 액션 타입 분류 손실
        action_type_loss = F.cross_entropy(
            prediction["action_type"], 
            target["action_type"]
        )
        
        # 시나리오 일관성 손실 (같은 시나리오에서 일관된 행동 유도)
        scenario_consistency_loss = self.compute_scenario_consistency_loss(
            prediction, scenario
        )
        
        # 시나리오별 가중치 적용
        scenario_weight = self.scenario_weights.get(scenario, 1.0)
        
        total_loss = (
            self.movement_loss_weight * movement_loss +
            self.action_type_loss_weight * action_type_loss +
            self.scenario_consistency_weight * scenario_consistency_loss
        ) * scenario_weight
        
        return {
            "total_loss": total_loss,
            "movement_loss": movement_loss,
            "action_type_loss": action_type_loss,
            "scenario_consistency_loss": scenario_consistency_loss,
            "scenario_weight": scenario_weight
        }
    
    def training_step(self, batch, batch_idx):
        """mobile_vla_data_collector.py 데이터 기반 학습"""
        # 배치에서 Mobile VLA 데이터 추출
        images = batch["images"]          # [B, T, H, W, 3]
        actions = batch["actions"]        # [B, T, 4]
        scenarios = batch["scenarios"]    # [B] scenario names
        instructions = batch["instructions"]  # [B] tokenized Korean instructions
        
        # 모델 포워드
        predictions = self.model(images, instructions, scenarios)
        
        # 타겟 액션 분리
        target_movement = actions[..., :3]    # [linear_x, linear_y, angular_z]
        target_action_type = actions[..., 3].long()  # action_type
        
        targets = {
            "movement": target_movement,
            "action_type": target_action_type
        }
        
        # 시나리오별 손실 계산
        batch_losses = []
        for i, scenario in enumerate(scenarios):
            pred_i = {k: v[i] for k, v in predictions.items()}
            target_i = {k: v[i] for k, v in targets.items()}
            loss_i = self._get_mobile_loss(pred_i, target_i, scenario)
            batch_losses.append(loss_i["total_loss"])
        
        total_loss = torch.stack(batch_losses).mean()
        
        # 로깅
        self.log_dict({
            "train_total_loss": total_loss,
            "train_movement_loss": movement_loss,
            "train_action_type_loss": action_type_loss,
        }, prog_bar=True)
        
        return total_loss
```

### Phase 4: ROS2 실시간 통합 (Week 4)

#### 🚀 Real-time Inference Engine
```python
# /home/soda/vla/Mobile_VLA/inference/engines/mobile_inference_engine.py
class MobileInferenceEngine:
    def __init__(self, model_path, configs):
        # 학습된 Mobile VLA 모델 로드
        self.model = MobilePaliGemma.load_from_checkpoint(model_path)
        self.model.eval()
        
        # mobile_vla_data_collector.py와 호환되는 액션 포맷터
        self.action_formatter = MobileActionFormatter()
        
        # ROS2 퍼블리셔 (기존 mobile_vla_data_collector.py와 동일)
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
    def predict_action(self, current_image, instruction, scenario):
        """실시간 액션 예측"""
        with torch.no_grad():
            # 이미지 전처리
            processed_image = self.preprocess_image(current_image)
            
            # 명령어 토크나이징
            tokenized_instruction = self.tokenize_instruction(instruction)
            
            # 모델 추론
            prediction = self.model(
                images=processed_image.unsqueeze(0),
                instructions=tokenized_instruction,
                scenarios=[scenario]
            )
            
            # Mobile VLA 액션을 mobile_vla_data_collector 형식으로 변환
            mobile_action = self.action_formatter.format_for_mobile_vla(prediction)
            
        return mobile_action
    
    def execute_action(self, mobile_action):
        """mobile_vla_data_collector.py와 동일한 방식으로 액션 실행"""
        # mobile_vla_data_collector.py의 publish_cmd_vel 메서드와 호환
        twist = Twist()
        twist.linear.x = float(mobile_action["linear_x"])
        twist.linear.y = float(mobile_action["linear_y"])
        twist.angular.z = float(mobile_action["angular_z"])
        
        self.cmd_pub.publish(twist)
        
        # 실제 로봇 제어 (mobile_vla_data_collector.py와 동일)
        if self.driver and ROBOT_AVAILABLE:
            self.control_physical_robot(mobile_action)
```

---

## 📈 통합 후 예상 성능 개선

### 1. **데이터 효율성** 
- **현재**: 수동 WASD 제어로 데이터 수집
- **통합 후**: 학습된 모델이 데이터 부족 영역 자동 식별 → 능동적 데이터 수집

### 2. **학습 속도**
- **현재**: 데이터 수집과 학습이 분리된 프로세스
- **통합 후**: 데이터 수집 → 즉시 학습 → 모델 개선 → 더 나은 데이터 수집 (선순환)

### 3. **실시간 성능**
- **현재**: 키보드 제어 기반 반응형 조작
- **통합 후**: VLM 기반 지능형 네비게이션 + 기존 안전성 유지

### 4. **확장성**
- **현재**: 8가지 고정 시나리오
- **통합 후**: 새로운 시나리오 자동 학습 + 기존 시나리오 성능 향상

---

## 🎯 구현 마일스톤

### Week 1: 데이터 브리지 구축
- [x] H5toCalvin Converter 구현
- [x] ActionSpace Adapter 구현  
- [x] 기본 변환 파이프라인 테스트

### Week 2: 모델 적응
- [ ] MobilePolicyHead 구현
- [ ] MobilePaliGemma 구현
- [ ] 액션 공간 변환 테스트

### Week 3: 학습 시스템 통합
- [ ] MobileBaseTrainer 구현
- [ ] 시나리오별 학습 테스트
- [ ] 손실 함수 최적화

### Week 4: ROS2 실시간 통합
- [ ] MobileInferenceEngine 구현
- [ ] mobile_vla_data_collector.py와 연동
- [ ] 실시간 성능 테스트

---

## 🏁 최종 통합 비전

이 통합 계획을 통해 **mobile_vla_data_collector.py의 실용성**과 **RoboVLMs의 학습 기술력**을 결합하여, 실제 환경에서 즉시 사용 가능한 **Mobile VLA 시스템**을 구축할 수 있습니다. 

기존의 **8가지 컵 도달 시나리오** 데이터를 활용하여 강력한 **시각-언어-네비게이션** 모델을 학습하고, 이를 다시 **mobile_vla_data_collector.py**를 통해 실시간으로 검증하고 개선하는 **선순환 시스템**이 완성됩니다.

**Robo-Mobile VLA 논문**의 핵심 기여도는 이러한 **실용적 통합 접근법**과 **실시간 성능 검증**이 될 것입니다.

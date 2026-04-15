# 🚀 Pure Mobile VLA System (Calvin 없는 순수 Mobile 네이티브 시스템)

## 🎯 기본 철학: mobile_vla_data_collector.py 100% 활용

Calvin 형식은 완전히 버리고, mobile_vla_data_collector.py가 생성하는 **순수 Mobile 데이터 형식**을 직접 활용하는 VLM 학습 시스템을 구축합니다.

---

## 📊 실제 Mobile 데이터 구조 (확인된 형식)

### 🔍 HDF5 파일 구조 분석 결과
```python
# 실제 mobile_vla_data_collector.py 출력 (70개 파일 확인)
mobile_data_structure = {
    "images": {
        "shape": "(18, 720, 1280, 3)",  # 18프레임, 720p 해상도
        "dtype": "uint8",
        "description": "RGB 카메라 이미지 시퀀스"
    },
    "actions": {
        "shape": "(18, 3)",              # 3D 액션 (4D가 아님!)
        "dtype": "float32", 
        "content": "[linear_x, linear_y, angular_z]",
        "sample": "[[0.0, 0.0, 0.0], [1.15, 0.0, 0.0], [1.15, 0.0, 0.0]]"
    },
    "action_event_types": {
        "shape": "(18,)",
        "dtype": "object (bytes)",
        "content": "['episode_start', 'start_action', 'start_action', ...]"
    },
    "metadata": {
        "episode_name": "episode_20250808_123136_1box_vert_left",
        "action_chunk_size": 8,
        "num_frames": 18,
        "total_duration": 18.87,
        "scenario": "1box_vert_left"  # 에피소드명에서 추출 가능
    }
}
```

### 🔥 핵심 발견사항
1. **액션이 3D임!** (4D가 아니라 linear_x, linear_y, angular_z만 있음)
2. **18프레임이 표준** (프레임 18개 데이터의 중요성 확인)
3. **720p 고해상도** (1280x720, 기존 224x224보다 훨씬 높음)
4. **이벤트 기반 타임스탬프** (episode_start, start_action, stop_action)

---

## 🧠 Pure Mobile VLM 아키텍처 설계

### 1. 📸 Native Mobile Image Encoder
```python
# /home/soda/vla/Mobile_VLA/models/encoders/mobile_image_encoder.py
class MobileImageEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        # mobile_vla_data_collector.py의 실제 해상도 처리
        self.input_size = (720, 1280, 3)  # ✅ 실제 데이터 해상도
        
        # 고해상도 처리를 위한 효율적 CNN
        self.backbone = torchvision.models.efficientnet_v2_s(pretrained=True)
        self.backbone.features[0][0] = nn.Conv2d(3, 24, kernel_size=3, stride=2, padding=1)
        
        # 시간적 특징 추출 (18프레임 시퀀스)
        self.temporal_encoder = nn.LSTM(
            input_size=1000,  # EfficientNet output
            hidden_size=512,
            num_layers=2,
            batch_first=True,
            bidirectional=True
        )
        
    def forward(self, image_sequence):
        # image_sequence: [B, 18, 720, 1280, 3]
        B, T, H, W, C = image_sequence.shape
        
        # 배치 차원으로 펼치기
        images_flat = image_sequence.view(B * T, C, H, W)
        
        # 각 프레임 특징 추출
        frame_features = self.backbone(images_flat)  # [B*T, 1000]
        frame_features = frame_features.view(B, T, -1)  # [B, T, 1000]
        
        # 시간적 특징 추출
        temporal_features, _ = self.temporal_encoder(frame_features)
        
        return temporal_features  # [B, T, 1024]
```

### 2. 🗣️ Korean Instruction Encoder  
```python
# /home/soda/vla/Mobile_VLA/models/encoders/korean_text_encoder.py
class KoreanInstructionEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        # 한국어 특화 텍스트 인코더
        self.tokenizer = AutoTokenizer.from_pretrained("klue/roberta-base")
        self.text_encoder = AutoModel.from_pretrained("klue/roberta-base")
        
        # 시나리오별 한국어 명령어 템플릿
        self.scenario_instructions = {
            "1box_vert_left": "가장 왼쪽 외곽으로 돌아 컵까지 가세요",
            "1box_vert_right": "가장 오른쪽 외곽으로 돌아 컵까지 가세요", 
            "1box_hori_left": "가장 왼쪽 외곽으로 돌아 컵까지 가세요",
            "1box_hori_right": "가장 오른쪽 외곽으로 돌아 컵까지 가세요",
            "2box_vert_left": "가장 왼쪽 외곽으로 돌아 컵까지 가세요",
            "2box_vert_right": "가장 오른쪽 외곽으로 돌아 컵까지 가세요",
            "2box_hori_left": "가장 왼쪽 외곽으로 돌아 컵까지 가세요", 
            "2box_hori_right": "가장 오른쪽 외곽으로 돌아 컵까지 가세요"
        }
        
    def forward(self, scenario_names):
        # 시나리오명에서 한국어 명령어 생성
        instructions = [self.scenario_instructions[scenario] for scenario in scenario_names]
        
        # 토크나이징
        tokenized = self.tokenizer(
            instructions, 
            padding=True, 
            truncation=True, 
            return_tensors="pt"
        )
        
        # 텍스트 인코딩
        text_features = self.text_encoder(**tokenized)
        
        return text_features.last_hidden_state  # [B, seq_len, 768]
```

### 3. 🎯 Mobile Action Predictor (3D 액션)
```python
# /home/soda/vla/Mobile_VLA/models/policy_heads/mobile_action_predictor.py
class MobileActionPredictor(nn.Module):
    def __init__(self, visual_dim=1024, text_dim=768):
        super().__init__()
        
        # mobile_vla_data_collector.py의 실제 3D 액션에 맞춤
        self.action_dim = 3  # [linear_x, linear_y, angular_z]
        
        # 멀티모달 융합
        self.fusion = nn.MultiheadAttention(
            embed_dim=visual_dim + text_dim,
            num_heads=8,
            dropout=0.1
        )
        
        # 3D 액션 예측 헤드 (mobile_vla_data_collector.py WASD_TO_CONTINUOUS 기준)
        self.action_head = nn.Sequential(
            nn.Linear(visual_dim + text_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 3),  # [linear_x, linear_y, angular_z]
        )
        
        # 이벤트 타입 예측 (start_action, stop_action 예측)
        self.event_head = nn.Sequential(
            nn.Linear(visual_dim + text_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 3)  # [episode_start, start_action, stop_action]
        )
        
        # mobile_vla_data_collector.py의 액션 범위
        self.action_bounds = {
            "linear_x": 2.0,    # ±2.0 (실제로는 ±1.15 사용)
            "linear_y": 2.0,    # ±2.0 (실제로는 ±1.15 사용)  
            "angular_z": 2.0    # ±2.0 (실제로는 ±1.15 사용)
        }
        
    def forward(self, visual_features, text_features):
        # visual_features: [B, T, 1024]
        # text_features: [B, seq_len, 768]
        
        B, T = visual_features.shape[:2]
        
        # 텍스트 특징 평균화
        text_pooled = text_features.mean(dim=1)  # [B, 768]
        text_expanded = text_pooled.unsqueeze(1).repeat(1, T, 1)  # [B, T, 768]
        
        # 시각-텍스트 융합
        fused_features = torch.cat([visual_features, text_expanded], dim=-1)  # [B, T, 1792]
        
        # Attention 융합
        fused_attended, _ = self.fusion(fused_features, fused_features, fused_features)
        
        # 액션 예측 (mobile_vla_data_collector.py 형식)
        raw_actions = self.action_head(fused_attended)  # [B, T, 3]
        
        # 실제 액션 범위로 스케일링
        actions = torch.tanh(raw_actions) * 2.0  # [-2.0, 2.0] 범위
        
        # 이벤트 타입 예측
        event_logits = self.event_head(fused_attended)  # [B, T, 3]
        
        return {
            "actions": actions,                    # [B, T, 3] - mobile 형식
            "event_logits": event_logits,         # [B, T, 3] - 이벤트 예측
            "action_events": torch.argmax(event_logits, dim=-1)  # [B, T] - 예측된 이벤트
        }
```

---

## 📦 Pure Mobile Dataset Loader

### 🔥 Calvin 없는 순수 Mobile Dataset
```python
# /home/soda/vla/Mobile_VLA/data/mobile_native_dataset.py
class MobileVLADataset(Dataset):
    def __init__(self, data_dir="/home/soda/vla/ROS_action/mobile_vla_dataset/"):
        self.data_dir = Path(data_dir)
        self.h5_files = list(self.data_dir.glob("*.h5"))
        
        print(f"📁 {len(self.h5_files)}개의 Mobile VLA 에피소드 로드됨")
        
        # 시나리오 추출 및 통계
        self.scenarios = []
        self.scenario_stats = defaultdict(int)
        
        for h5_file in self.h5_files:
            scenario = self.extract_scenario_from_filename(h5_file.name)
            self.scenarios.append(scenario)
            self.scenario_stats[scenario] += 1
            
        print(f"🎯 시나리오 분포: {dict(self.scenario_stats)}")
        
    def extract_scenario_from_filename(self, filename):
        """파일명에서 시나리오 추출 (mobile_vla_data_collector.py 방식)"""
        for scenario in ["1box_vert_left", "1box_vert_right", "1box_hori_left", "1box_hori_right",
                        "2box_vert_left", "2box_vert_right", "2box_hori_left", "2box_hori_right"]:
            if scenario in filename:
                return scenario
        return "unknown"
    
    def __len__(self):
        return len(self.h5_files)
    
    def __getitem__(self, idx):
        h5_file = self.h5_files[idx]
        scenario = self.scenarios[idx]
        
        with h5py.File(h5_file, 'r') as f:
            # mobile_vla_data_collector.py 데이터 직접 로드
            images = f['images'][:]                    # [18, 720, 1280, 3]
            actions = f['actions'][:]                  # [18, 3]
            action_events = f['action_event_types'][:]  # [18]
            
            # 메타데이터
            episode_name = f.attrs['episode_name']
            num_frames = f.attrs['num_frames']
            duration = f.attrs['total_duration']
            
        # 이벤트 타입을 정수로 변환
        event_mapping = {
            b'episode_start': 0,
            b'start_action': 1, 
            b'stop_action': 2
        }
        event_indices = np.array([event_mapping.get(event, 1) for event in action_events])
        
        return {
            "images": torch.FloatTensor(images) / 255.0,     # [18, 720, 1280, 3] 정규화
            "actions": torch.FloatTensor(actions),           # [18, 3]  
            "action_events": torch.LongTensor(event_indices), # [18]
            "scenario": scenario,                            # str
            "episode_name": episode_name,                    # str
            "num_frames": num_frames,                        # int
            "duration": duration                             # float
        }
```

---

## 🏋️ Pure Mobile Trainer

### 📈 Calvin 없는 순수 Mobile 학습
```python
# /home/soda/vla/Mobile_VLA/training/mobile_native_trainer.py
class MobileVLATrainer(pl.LightningModule):
    def __init__(self, configs):
        super().__init__()
        
        # Pure Mobile VLM 구성요소
        self.image_encoder = MobileImageEncoder()
        self.text_encoder = KoreanInstructionEncoder() 
        self.action_predictor = MobileActionPredictor()
        
        # mobile_vla_data_collector.py 시나리오별 가중치
        self.scenario_weights = {
            "1box_vert_left": 1.0,
            "1box_vert_right": 1.0,
            "1box_hori_left": 1.2,   # 더 어려운 시나리오
            "1box_hori_right": 1.1,
            "2box_vert_left": 1.5,   # 가장 어려운 시나리오
            "2box_vert_right": 1.4,
            "2box_hori_left": 1.8,
            "2box_hori_right": 1.6
        }
        
        # 손실 함수 가중치
        self.action_loss_weight = 1.0
        self.event_loss_weight = 0.5
        
    def forward(self, batch):
        images = batch["images"]      # [B, 18, 720, 1280, 3]
        scenarios = batch["scenario"] # [B] list of scenario names
        
        # 인코딩
        visual_features = self.image_encoder(images)        # [B, 18, 1024]
        text_features = self.text_encoder(scenarios)        # [B, seq_len, 768]
        
        # 액션 예측
        predictions = self.action_predictor(visual_features, text_features)
        
        return predictions
    
    def training_step(self, batch, batch_idx):
        # 포워드 패스
        predictions = self.forward(batch)
        
        # 타겟 데이터
        target_actions = batch["actions"]          # [B, 18, 3]
        target_events = batch["action_events"]     # [B, 18]
        scenarios = batch["scenario"]
        
        # 손실 계산
        action_loss = F.mse_loss(predictions["actions"], target_actions)
        event_loss = F.cross_entropy(
            predictions["event_logits"].view(-1, 3), 
            target_events.view(-1)
        )
        
        # 시나리오별 가중치 적용
        scenario_weights = torch.tensor([
            self.scenario_weights.get(scenario, 1.0) for scenario in scenarios
        ]).to(self.device)
        
        weighted_action_loss = (action_loss * scenario_weights.mean())
        weighted_event_loss = (event_loss * scenario_weights.mean())
        
        total_loss = (
            self.action_loss_weight * weighted_action_loss + 
            self.event_loss_weight * weighted_event_loss
        )
        
        # 로깅
        self.log_dict({
            "train_total_loss": total_loss,
            "train_action_loss": weighted_action_loss,
            "train_event_loss": weighted_event_loss,
            "train_action_accuracy": self.compute_action_accuracy(predictions["actions"], target_actions),
            "train_event_accuracy": self.compute_event_accuracy(predictions["action_events"], target_events)
        }, prog_bar=True)
        
        return total_loss
    
    def compute_action_accuracy(self, pred_actions, target_actions):
        """액션 정확도 계산 (mobile_vla_data_collector.py 기준)"""
        # 각 축별 오차가 0.1 이내면 정확한 것으로 간주
        action_diff = torch.abs(pred_actions - target_actions)
        accurate_actions = (action_diff < 0.1).all(dim=-1)  # [B, T]
        return accurate_actions.float().mean()
    
    def compute_event_accuracy(self, pred_events, target_events):
        """이벤트 타입 예측 정확도"""
        return (pred_events == target_events).float().mean()
    
    def configure_optimizers(self):
        optimizer = torch.optim.AdamW(self.parameters(), lr=1e-4, weight_decay=0.01)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100)
        return {"optimizer": optimizer, "lr_scheduler": scheduler}
```

---

## 🚀 실시간 Mobile VLA Inference

### 🎯 mobile_vla_data_collector.py와 완전 호환
```python
# /home/soda/vla/Mobile_VLA/inference/mobile_real_time_inference.py
class MobileVLAInference:
    def __init__(self, model_checkpoint_path):
        # 학습된 Pure Mobile VLA 모델 로드
        self.model = MobileVLATrainer.load_from_checkpoint(model_checkpoint_path)
        self.model.eval()
        
        # mobile_vla_data_collector.py와 동일한 액션 형식
        self.action_converter = MobileActionConverter()
        
    def predict_next_action(self, current_image, scenario):
        """
        실시간 액션 예측 (mobile_vla_data_collector.py 호환)
        
        Args:
            current_image: numpy array [720, 1280, 3]
            scenario: str (e.g., "1box_hori_left")
            
        Returns:
            mobile_action: dict compatible with mobile_vla_data_collector.py
        """
        with torch.no_grad():
            # 단일 이미지를 18프레임 시퀀스로 확장 (최신 이미지 반복)
            image_sequence = np.tile(current_image[None, ...], (18, 1, 1, 1))  # [18, 720, 1280, 3]
            image_tensor = torch.FloatTensor(image_sequence).unsqueeze(0) / 255.0  # [1, 18, 720, 1280, 3]
            
            # 배치 생성
            batch = {
                "images": image_tensor,
                "scenario": [scenario]
            }
            
            # 예측
            predictions = self.model.forward(batch)
            
            # 마지막 프레임의 액션 사용
            predicted_action = predictions["actions"][0, -1].cpu().numpy()  # [3]
            predicted_event = predictions["action_events"][0, -1].cpu().item()
            
            # mobile_vla_data_collector.py 형식으로 변환
            mobile_action = {
                "linear_x": float(predicted_action[0]),
                "linear_y": float(predicted_action[1]), 
                "angular_z": float(predicted_action[2]),
                "event_type": ["episode_start", "start_action", "stop_action"][predicted_event]
            }
            
        return mobile_action
    
    def integrate_with_data_collector(self, data_collector):
        """mobile_vla_data_collector.py와 통합"""
        # 기존 키보드 제어 대신 VLA 예측 사용
        def vla_action_callback():
            if data_collector.collecting:
                # 현재 이미지 가져오기
                current_image = data_collector.get_latest_image_via_service()
                if current_image is not None:
                    # 현재 시나리오 추출
                    scenario = data_collector.extract_scenario_from_episode_name(
                        data_collector.episode_name
                    )
                    
                    if scenario:
                        # VLA 액션 예측
                        predicted_action = self.predict_next_action(current_image, scenario)
                        
                        # mobile_vla_data_collector.py 액션 실행
                        data_collector.publish_cmd_vel(predicted_action)
                        data_collector.collect_data_point_with_action(
                            "vla_predicted_action", predicted_action, current_image
                        )
        
        return vla_action_callback
```

---

## 🎯 핵심 장점: Pure Mobile 시스템

### ✅ Calvin 제거의 이점
1. **데이터 변환 불필요**: HDF5 → 직접 학습
2. **네이티브 해상도**: 720p 고화질 그대로 활용  
3. **실제 액션 공간**: 3D 모바일 액션 직접 학습
4. **이벤트 기반 학습**: start/stop 타이밍 학습 가능
5. **시나리오 네이티브**: 8가지 시나리오 직접 인식

### 🚀 구현 우선순위
1. **Week 1**: MobileVLADataset + 기본 데이터 로딩
2. **Week 2**: Pure Mobile VLM 모델 구현  
3. **Week 3**: MobileVLATrainer + 학습 파이프라인
4. **Week 4**: 실시간 추론 + mobile_vla_data_collector 통합

이제 Calvin 형식에 의존하지 않고 **mobile_vla_data_collector.py의 순수한 데이터 형식**을 100% 활용하는 VLA 시스템이 완성됩니다! 🎉

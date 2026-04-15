# RoboVLMs 상세 분석 리포트

## 📁 프로젝트 구조 개요

RoboVLMs는 Vision-Language-Action (VLA) 모델을 위한 종합적인 프레임워크로, 로봇 제어를 위한 멀티모달 AI 시스템을 구현합니다.

```
RoboVLMs/
├── configs/                    # 설정 및 구성 파인튜닝 설정
│   ├── calvin_finetune/       # CALVIN 데이터셋 파인튜닝 설정
│   ├── data/                  # 데이터 관련 설정
│   └── oxe_training/          # Open-X Embodiment 훈련 설정
├── robovlms/                  # 메인 패키지
│   ├── data/                  # 데이터 처리 모듈
│   ├── model/                 # 모델 아키텍처
│   ├── train/                 # 훈련 시스템
│   └── utils/                 # 유틸리티 함수
├── vla_test/                  # VLA 테스트 및 액션 파싱
└── scripts/                   # 실행 스크립트
```

## 🎯 VLA에서 정책(Policy)의 개념과 구현

### 1. 정책(Policy)이란?

**정책(Policy)**은 VLA 시스템의 핵심 구성요소로, **"주어진 상황(비전+언어)에서 로봇이 어떤 행동을 취할지 결정하는 의사결정 함수"**입니다.

#### 수학적 정의
```python
π(action | vision, language, history) 
= 이미지, 언어 명령, 이전 행동 히스토리가 주어졌을 때 
  다음에 취할 최적의 액션을 선택하는 확률 분포
```

#### 정책의 역할
1. **인식**: 현재 상황 파악 (비전 + 언어 이해)
2. **추론**: 목표 달성을 위한 최적 행동 계획
3. **실행**: 구체적인 로봇 제어 명령 생성

### 2. RoboVLMs의 정책 아키텍처

#### 정책 시스템 구조
```python
class BaseRoboVLM(nn.Module):
    def _init_heads(self):
        # 정책 헤드 초기화
        action_head = self._build_policy_head()
        
    def forward(self, vision_x, lang_x, ...):
        # 1. 멀티모달 특징 융합
        fused_features = self.encode_multimodal(vision_x, lang_x)
        
        # 2. 정책 헤드를 통한 액션 예측
        predicted_actions = self.action_head(fused_features)
        
        return predicted_actions
```

#### 지원되는 정책 헤드 타입들 상세 분석

**1. FCDecoder (Fully Connected Policy) - 즉시 반응형 정책**

FCDecoder는 가장 기본적이고 직관적인 정책 헤드입니다.

```python
class FCDecoder(BasePolicyHead):
    def __init__(self, in_features, action_dim, fwd_pred_next_n, ...):
        # 완전연결층 기반 정책
        self.actions = MLPTanhHead(hidden_size, fwd_pred_next_n * (action_dim-1))  # 팔 제어
        self.gripper = MLPSigmoidHead(hidden_size, fwd_pred_next_n)               # 그리퍼 제어
        self.mlp = Sequential(
            Linear(in_features, in_features // 2),
            ReLU(),
            Linear(in_features // 2, hidden_size)
        )
        
    def forward(self, features):
        # 1. 특징 압축
        compressed_features = self.mlp(features)
        
        # 2. 팔 액션 예측 (6DOF: x,y,z,roll,pitch,yaw)
        arm_actions = self.actions(compressed_features)  # [-1, 1] 범위
        
        # 3. 그리퍼 액션 예측 (open/close)
        gripper_action = self.gripper(compressed_features)  # [0, 1] 확률
        
        return arm_actions, gripper_action
```

**특징:**
- ⚡ **빠른 추론**: 단일 패스로 즉시 액션 생성
- 🎯 **직관적**: 현재 상황만 고려하는 단순한 매핑
- 📏 **경량화**: 메모리 사용량 최소화
- ❌ **한계**: 시간적 맥락 부족, 복잡한 시퀀스 태스크 어려움

**적용 예시**: 컵 잡기, 물체 터치, 단순 이동

---

**2. LSTMDecoder (Sequential Policy) - 시퀀스 기반 정책**

LSTMDecoder는 시간적 의존성을 고려하여 순차적 행동을 모델링합니다.

```python
class LSTMDecoder(BasePolicyHead):
    def __init__(self, window_size=16, fwd_pred_next_n=2, hidden_size=1024, ...):
        # 시퀀스 기반 정책 (시간적 의존성 고려)
        self.window_size = window_size      # 히스토리 윈도우
        self.fwd_pred_next_n = fwd_pred_next_n  # 예측할 미래 스텝
        self.history_memory = []            # 히스토리 저장
        
        self.rnn = LSTM(
            input_size=in_features,
            hidden_size=hidden_size,
            num_layers=4,
            dropout=0.1
        )
        self.actions = MLPTanhHead(hidden_size, fwd_pred_next_n * (action_dim-1))
        self.gripper = MLPSigmoidHead(hidden_size, fwd_pred_next_n)
        
    def forward(self, feature_sequence):
        # 1. 히스토리 관리
        if feature_sequence.shape[1] == 1:  # 단일 스텝 입력
            self.history_memory.append(feature_sequence)
            if len(self.history_memory) > self.window_size:
                self.history_memory.pop(0)
            hist_features = torch.cat(self.history_memory, dim=1)
        else:  # 전체 시퀀스 입력
            hist_features = feature_sequence
            
        # 2. LSTM을 통한 시퀀스 처리
        lstm_output, (h_n, c_n) = self.rnn(hist_features)
        
        # 3. 마지막 출력으로 액션 예측
        final_output = lstm_output[:, -1, :]  # [batch, hidden_size]
        
        # 4. 미래 N스텝 액션 예측
        arm_actions = self.actions(final_output)      # [batch, N*6]
        gripper_actions = self.gripper(final_output)  # [batch, N]
        
        # 5. 차원 재구성
        arm_actions = arm_actions.view(batch_size, self.fwd_pred_next_n, 6)
        gripper_actions = gripper_actions.view(batch_size, self.fwd_pred_next_n, 1)
        
        return arm_actions, gripper_actions
```

**특징:**
- 🔄 **시간적 맥락**: 과거 행동을 기억하여 일관성 있는 액션 생성
- 📈 **순차적 학습**: 점진적으로 복잡한 태스크 수행 가능
- 🎯 **미래 예측**: 다음 N스텝의 액션을 한 번에 예측
- ❌ **한계**: 장기 의존성 문제, 그래디언트 소실

**적용 예시**: 물 따르기, 문 열기, 연속적인 조작 태스크

---

**3. GPTDecoder (Transformer Policy) - 어텐션 기반 정책**

GPTDecoder는 트랜스포머의 어텐션 메커니즘을 활용한 고급 정책입니다.

```python
class GPTDecoder(BasePolicyHead):
    def __init__(self, window_size=16, hidden_size=1024, ...):
        from robovlms.model.policy_head.trajectory_gpt2 import get_gpt_model
        
        # GPT 스타일 트랜스포머 정책
        self.gpt = get_gpt_model(
            input_dim=hidden_size,
            window_size=window_size,
            n_layer=8,
            n_head=8
        )
        self.fc = Linear(in_features, hidden_size)  # 입력 차원 조정
        self.actions = MLPTanhHead(hidden_size, fwd_pred_next_n * (action_dim-1))
        self.gripper = MLPSigmoidHead(hidden_size, fwd_pred_next_n)
        self.history_memory = []
        
    def forward(self, feature_sequence):
        # 1. 특징 압축
        features = self.fc(feature_sequence)  # [batch, seq_len, hidden_size]
        
        # 2. 히스토리 관리 (추론 시)
        if features.shape[1] == 1:
            self.history_memory.append(features)
            if len(self.history_memory) > self.window_size:
                self.history_memory.pop(0)
            hist_features = torch.cat(self.history_memory, dim=1)
        else:
            hist_features = features
            
        # 3. GPT 트랜스포머를 통한 처리
        # - 셀프 어텐션으로 중요한 과거 정보에 집중
        # - 위치 인코딩으로 시간 순서 고려
        transformer_output = self.gpt(hist_features)  # [batch, seq_len, hidden_size]
        
        # 4. 마지막 토큰으로 액션 예측
        final_output = transformer_output[:, -1, :]
        
        # 5. 액션 디코딩
        arm_actions = self.actions(final_output)
        gripper_actions = self.gripper(final_output)
        
        return arm_actions.view(-1, self.fwd_pred_next_n, 6), \
               gripper_actions.view(-1, self.fwd_pred_next_n, 1)
```

**특징:**
- 🧠 **강력한 모델링**: 어텐션으로 중요 정보에 선택적 집중
- 🔗 **장기 의존성**: LSTM보다 긴 시퀀스 처리 가능
- 🎯 **병렬 처리**: 시퀀스 전체를 동시에 처리
- ❌ **한계**: 높은 계산 비용, 메모리 사용량 증가

**적용 예시**: 복잡한 조립 작업, 멀티스텝 요리, 장기 계획이 필요한 태스크

---

**4. DiscreteDecoder (Discrete Action Policy) - 토큰 기반 정책**

DiscreteDecoder는 연속 액션을 이산 토큰으로 변환하여 언어모델처럼 처리합니다.

```python
class DiscreteDecoder(BasePolicyHead):
    def __init__(self, tokenizer, n_bin=256, min_action=-1, max_action=1, ...):
        # 이산적 액션 공간 정책
        self.action_tokenizer = ActionTokenizer(
            tokenizer=tokenizer,
            bins=n_bin,
            min_action=min_action,
            max_action=max_action
        )
        
        # 분류기 (액션 차원 * 빈 수 = 분류 클래스 수)
        self.classifier = Linear(
            hidden_size, 
            action_dim * n_bin + tokenizer.vocab_size
        )
        
    def forward(self, features):
        # 1. 로짓 계산 (분류 문제로 접근)
        logits = self.classifier(features)  # [batch, seq_len, vocab_size + action_vocab]
        
        # 2. 액션 토큰 예측
        action_logits = logits[..., :self.action_dim * self.n_bin]
        action_probs = F.softmax(action_logits, dim=-1)
        
        # 3. 가장 높은 확률의 토큰 선택
        action_tokens = torch.argmax(action_probs, dim=-1)
        
        # 4. 토큰을 연속 액션으로 디코딩
        decoded_actions = self.action_tokenizer.decode_token_ids_to_actions(
            action_tokens.cpu().numpy()
        )
        
        return torch.tensor(decoded_actions, device=features.device)
        
    def compute_loss(self, logits, target_actions, mask=None):
        # 액션을 토큰으로 인코딩
        target_tokens = self.action_tokenizer.encode_actions_to_token_ids(
            target_actions.cpu().numpy()
        )
        
        # 크로스 엔트로피 손실
        loss = F.cross_entropy(
            logits.view(-1, logits.size(-1)),
            target_tokens.view(-1),
            ignore_index=-100
        )
        
        return loss
```

**ActionTokenizer의 작동 원리:**
```python
class ActionTokenizer:
    def encode_actions_to_token_ids(self, actions):
        # 1. 연속값을 [-1, 1] 범위로 정규화
        normalized = (actions - self.min_action) / (self.max_action - self.min_action)
        
        # 2. [0, 1] 범위를 n_bin 개의 구간으로 양자화
        quantized = (normalized * (self.bins - 1)).astype(int)
        
        # 3. 각 액션 차원별로 고유 토큰 ID 할당
        token_ids = []
        for dim_idx, dim_values in enumerate(quantized.T):
            dim_token_ids = dim_values + dim_idx * self.bins
            token_ids.append(dim_token_ids)
            
        return np.concatenate(token_ids)
    
    def decode_token_ids_to_actions(self, token_ids):
        # 역과정: 토큰 ID → 연속값
        # ...
```

**특징:**
- 🔗 **언어-액션 통합**: 텍스트와 액션을 동일한 토큰 공간에서 처리
- 📚 **언어모델 활용**: 기존 언어모델의 강력한 학습 능력 활용
- 🎯 **일관성**: 언어 명령과 액션 예측의 일관된 처리
- ❌ **한계**: 연속성 정보 손실, 양자화 오차

**적용 예시**: 언어 명령과 밀접한 태스크, 설명 가능한 액션 생성

### 3. 정책의 학습 과정

#### 손실 함수 구조
```python
def policy_loss(predicted_actions, ground_truth_actions, attention_mask):
    # 1. 팔 제어 손실 (Huber Loss - 연속값)
    arm_loss = F.huber_loss(predicted_actions[..., :6], gt_actions[..., :6])
    
    # 2. 그리퍼 제어 손실 (Binary Cross Entropy - 이진값)
    gripper_loss = F.binary_cross_entropy_with_logits(
        predicted_actions[..., -1], gt_actions[..., -1]
    )
    
    # 3. 마스킹된 위치만 계산
    if attention_mask is not None:
        arm_loss = arm_loss[attention_mask].mean()
        gripper_loss = gripper_loss[attention_mask].mean()
    
    return {
        'loss_arm': arm_loss,
        'loss_gripper': gripper_loss,
        'total_loss': arm_loss + gripper_loss
    }
```

### 4. 정책의 실행 흐름

#### 훈련 시 정책 작동
```python
def training_step(self, batch):
    # 1. 멀티모달 입력 처리
    vision_features = self.encode_images(batch['images'])
    text_features = self.encode_text(batch['instructions'])
    
    # 2. 특징 융합
    fused_features = self.backbone(vision_features, text_features)
    
    # 3. 정책을 통한 액션 예측
    predicted_actions = self.policy_head(fused_features)
    
    # 4. 정책 손실 계산
    policy_loss = self.compute_policy_loss(predicted_actions, batch['actions'])
    
    return policy_loss
```

#### 추론 시 정책 작동
```python
def inference(self, image, instruction):
    with torch.no_grad():
        # 1. 입력 전처리
        vision_x = self.preprocess_image(image)
        lang_x = self.tokenize_instruction(instruction)
        
        # 2. 정책을 통한 액션 생성
        predicted_action = self.forward(vision_x, lang_x)
        
        # 3. 액션 후처리 및 안전성 검증
        safe_action = self.validate_action(predicted_action)
        
        return safe_action
```

### 5. 정책 선택 기준

#### 정책 헤드 선택 가이드라인

| 정책 타입 | 적용 상황 | 장점 | 단점 |
|-----------|-----------|------|------|
| **FCDecoder** | 단순한 즉시 반응 태스크 | 빠른 추론, 경량화 | 시간적 맥락 부족 |
| **LSTMDecoder** | 순차적 행동이 중요한 태스크 | 시간적 의존성 모델링 | 장기 의존성 한계 |
| **GPTDecoder** | 복합적이고 긴 시퀀스 태스크 | 강력한 시퀀스 모델링 | 계산 비용 높음 |
| **DiscreteDecoder** | 언어모델과 통합된 시스템 | 언어-액션 통합 학습 | 연속성 정보 손실 |

### 6. 정책 최적화 기법

#### 정책 정규화
```python
# 액션 값 정규화
def normalize_actions(actions):
    # [-1, 1] 범위로 정규화
    normalized = (actions - action_min) / (action_max - action_min) * 2 - 1
    return normalized

# μ-law 압축 (음성 처리에서 영감)
def mu_law_encoding(actions, mu=255):
    return torch.sign(actions) * torch.log(1 + mu * torch.abs(actions)) / torch.log(1 + mu)
```

#### 안전성 보장
```python
class ActionValidator:
    def validate_action(self, action):
        # 1. 속도 제한
        action.linear_x = torch.clamp(action.linear_x, -0.5, 0.5)
        action.angular_z = torch.clamp(action.angular_z, -1.0, 1.0)
        
        # 2. 신뢰도 검사
        if action.confidence < 0.3:
            return self.get_safe_default_action()
            
        return action
```

## 🧠 VLA 모델 아키텍처 분석

### 1. 모델 백본 구조

RoboVLMs는 다양한 백본 모델을 지원하는 모듈러 아키텍처를 채택합니다:

#### 지원되는 백본 모델들
- **RoboFlamingo**: OpenFlamingo 기반 멀티모달 모델
- **RoboLLaVA**: LLaVA 기반 비전-언어 모델  
- **RoboQwen**: Qwen 기반 대화형 AI 모델
- **RoboPaligemma**: PaLI 계열 멀티모달 모델
- **RoboMoonDream**: 경량화된 비전-언어 모델
- **RoboUform**: Unified 형태의 멀티모달 모델

#### 백본 모델의 공통 인터페이스

```python
class BaseRoboVLM(nn.Module):
    def __init__(self, configs, train_setup_configs, ...):
        # 공통 초기화 구조
        self._init_backbone()      # 백본 모델 초기화
        self._init_heads()         # 정책 헤드 초기화
        self._trainable_params_setup()  # 훈련 파라미터 설정
    
    @property
    def hidden_size(self):         # 은닉층 크기
    
    @property  
    def vision_tower(self):        # 비전 인코더
    
    @property
    def text_tower(self):          # 텍스트 인코더
    
    def encode_images(self, images): # 이미지 인코딩
    
    def forward(self, vision_x, lang_x, ...): # 순전파
```

### 2. 멀티모달 입력 처리

#### 이미지 처리 파이프라인
```python
def encode_images(self, images, image_sizes=None):
    # 입력: images: list of b,c,h,w or b,t,c,h,w
    # 출력: image_features: b, t, n, d
    
    # 1. 이미지 전처리
    # 2. 비전 인코더를 통한 특징 추출
    # 3. 시퀀스 차원으로 재구성
```

#### 언어 처리 파이프라인
- 토크나이저를 통한 텍스트 인코딩
- 프롬프트 빌더를 통한 대화 형식 구성
- 어텐션 마스크 생성

### 3. 액션 예측 시스템

#### 액션 토크나이저 (Discrete Actions)
```python
class ActionTokenizer:
    def __init__(self, tokenizer, bins=256, min_action=-1, max_action=1):
        # 연속적인 액션을 이산적인 토큰으로 변환
        
    def encode_actions_to_token_ids(self, action):
        # 액션 → 토큰 ID 변환
        
    def decode_token_ids_to_actions(self, action_token_ids):
        # 토큰 ID → 액션 변환
```

#### 정책 헤드 구조
- **FCDecoder**: 완전연결층 기반 디코더
- **LSTMDecoder**: LSTM 기반 시퀀스 디코더  
- **GPTDecoder**: GPT 스타일 트랜스포머 디코더
- **DiscreteDecoder**: 이산적 액션 공간 디코더

## 🎯 액션 규정 및 처리 방식

### 1. 액션 타입 정의

VLA 시스템에서 지원하는 액션 타입들:

```python
class ActionType(Enum):
    MOVE = "move"           # 이동
    TURN = "turn"           # 회전
    STOP = "stop"           # 정지
    GRAB = "grab"           # 잡기
    RELEASE = "release"     # 놓기
    POINT = "point"         # 가리키기
    LOOK = "look"           # 보기
    NAVIGATE = "navigate"   # 네비게이션
    AVOID = "avoid"         # 회피
    UNKNOWN = "unknown"     # 미지정
```

### 2. 액션 데이터 구조

```python
@dataclass
class RobotAction:
    action_type: ActionType    # 액션 타입
    linear_x: float = 0.0      # 선형 속도 (전후)
    linear_y: float = 0.0      # 선형 속도 (좌우)
    angular_z: float = 0.0     # 각속도 (회전)
    target_object: str = None  # 목표 객체
    confidence: float = 0.0    # 신뢰도
    description: str = ""      # 설명
```

### 3. VLA 출력 파싱 시스템

#### 텍스트 기반 액션 파싱
```python
class VLAActionParser:
    def parse_text_output(self, vla_output: str) -> RobotAction:
        # 1. 액션 타입 결정
        action_type = self._determine_action_type(text)
        
        # 2. 키워드 매칭을 통한 액션 분류
        # 3. 방향성 및 속도 수식어 처리
        # 4. 신뢰도 계산
        
    def _determine_action_type(self, text: str) -> ActionType:
        # 키워드 기반 액션 타입 결정
        for action_type, keywords in self.action_keywords.items():
            # 키워드 매칭 스코어 계산
```

#### 세그멘테이션 토큰 기반 파싱
```python
def parse_segmentation_output(self, vla_output: str, image_width: int, image_height: int):
    # <loc0500><loc0300><loc0700><loc0600> 형태의 위치 토큰 파싱
    loc_tokens = re.findall(r"<loc(\d{4})>", vla_output)
    
    # 바운딩 박스에서 이동 명령 계산
    linear_x, linear_y, angular_z = self._calculate_movement_from_bbox(bbox, ...)
```

### 4. 액션 공간 처리

#### 연속 액션 공간
- 정규화: `normalize_action(action, action_min=-1, action_max=1)`
- 정칙화: `regularize_action(x, x_mean, x_std)` 
- μ-law 압축: `mu_law_companding(x, mu=255)`

#### 이산 액션 공간
- 빈 양자화: 연속 값을 256개 빈으로 분할
- 토큰 매핑: 각 빈을 고유 토큰 ID에 매핑
- 언어 모델 통합: 액션 토큰을 텍스트 토큰과 함께 처리

## 🔄 데이터 처리 파이프라인

### 1. 액션 예측 데이터셋

```python
class ActionPredictionDataset(BaseTaskDataset):
    def __init__(self, 
                 window_size: int = 16,        # 히스토리 윈도우 크기
                 fwd_pred_next_n: int = 2,     # 예측할 미래 스텝 수
                 organize_type: str = "segment", # "interleave" or "segment"
                 discrete: bool = True,         # 이산/연속 액션
                 ...):
```

#### 데이터 조직화 방식

**Segment 방식**:
```
[히스토리 이미지] + [언어 명령] + [히스토리 액션] + [미래 액션 예측]
```

**Interleave 방식**:
```
[이미지1] + [액션1] + [이미지2] + [액션2] + ... + [예측 액션]
```

### 2. 배치 변환 시스템

```python
class ActionPredictionBatchTransform:
    def convert_image(self, images, image_mask):
        # 이미지 텐서 변환 및 히스토리 처리
        
    def convert_action(self, action, action_mask):
        # 액션 정규화, 정칙화, μ-law 변환
        
    def wrap_instruction_and_action_segment(self, task_description, action, action_mask):
        # 명령어와 액션을 하나의 시퀀스로 결합
```

## 🚀 모델 사용 방법

### 1. 훈련 설정

```python
# 설정 로드
configs = load_config("configs/calvin_finetune/roboflamingo_calvin.yaml")

# 모델 초기화
model = build_vlm(vlm_config, tokenizer_config, precision="bf16")

# 데이터 모듈 설정
data_module = GRDataModule(
    train_dataset=train_dataset_configs,
    val_dataset=val_dataset_configs,
    batch_size=batch_size,
    num_workers=num_workers
)

# 훈련 실행
trainer = BaseTrainer(configs)
trainer.fit(model, data_module)
```

### 2. 추론 과정

```python
# 이미지와 언어 입력 준비
vision_x = preprocess_images(images)
lang_x = tokenize_instruction(instruction)

# 모델 추론
with torch.no_grad():
    outputs = model.forward(
        vision_x=vision_x,
        lang_x=lang_x,
        mode="inference"
    )

# 액션 디코딩
if discrete_actions:
    actions = action_tokenizer.decode_token_ids_to_actions(outputs.action_logits)
else:
    actions = outputs.action_predictions
```

### 3. 액션 후처리

```python
# VLA 출력 파싱
parser = VLAActionParser()
action = parser.parse_text_output(vla_output, original_prompt)

# 안전성 검증
validator = ActionValidator(max_linear_speed=0.5, max_angular_speed=1.0)
safe_action = validator.validate_action(action)

# 로봇 제어 명령 생성
if validator.is_safe_action(safe_action):
    robot_command = {
        'linear': {'x': safe_action.linear_x, 'y': safe_action.linear_y},
        'angular': {'z': safe_action.angular_z}
    }
```

## 📊 성능 및 특징

### 1. 지원 데이터셋
- **CALVIN**: 시뮬레이션 환경에서의 장기 태스크
- **Open-X Embodiment**: 다양한 로봇 데이터셋 통합
- **Custom Datasets**: 사용자 정의 데이터셋 지원

### 2. 주요 특징
- **멀티모달 융합**: 비전, 언어, 액션의 통합 처리
- **시퀀스 모델링**: 시간적 의존성을 고려한 액션 예측
- **유연한 액션 공간**: 연속/이산 액션 모두 지원
- **확장 가능한 아키텍처**: 새로운 백본 모델 쉽게 추가 가능
- **안전성 검증**: 액션 유효성 및 안전성 검사

### 3. 훈련 최적화
- **혼합 정밀도**: BF16을 통한 메모리 효율성
- **그래디언트 체크포인팅**: 메모리 사용량 최적화
- **분산 훈련**: 멀티 GPU 지원
- **점진적 학습**: 사전훈련 → 파인튜닝 파이프라인

## 🔧 실제 활용 예시

### Jetson VLA 테스트 시스템
```python
# jetson_vla_test.py에서의 활용
def main():
    # 목표 설정
    goal = Goal.FIND_OBJECT
    target_object = "cup"
    
    # VLA 프롬프트 생성
    prompt = get_vlm_prompt(goal, target_object=target_object)
    
    # 모델 추론
    vlm_output = model.generate(prompt, image)
    
    # 액션 실행
    execute_action(goal, vlm_output, frame, target_object=target_object)
```

이 분석을 통해 RoboVLMs가 어떻게 VLA 모델을 구현하고, 정책을 통해 액션을 규정하며, 실제 로봇 제어에 활용되는지 상세히 파악할 수 있습니다. 
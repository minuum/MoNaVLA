# Red Ball Navigation System - 상세 설계

**Date**: 2026-01-19  
**Objective**: Red Ball + Yellow Bucket 기반 LoRA-free navigation system  
**Timeline**: 2 weeks to deployment

---

## 1. System Architecture

### 1.1 Overall Pipeline

```
[Camera] → [VLM Feature Extractor] → [Action Head] → [Navigation Controller]
   ↓              ↓ (Frozen)              ↓ (Trainable)         ↓
 Image    Visual Features (80%)      LEFT/RIGHT Actions    Motor Commands
```

### 1.2 Component Details

#### A. Vision System
```python
Input: RGB image (224x224)
Camera: 30cm height, wide-angle
Objects: Red Ball (target), Yellow Bucket (obstacle)
Preprocessing: Resize, normalize to ImageNet stats
```

#### B. VLM Feature Extractor (Frozen)
```python
Model: Kosmos-2 (Google Robot pretrained)
Input: Image + Structured Prompt
Output: Visual features (1024-dim)
Status: FROZEN (no training)
```

#### C. Action Head (Trainable)
```python
Architecture: LSTM + MLP
Input: VLM features (1024) + Instruction embedding
Hidden: 512-dim LSTM
Output: (linear_x, angular_z)
Loss: MSE (regression)
```

#### D. Navigation Controller
```python
Input: Predicted actions
Output: Motor commands (velocity)
Safety: Collision detection, speed limits
```

---

## 2. Data Collection 설계

### 2.1 Objects 구성

**Target Object**: Red Ball
- Price: $10 (soccer ball)
- Size: ~22cm diameter
- Color: Bright red
- VLM Recognition: 80%

**Obstacle Object**: Yellow Bucket
- Price: $5 (plastic bucket)
- Size: ~30cm height, 25cm diameter
- Color: Bright yellow
- VLM Recognition: 80%

**Alternative**: Cardboard boxes ($0, free)

---

### 2.2 Episode Structure

```python
Episode Structure:
{
    'observations': {
        'image': [H, W, 3],  # RGB image 224x224
        'instruction': str,  # Navigation instruction
    },
    'actions': {
        'linear_x': float,   # Forward velocity
        'angular_z': float,  # Turning velocity
    },
    'metadata': {
        'object_type': 'red_ball' or 'yellow_bucket',
        'target_side': 'LEFT' or 'RIGHT',
        'obstacle_present': bool,
    }
}
```

---

### 2.3 Data Collection 계획

#### Phase 1: Red Ball Only (200 episodes)

**Setup**:
```
Environment: 복도 (3-5m length)
Target: Red Ball (floor에 배치)
Obstacle: None (빈 복도)
Variations:
  - Target position: LEFT, RIGHT, CENTER
  - Distance: 1m, 2m, 3m
  - Lighting: Normal, Dim
```

**Instructions**:
```python
instructions_left = [
    "Navigate around obstacles and reach the front of the red ball on the left",
    "Navigate to the left of the red ball",
    "Go to the red ball on the left",
]

instructions_right = [
    "Navigate around obstacles and reach the front of the red ball on the right", 
    "Navigate to the right of the red ball",
    "Go to the red ball on the right",
]
```

**Distribution**:
- LEFT: 100 episodes
- RIGHT: 100 episodes

---

#### Phase 2: Red Ball + Yellow Bucket (150 episodes)

**Setup**:
```
Target: Red Ball
Obstacle: Yellow Bucket (between robot and ball)
Variations:
  - Obstacle position: Various
  - Path complexity: Simple, Medium
```

**Distribution**:
- LEFT + obstacle: 75 episodes
- RIGHT + obstacle: 75 episodes

---

#### Phase 3: Diversity (50 episodes, optional)

**Variations**:
- Multiple buckets
- Different distances
- Corner cases
- Edge scenarios

---

### 2.4 Collection Protocol

**Per Episode**:
```python
1. Place objects (Red Ball + optional Bucket)
2. Robot initial position (2-3m away)
3. Select instruction (LEFT or RIGHT)
4. Teleoperate robot to target
5. Record:
   - Images (30 fps → downsample to 10 fps)
   - Actions (linear_x, angular_z)
   - Instruction
6. Save to H5 file
```

**Quality Control**:
- Smooth trajectories (no jerky movements)
- Successful reaching (within 30cm of target)
- Correct side (LEFT vs RIGHT verified)

---

## 3. Model Design

### 3.1 Option A: Instruction-Specific (Recommended) ⭐⭐⭐⭐⭐

**Architecture**:
```
Two separate models:
  - Model_LEFT: For LEFT instructions
  - Model_RIGHT: For RIGHT instructions
```

**Advantages**:
- ✅ Proven to work (current system)
- ✅ Simpler learning (no instruction confusion)
- ✅ Higher accuracy expected
- ✅ Easy to debug

**Implementation**:
```python
class NavigationModel:
    def __init__(self, side='LEFT'):
        self.vlm = load_frozen_vlm()  # Kosmos-2
        self.action_head = LSTMActionHead(
            input_dim=1024,  # VLM features
            hidden_dim=512,
            output_dim=2,    # (linear_x, angular_z)
        )
        self.side = side
    
    def forward(self, image):
        # Frozen VLM
        prompt = self.get_structured_prompt(self.side)
        features = self.vlm(image, prompt)  # (1024,)
        
        # Trainable action head
        action = self.action_head(features)  # (2,)
        return action
    
    def get_structured_prompt(self, side):
        return f"<grounding> Is there a red ball on the floor? " \
               f"Navigate to the {side}. JSON: {{\"detected\": true/false}}"
```

**Training**:
```python
# Model LEFT
train_on_episodes(
    model=Model_LEFT,
    episodes=filter(episodes, instruction_contains=['left', 'LEFT']),
    epochs=10,
    batch_size=8,
)

# Model RIGHT  
train_on_episodes(
    model=Model_RIGHT,
    episodes=filter(episodes, instruction_contains=['right', 'RIGHT']),
    epochs=10,
    batch_size=8,
)
```

**Inference**:
```python
def navigate(instruction, image):
    if 'left' in instruction.lower():
        action = model_left(image)
    elif 'right' in instruction.lower():
        action = model_right(image)
    else:
        raise ValueError("Unknown instruction")
    
    return action
```

---

### 3.2 Option B: Unified Model (Experimental) ⭐⭐⭐

**Architecture**:
```
Single model with instruction embedding
```

**Implementation**:
```python
class UnifiedNavigationModel:
    def __init__(self):
        self.vlm = load_frozen_vlm()
        self.instruction_encoder = nn.Embedding(2, 64)  # LEFT=0, RIGHT=1
        self.action_head = LSTMActionHead(
            input_dim=1024 + 64,  # VLM + instruction
            hidden_dim=512,
            output_dim=2,
        )
    
    def forward(self, image, instruction_id):
        # VLM features
        features = self.vlm(image, prompt)  # (1024,)
        
        # Instruction embedding
        inst_emb = self.instruction_encoder(instruction_id)  # (64,)
        
        # Concatenate
        combined = torch.cat([features, inst_emb], dim=-1)  # (1088,)
        
        # Action head
        action = self.action_head(combined)
        return action
```

**Advantages**:
- ✅ Single model (simpler deployment)
- ✅ Shared visual understanding
- ✅ Can test instruction grounding

**Disadvantages**:
- ⚠️ More complex learning
- ⚠️ May confuse LEFT/RIGHT
- ⚠️ Unproven in our setup

**Decision**: Try if time permits, but **prioritize Option A**

---

## 4. Training Configuration

### 4.1 Config Files

**Model LEFT**:
```json
{
  "exp_name": "red_ball_left",
  "model": "kosmos",
  "model_url": "https://huggingface.co/microsoft/kosmos-2-patch14-224",
  
  "train_setup": {
    "precision": "16-mixed",
    "predict_action": true,
    "freeze_backbone": true,  // Frozen VLM!
    "train_vision": false,
    "lora_enable": false,      // No LoRA!
  },
  
  "act_head": {
    "type": "MobileVLALSTMDecoder",
    "hidden_size": 512,
    "action_dim": 2,
  },
  
  "train_dataset": {
    "type": "MobileVLAH5Dataset",
    "data_dir": "/path/to/red_ball_dataset",
    "episode_pattern": "episode_*_left.h5",  // LEFT only
  },
  
  "trainer": {
    "max_epochs": 10,
    "batch_size": 8,
    "learning_rate": 1e-4,
  }
}
```

**Model RIGHT**: Same but with `episode_*_right.h5`

---

### 4.2 Training Script

```bash
#!/bin/bash
# scripts/train_red_ball.sh

# Train LEFT model
python RoboVLMs_upstream/robovlms/train/train.py \
    --config configs/red_ball_left.json \
    --gpus 1

# Train RIGHT model  
python RoboVLMs_upstream/robovlms/train/train.py \
    --config configs/red_ball_right.json \
    --gpus 1

echo "✅ Training complete!"
```

---

### 4.3 Expected Training Time

```
Dataset: 350 episodes (200 LEFT + 150 RIGHT)
Hardware: 1x GPU (RTX 3090 or similar)
Batch size: 8
Epochs: 10

Per model training time: ~2-3 hours
Total training time: ~5-6 hours

→ Can finish in single day!
```

---

## 5. Inference Pipeline

### 5.1 Pipeline Architecture

```python
class RedBallNavigationPipeline:
    def __init__(self):
        # Load models
        self.model_left = load_model('red_ball_left.ckpt')
        self.model_right = load_model('red_ball_right.ckpt')
        
        # Processors
        self.processor = AutoProcessor.from_pretrained('kosmos-2')
        
        # Safety
        self.max_linear = 0.3  # m/s
        self.max_angular = 0.5  # rad/s
    
    def predict(self, image, instruction):
        """
        Main inference function
        """
        # 1. Determine model
        if 'left' in instruction.lower():
            model = self.model_left
            side = 'LEFT'
        elif 'right' in instruction.lower():
            model = self.model_right
            side = 'RIGHT'
        else:
            raise ValueError(f"Unknown instruction: {instruction}")
        
        # 2. Predict action
        action = model(image)  # (linear_x, angular_z)
        
        # 3. Safety clipping
        action[0] = np.clip(action[0], 0, self.max_linear)
        action[1] = np.clip(action[1], -self.max_angular, self.max_angular)
        
        return action, side
    
    def navigate_episode(self, camera, instruction, max_steps=100):
        """
        Full navigation episode
        """
        for step in range(max_steps):
            # Get image
            image = camera.get_image()
            
            # Predict
            action, side = self.predict(image, instruction)
            
            # Execute
            robot.move(linear_x=action[0], angular_z=action[1])
            
            # Check completion (distance to red ball < 30cm)
            if self.reached_target(image):
                print(f"✅ Reached red ball ({side})!")
                return True
        
        print("❌ Max steps reached")
        return False
```

---

### 5.2 ROS2 Integration (Real Robot)

```python
# ros2_navigation_node.py

import rclpy
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist

class RedBallNavigationNode(Node):
    def __init__(self):
        super().__init__('red_ball_nav')
        
        # Pipeline
        self.pipeline = RedBallNavigationPipeline()
        
        # ROS
        self.image_sub = self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, 10
        )
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Current instruction
        self.instruction = "Navigate to the left of the red ball"
        
    def image_callback(self, msg):
        # Convert ROS image to numpy
        image = self.ros_to_numpy(msg)
        
        # Predict
        action, side = self.pipeline.predict(image, self.instruction)
        
        # Publish
        cmd = Twist()
        cmd.linear.x = float(action[0])
        cmd.angular.z = float(action[1])
        self.cmd_pub.publish(cmd)
```

---

## 6. Evaluation Metrics

### 6.1 Success Criteria

```python
Episode Success Metrics:
1. Reached Target: Distance to red ball < 30cm ✅
2. Correct Side: Robot on LEFT/RIGHT as instructed ✅
3. No Collision: No collision with yellow bucket ✅
4. Time Limit: Completed within 2 minutes ✅

Success Rate = (Successful Episodes / Total Episodes) × 100
```

### 6.2 Target Performance

```
Minimum Acceptable: 75% success rate
Target: 85% success rate
Excellent: 95% success rate

Current baseline (bottle/box): 60-70%
Expected (red ball): 85-95% ✅
```

---

## 7. Implementation Timeline

### Week 1: Data Collection

**Day 1 (Monday)**:
- ✅ Order Red Ball ($10) + Yellow Bucket ($5)
- ✅ Prepare data collection setup
- ✅ Test camera positioning

**Day 2-3 (Tue-Wed)**:
- ✅ Collect 200 episodes (Red Ball only)
  - 100 LEFT, 100 RIGHT
- ✅ Quality check

**Day 4-5 (Thu-Fri)**:
- ✅ Collect 150 episodes (with Yellow Bucket)
  - 75 LEFT, 75 RIGHT
- ✅ Final dataset validation

**Milestone**: 350 episodes collected ✅

---

### Week 2: Training & Deployment

**Day 1 (Monday)**:
- ✅ Create config files (red_ball_left.json, red_ball_right.json)
- ✅ Start training both models
- ✅ Monitor training (~5-6 hours)

**Day 2 (Tuesday)**:
- ✅ Evaluate trained models on validation set
- ✅ Tune hyperparameters if needed
- ✅ Re-train if necessary

**Day 3 (Wednesday)**:
- ✅ Implement inference pipeline
- ✅ Test with sample images
- ✅ Verify action predictions

**Day 4 (Thursday)**:
- ✅ ROS2 integration
- ✅ Real robot testing (dry run)
- ✅ Safety checks

**Day 5 (Friday)**:
- ✅ Full navigation tests
- ✅ Measure success rate
- ✅ Document results

**Milestone**: Deployment ready! ✅

---

## 8. Risk Mitigation

### Risk 1: VLM Recognition Drops in Real Environment

**Probability**: Low (20%)  
**Mitigation**:
- Pre-test VLM on real environment images
- Adjust lighting if needed
- Use larger ball if recognition < 70%

---

### Risk 2: Action Head Learning Insufficient

**Probability**: Low (15%)  
**Mitigation**:
- Collect more data (500 episodes vs 350)
- Tune hyperparameters (learning rate, hidden size)
- Fallback to LoRA if < 65% success

---

### Risk 3: LEFT/RIGHT Confusion

**Probability**: Medium (30%)  
**Mitigation**:
- Use instruction-specific models (clear separation)
- Test thoroughly on validation set
- Add explicit LEFT/RIGHT checks in code

---

## 9. Fallback Plan

### If Success Rate < 75%

**Option 1**: More Data
- Collect additional 200 episodes
- Focus on failure cases
- Re-train with 550 total episodes

**Option 2**: Object Swap
- Try Yellow Bucket as target (also 80% recognition)
- Test if object type matters

**Option 3**: LoRA Fine-tuning
- Add LoRA to VLM
- Keep everything else same
- Expected boost: +10-15%

---

## 10. Cost Analysis

### Total Budget

```
Hardware:
  Red Ball:              $10
  Yellow Bucket:         $5
  ---------------------------
  Subtotal:              $15

Compute (optional cloud):
  Training (5-6 hrs):    $0 (local GPU)
  OR Cloud GPU:          ~$5
  ---------------------------
  Subtotal:              $0-5

Total:                   $15-20
```

### Time Investment

```
Data collection:       3-4 days (researcher time)
Training:              5-6 hours (GPU time)  
Integration:           2-3 days (engineering)
Testing:               1-2 days

Total:                 ~2 weeks
```

---

## 11. Success Indicators

### Week 1 Checkpoint

```
✅ 350 episodes collected
✅ Data quality verified
✅ VLM recognition > 75% on samples
```

**Go/No-Go**: If VLM < 70%, consider object change

---

### Week 2 Checkpoint

```
✅ Models trained successfully
✅ Validation accuracy > 80%
✅ Inference pipeline working
```

**Go/No-Go**: If validation < 70%, add more data or try LoRA

---

### Final Deployment

```
✅ Real robot success rate > 75%
✅ No safety issues
✅ LEFT/RIGHT accuracy > 90%
```

**Go/No-Go**: Deploy if all criteria met

---

## 12. Deliverables

### Code

```
configs/
  ├── red_ball_left.json
  └── red_ball_right.json

scripts/
  ├── collect_red_ball_data.py
  ├── train_red_ball.sh
  └── test_red_ball_inference.py

ros2_nodes/
  └── red_ball_navigation_node.py
```

### Documentation

```
docs/
  ├── RED_BALL_SYSTEM_DESIGN.md (this file)
  ├── RED_BALL_TRAINING_LOG.md
  └── RED_BALL_DEPLOYMENT_GUIDE.md
```

### Models

```
checkpoints/
  ├── red_ball_left_epoch10.ckpt
  └── red_ball_right_epoch10.ckpt
```

---

## 13. Summary

### Design Choice: Instruction-Specific Models ✅

**Rationale**:
- ✅ Proven to work (current system)
- ✅ Red Ball: 80% VLM recognition
- ✅ No LoRA needed
- ✅ 2-week timeline achievable
- ✅ $15 total cost

### Expected Outcome

```
Current System:
  Objects: Bottle/Box
  VLM: 20% recognition
  Navigation: 60-70% success

Red Ball System:
  Objects: Red Ball/Yellow Bucket
  VLM: 80% recognition
  Navigation: 85-95% success ⭐

Improvement: +15-25% success rate!
```

### Go Decision

**🚀 PROCEED with Red Ball design!**

**Reasoning**:
1. High VLM recognition (80%)
2. Low cost ($15)
3. Fast timeline (2 weeks)
4. No LoRA required
5. Low risk

**Next Step**: Order Red Ball + Yellow Bucket TODAY!

---

**End of Design Document**

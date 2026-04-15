# Mobile-VLA 추론(Inference) 시나리오 분석

**작성일**: 2025-12-04
**목표**: 실제 로봇 제어를 위한 추론 시나리오 설계 및 구현

---

## 🎯 **교수님 요구사항**

### **추론 시나리오**
> 처음에 거리를 잼, 그 자리에서 카메라로 찍은 이미지, 텍스트(고정)
> 
> **0.4초마다 2DOF (velocity)를 가져옴**
> 
> 앞의 window frame에서는 오래 걸리고, 뒤에서는 기존 action대로 이동하는 형태

### **Action Chunk 방식**
> 20ms마다 예측하면 계산량이 느리기에, **앞으로의 10개를 한꺼번에 계산**
> 
> **200ms마다 계산** (10 timesteps × 20ms)
>
> 다른 태스크는 20초마다 예측

### **검증 필요**
> 파인튜닝하고 학습된 값을 가지고 추론해서 **제대로된 x, y 값을 뿌려주는지** 테스트

---

## 📊 **현재 학습 설정 (Training)**

### **데이터셋 구조**
```python
window_size = 8          # 과거 8 프레임
fwd_pred_next_n = 10     # 미래 10 프레임
total_frames = 18        # 총 18 프레임

# 입력
images: (18, 3, 224, 224)      # 18 프레임 이미지
actions: (18, 2)               # 18 프레임 velocity

# 학습
for each batch:
    context = VLM(images[:8])       # 과거 8 프레임으로 context
    predicted = ActionHead(context)  # 미래 10 프레임 예측
    loss = MSE(predicted, actions[8:18])
```

### **시간 간격 (수집 시)**
```python
# 데이터 수집 시 프레임 간격 확인 필요
frame_interval = ?  # 몇 ms 간격으로 수집했는지

# 예상: 100-200ms 간격
# → 18 프레임 = 1.8~3.6초 시퀀스
```

---

## 🚀 **추론 시나리오 설계**

### **Scenario 1: Sliding Window (교수님 요구사항)**

```python
class MobileVLAInference:
    def __init__(self):
        self.window_size = 8
        self.action_chunk_size = 10
        self.control_interval = 0.4  # 400ms (교수님 요구사항)
        
        self.image_buffer = deque(maxlen=8)
        self.action_buffer = deque(maxlen=10)
        self.last_inference_time = 0
        
    def run(self):
        while not arrived:
            current_time = time.time()
            
            # Step 1: 이미지 캡처
            image = camera.capture()
            self.image_buffer.append(image)
            
            # Step 2: 0.4초마다 추론
            if current_time - self.last_inference_time >= 0.4:
                if len(self.image_buffer) == 8:
                    # VLM + Action Head 추론
                    context = model.vlm(self.image_buffer)
                    action_chunk = model.action_head(context)  # (10, 2)
                    
                    self.action_buffer = deque(action_chunk)
                    self.last_inference_time = current_time
            
            # Step 3: Action buffer에서 velocity 가져오기
            if self.action_buffer:
                velocity = self.action_buffer.popleft()
                robot.set_velocity(velocity)
            
            time.sleep(0.02)  # 20ms control loop
```

**특징**:
- ✅ 0.4초마다 추론 (교수님 요구사항)
- ✅ Action chunk 활용 (10개 미리 예측)
- ✅ 20ms control loop
- ⚠️ 처음 8 프레임 모을 때까지 대기 (0.8~1.6초)

---

### **Scenario 2: Action Chunk with Fast Start**

```python
class FastStartInference:
    def __init__(self):
        self.window_size = 8
        self.action_chunk_size = 10
        self.inference_interval = 0.2  # 200ms (action chunk 방식)
        
    def run(self):
        # Step 1: 초기 이미지 수집 (빠르게)
        for i in range(8):
            image = camera.capture()
            self.image_buffer.append(image)
            time.sleep(0.05)  # 50ms 간격 (빠르게 채움)
        
        # Step 2: 추론 루프
        while not arrived:
            # 200ms마다 추론 (교수님 언급)
            context = model.vlm(self.image_buffer)
            action_chunk = model.action_head(context)  # (10, 2)
            
            # 10개 action을 20ms씩 실행
            for action in action_chunk:
                robot.set_velocity(action)
                time.sleep(0.02)  # 20ms
                
                # 새 이미지 추가 (sliding)
                new_image = camera.capture()
                self.image_buffer.append(new_image)
```

**특징**:
- ✅ 빠른 시작 (0.4초 만에 시작)
- ✅ 200ms 추론 간격 (10 × 20ms)
- ✅ Sliding window
- ⚠️ 계산 부하 높음 (200ms로 충분한지?)

---

## ⚙️ **성능 분석 (Latency)**

### **추론 시간 측정 필요**

```python
# 측정해야 할 것들
with torch.no_grad():
    # VLM forward
    t1 = time.time()
    context = model.vlm(images)
    vlm_time = time.time() - t1
    
    # Action Head forward
    t2 = time.time()
    actions = model.action_head(context)
    action_head_time = time.time() - t2
    
total_inference_time = vlm_time + action_head_time
```

**예상 (Frozen VLM)**:
```
VLM forward: ~50-100ms (Kosmos-2, frozen)
Action Head: ~5-10ms (LSTM, tiny)
Total: ~60-110ms

→ 200ms 간격이면 충분!
```

---

## 🔧 **거리 측정 (교수님 요구사항)**

> 처음에 거리를 잼

### **방법 1: 카메라 기반 (Vision)**
```python
def estimate_distance(image, bottle_detector):
    # YOLO로 병 감지
    boxes = bottle_detector(image)
    
    # Bounding box 크기로 거리 추정
    if boxes:
        box_height = boxes[0].height
        # 역비례 관계 (가까우면 크게 보임)
        distance = calibration_constant / box_height
        return distance
    return None
```

### **방법 2: Depth Camera**
```python
# Intel RealSense 등
depth_image = camera.get_depth()
bottle_mask = detector(rgb_image)
average_depth = depth_image[bottle_mask].mean()
return average_depth
```

---

## 📝 **ROS 노드 구현**

```python
#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import torch
from collections import deque

class VLAInferenceNode:
    def __init__(self):
        rospy.init_node('vla_inference')
        
        # 파라미터
        self.control_interval = rospy.get_param('~control_interval', 0.4)  # 400ms
        self.checkpoint_path = rospy.get_param('~checkpoint_path')
        
        # 모델 로드
        self.model = self.load_model(self.checkpoint_path)
        self.model.eval()
        
        # Buffers
        self.image_buffer = deque(maxlen=8)
        self.action_buffer = deque(maxlen=10)
        
        # ROS
        self.bridge = CvBridge()
        self.image_sub = rospy.Subscriber('/camera/image_raw', Image, self.image_callback)
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
        
        self.last_inference_time = rospy.Time.now()
        
        rospy.loginfo("VLA Inference Node started")
        
    def load_model(self, checkpoint_path):
        # Checkpoint 로드
        checkpoint = torch.load(checkpoint_path, map_location='cuda')
        
        # 모델 재구성
        from robovlms.train.mobile_vla_trainer import MobileVLATrainer
        model = MobileVLATrainer.load_from_checkpoint(checkpoint_path)
        model.cuda()
        model.freeze()  # Ensure frozen
        
        return model
        
    def image_callback(self, msg):
        # ROS Image → numpy
        cv_image = self.bridge.imgmsg_to_cv2(msg, "rgb8")
        
        # 전처리 (224x224 resize, normalize)
        image_tensor = self.preprocess(cv_image)
        
        # Buffer에 추가
        self.image_buffer.append(image_tensor)
        
    def preprocess(self, image):
        # Resize to 224x224
        from PIL import Image as PILImage
        import torchvision.transforms as T
        
        pil_img = PILImage.fromarray(image)
        pil_img = pil_img.resize((224, 224))
        
        # To tensor
        tensor = T.ToTensor()(pil_img)
        return tensor
        
    def run(self):
        rate = rospy.Rate(50)  # 20ms = 50Hz
        
        while not rospy.is_shutdown():
            current_time = rospy.Time.now()
            
            # 0.4초마다 추론
            if (current_time - self.last_inference_time).to_sec() >= self.control_interval:
                if len(self.image_buffer) == 8:
                    self.run_inference()
                    self.last_inference_time = current_time
            
            # Action buffer에서 velocity 가져오기
            if self.action_buffer:
                velocity = self.action_buffer.popleft()
                self.publish_velocity(velocity)
            
            rate.sleep()
    
    def run_inference(self):
        # 이미지 스택
        images = torch.stack(list(self.image_buffer)).unsqueeze(0)  # (1, 8, 3, 224, 224)
        images = images.cuda()
        
        # 추론
        with torch.no_grad():
            # VLM forward
            context = self.model.model.encode_images(images)
            
            # Action Head forward
            actions = self.model.model.act_head(context)  # (1, 10, 2)
        
        # Buffer에 저장
        actions = actions.squeeze(0).cpu()  # (10, 2)
        self.action_buffer = deque(actions.numpy())
        
        rospy.loginfo(f"Inference done. Predicted {len(self.action_buffer)} actions")
    
    def publish_velocity(self, velocity):
        twist = Twist()
        twist.linear.x = float(velocity[0])  # linear_x
        twist.linear.y = float(velocity[1])  # linear_y
        twist.angular.z = 0.0  # 고정 (또는 velocity[2] 사용 시)
        
        self.cmd_vel_pub.publish(twist)

if __name__ == '__main__':
    node = VLAInferenceNode()
    node.run()
```

---

## 📊 **검증 계획**

### **Test 1: Velocity 값 검증**
```python
# 예측된 velocity가 합리적인가?
predicted_velocities = []
for _ in range(100):
    vel = model.predict()
    predicted_velocities.append(vel)

# 분석
mean_vel = np.mean(predicted_velocities, axis=0)
std_vel = np.std(predicted_velocities, axis=0)

print(f"Mean velocity: {mean_vel}")  # 예상: [0.1~0.3, -0.1~0.1]
print(f"Std velocity: {std_vel}")    # 예상: [0.05~0.1, 0.05~0.1]
```

### **Test 2: 실시간 성능**
```python
# Latency 측정
latencies = []
for _ in range(100):
    t1 = time.time()
    model.predict()
    latency = time.time() - t1
    latencies.append(latency)

print(f"Mean latency: {np.mean(latencies)*1000:.1f}ms")
print(f"Max latency: {np.max(latencies)*1000:.1f}ms")

# 목표: < 200ms (action chunk size에 맞춤)
```

### **Test 3: 실제 주행**
```
시나리오:
1. 로봇을 2m 거리에 배치
2. 박스를 중앙에 배치
3. 병을 박스 뒤에 배치

측정:
- 성공률 (병에 도달)
- 주행 시간
- 경로 smoothness
- 충돌 여부
```

---

## 📝 **결론 및 다음 단계**

### ✅ **추론 시나리오 설계 완료**
- 0.4초 간격 추론 (교수님 요구사항)
- Action chunk 활용 (10 timesteps)
- ROS 노드 구현 준비

### 🎯 **즉시 실행 가능**
1. ROS 노드 구현 완료
2. Best checkpoint 로드
3. 실제 로봇 테스트

### ⏱️ **예상 타임라인**
- ROS 노드 코드 작성: ~30분
- Latency 측정: ~10분
- 실제 주행 테스트: ~1시간

---

*다음: ROS 노드 구현 및 실제 추론 테스트*

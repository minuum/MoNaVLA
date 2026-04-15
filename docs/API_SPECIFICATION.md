# Mobile VLA API 명세서

**버전**: 1.0.0  
**Base URL**: `http://localhost:8000`  
**인증**: API Key (Header: `X-API-Key`)

---

## 🔐 Authentication

모든 API 요청에 API Key 필요 (Health check 제외)

```bash
# Header
X-API-Key: your-api-key-here
```

**API Key 설정**:
```bash
export VLA_API_KEY="your-secret-key"
python Mobile_VLA/inference_server.py
```

---

## 📡 Endpoints

### 1. Health Check

**Endpoint**: `GET /health`  
**인증**: 불필요

**Response**:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda",
  "gpu_memory": {
    "allocated_gb": 4.2,
    "reserved_gb": 5.1,
    "peak_allocated_gb": 4.5,
    "total_memory_gb": 24.0,
    "device_name": "NVIDIA RTX A5000"
  },
  "quantization": {
    "enabled": false,
    "precision": "FP16"
  }
}
```

---

### 2. Predict Action

**Endpoint**: `POST /predict`  
**인증**: 필요 (`X-API-Key`)

#### Request

**Content-Type**: `application/json`

```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgAA...",
  "instruction": "Navigate around obstacles and reach the front of the beverage bottle on the left"
}
```

**Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | string | ✅ | Base64 encoded RGB image (PNG/JPEG) |
| `instruction` | string | ✅ | Natural language command (max 256 chars) |

**Image Constraints**:
- Format: PNG or JPEG
- Encoding: Base64
- Recommended size: 720x1280 (H x W)
- Color: RGB (3 channels)

**Instruction Examples**:
- `"Navigate around obstacles and reach the front of the beverage bottle on the left"`
- `"Navigate around obstacles and reach the front of the beverage bottle on the right"`
- `"Move forward to the target"`

#### Response

**Success (200 OK)**:
```json
{
  "action": [1.15, -0.32],
  "latency_ms": 385.2,
  "model_name": "mobile_vla_left_chunk10_20251218"
}
```

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `action` | array[float, float] | 2DOF robot action [linear_x, linear_y] |
| `latency_ms` | float | Model inference latency in milliseconds |
| `model_name` | string | Model identifier |

**Action Format**:
- `action[0]`: **linear_x** (m/s) - Forward velocity
  - Range: `[0.0, 2.0]`
  - `0.0`: Stop
  - `2.0`: Maximum forward speed
  
- `action[1]`: **linear_y** (rad/s) - Angular velocity
  - Range: `[-0.5, 0.5]`
  - `< 0`: Turn left
  - `> 0`: Turn right
  - `0.0`: Go straight

**Action Interpretation**:
```python
linear_x, angular_z = action

if linear_x > 0 and angular_z < 0:
    # Move forward and turn left
    
elif linear_x > 0 and angular_z > 0:
    # Move forward and turn right
    
elif linear_x > 0 and angular_z == 0:
    # Move straight forward
    
elif linear_x == 0:
    # Stop
```

#### Error Responses

**403 Forbidden** - Invalid API Key:
```json
{
  "detail": "Invalid API Key"
}
```

**422 Unprocessable Entity** - Missing fields:
```json
{
  "detail": [
    {
      "loc": ["body", "image"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**500 Internal Server Error** - Inference failed:
```json
{
  "detail": "Inference failed: <error message>"
}
```

---

## 💻 Usage Examples

### Python

```python
import requests
import base64
from PIL import Image
from io import BytesIO

# API 설정
API_URL = "http://localhost:8000"
API_KEY = "your-api-key"

# 이미지 로드 및 인코딩
img = Image.open("test_image.jpg")
buffer = BytesIO()
img.save(buffer, format='PNG')
img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

# 요청
headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

payload = {
    "image": img_base64,
    "instruction": "Navigate to the left bottle"
}

response = requests.post(
    f"{API_URL}/predict",
    headers=headers,
    json=payload
)

# 결과
if response.status_code == 200:
    result = response.json()
    linear_x = result['action'][0]
    angular_z = result['action'][1]
    
    print(f"Action: forward={linear_x:.2f} m/s, turn={angular_z:.2f} rad/s")
    print(f"Latency: {result['latency_ms']:.1f} ms")
else:
    print(f"Error: {response.text}")
```

### cURL

```bash
# Health check
curl http://localhost:8000/health

# Predict (with image file)
IMAGE_B64=$(base64 -w 0 test_image.jpg)

curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d "{
    \"image\": \"$IMAGE_B64\",
    \"instruction\": \"Navigate to the left bottle\"
  }"
```

### ROS2 Client

```python
import rclpy
from rclpy.node import Node
import requests
import base64
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
import cv2

class VLAClient(Node):
    def __init__(self):
        super().__init__('vla_client')
        
        # API 설정
        self.api_url = "http://192.168.1.100:8000"
        self.api_key = "your-api-key"
        
        # ROS subscribers/publishers
        self.image_sub = self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, 10
        )
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.bridge = CvBridge()
        self.instruction = "Navigate to the target"
    
    def image_callback(self, msg):
        # ROS Image -> OpenCV
        cv_image = self.bridge.imgmsg_to_cv2(msg, "rgb8")
        
        # OpenCV -> Base64
        _, buffer = cv2.imencode('.jpg', cv_image)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # API 호출
        headers = {"X-API-Key": self.api_key}
        payload = {
            "image": img_base64,
            "instruction": self.instruction
        }
        
        response = requests.post(
            f"{self.api_url}/predict",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Action -> Twist
            twist = Twist()
            twist.linear.x = result['action'][0]
            twist.angular.z = result['action'][1]
            
            self.cmd_pub.publish(twist)
            self.get_logger().info(
                f"Published: v={twist.linear.x:.2f}, ω={twist.angular.z:.2f}"
            )
```

---

## 🚀 Quick Start

### 1. 서버 시작

```bash
cd /home/billy/25-1kp/vla

# API Key 설정
export VLA_API_KEY="my-secret-key"

# FP16 모델 (기본)
export VLA_CHECKPOINT_PATH="runs/.../best_model.ckpt"
python Mobile_VLA/inference_server.py

# 또는 INT8/INT4 양자화 모델
export VLA_USE_QUANTIZATION=true
export VLA_QUANTIZED_CHECKPOINT="quantized_models/left_chunk10/model_quantized.pt"
python Mobile_VLA/inference_server.py
```

### 2. 테스트

```bash
# 환경 변수 설정
export VLA_API_KEY="my-secret-key"

# 전체 테스트 실행
python scripts/test_api_complete.py

# 또는 개별 테스트
python scripts/test_api_complete.py --samples 10
```

---

## 📊 Performance

### Latency

| 구성 | Device | Precision | Latency |
|------|--------|-----------|---------|
| Billy Server | RTX A5000 24GB | FP16 | ~385 ms |
| Billy Server | RTX A5000 24GB | INT8/INT4 | ~350 ms |
| Jetson Orin | Orin 16GB | FP16 | ~450 ms (예상) |
| Jetson Orin | Orin 16GB | INT8/INT4 | ~400 ms (예상) |

### Memory

| Precision | Model Size | Runtime Memory |
|-----------|------------|----------------|
| FP16 | 3.1 GB | 7.4 GB |
| INT8/INT4 (PTQ) | 5.5 GB (파일) | 4.0 GB |

---

## 🔧 Troubleshooting

### API Key 오류
```bash
# API Key 확인
echo $VLA_API_KEY

# 서버 재시작
pkill -f inference_server.py
export VLA_API_KEY="your-key"
python Mobile_VLA/inference_server.py
```

### GPU 메모리 부족
```bash
# 실행 중인 프로세스 확인
nvidia-smi

# 프로세스 종료
pkill -f python

# 양자화 모델 사용
export VLA_USE_QUANTIZATION=true
```

### Connection Refused
```bash
# 서버 상태 확인
curl http://localhost:8000/health

# 포트 확인
netstat -tulpn | grep 8000

# 방화벽 확인 (Jetson)
sudo ufw allow 8000
```

---

## 📝 Notes

1. **이미지 크기**: 720x1280 권장, 다른 크기도 자동 resize됨
2. **Instruction**: 영어로 작성, 최대 256자
3. **Latency**: 첫 요청은 모델 로딩으로 느릴 수 있음
4. **Thread-safe**: 동시 요청 지원 (FastAPI async)
5. **Rate limit**: 없음 (필요시 추가 가능)

---

**Contact**: billy@example.com  
**Repository**: /home/billy/25-1kp/vla

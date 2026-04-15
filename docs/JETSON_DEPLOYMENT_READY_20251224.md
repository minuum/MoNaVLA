# Jetson 로봇 서버 배포 완료 가이드

**일시**: 2025-12-24 07:35 KST  
**브랜치**: `inference-integration`  
**상태**: 🟢 **Jetson 배포 준비 완료**

---

## ✅ 준비된 파일

### 1. Essential Files (모두 커밋됨)

| 파일 | 용도 |
|------|------|
| `requirements-inference.txt` | 최소 dependencies (추론용) |
| `QUICKSTART.md` | 5분 설치 가이드 |
| `README_INFERENCE.md` | Branch 문서 |
| `setup_jetson.sh` | 자동 설치 스크립트 |

### 2. 코드 파일

| 파일 | 상태 |
|------|------|
| `Mobile_VLA/inference_server.py` | ✅ INT8, 경로 수정 완료 |
| `Mobile_VLA/action_buffer.py` | ✅ Import 포함 |
| `Mobile_VLA/configs/*.json` | ✅ Chunk5 config |

### 3. 테스트 스크립트

| 파일 | 용도 |
|------|------|
| `test_api_inference_complete.py` | API 전체 테스트 |
| `test_robot_driving_18steps.py` | 18회 연속 주행 시뮬레이션 |

---

## 🚀 Jetson에서 실행 방법

### Option 1: 자동 설치 (추천)

```bash
# 1. Clone
git clone git@github.com-vla:minuum/vla.git
cd vla
git checkout inference-integration

# 2. 자동 설치
./setup_jetson.sh

# 3. API Key 설정
source secrets.sh

# 4. 서버 시작
python3 -m uvicorn Mobile_VLA.inference_server:app --host 0.0.0.0 --port 8000
```

**소요 시간**: **5-15분** (Jetson 속도에 따라)

---

### Option 2: 수동 설치

```bash
# 1. Clone
git clone git@github.com-vla:minuum/vla.git
cd vla
git checkout inference-integration

# 2. Dependencies 설치
pip install -r requirements-inference.txt

# 3. API Key 생성
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > api_key.txt
export VLA_API_KEY=$(cat api_key.txt)

# 4. 서버 시작
mkdir -p logs
nohup python3 -m uvicorn Mobile_VLA.inference_server:app \
  --host 0.0.0.0 --port 8000 > logs/api_server.log 2>&1 &

# 5. 확인
curl http://localhost:8000/health
```

---

## 📦 필요한 Dependencies

### Core (필수)
```
torch >= 2.2.0
transformers >= 4.41.0
bitsandbytes == 0.43.1
accelerate >= 0.29.0
fastapi >= 0.116.0
uvicorn >= 0.35.0
Pillow >= 10.0.0
numpy >= 1.26.0
```

### Jetson 주의사항
- PyTorch는 Jetson에 pre-installed 가능
- BitsAndBytes는 ARM64 버전 자동 설치
- CUDA 11.8+ 필요

---

## 🔍 검증 방법

### 1. Health Check
```bash
curl http://localhost:8000/health
```

**Expected**:
```json
{
    "status": "healthy",
    "model_loaded": true,
    "device": "cuda",
    "gpu_memory": {
        "allocated_gb": 1.8,
        "device_name": "NVIDIA ..."
    }
}
```

### 2. Simple Test
```bash
python3 scripts/test_api_inference_complete.py
```

**Expected**:
- ✅ 2회 inference 성공
- ✅ Latency ~500-600ms
- ✅ GPU Memory ~1.8GB

### 3. Robot Simulation
```bash
python3 scripts/test_robot_driving_18steps.py
```

**Expected**:
- ✅ 18/18 성공
- ✅ Total ~10-11초 (Jetson)
- ✅ No memory leaks

---

## 📊 예상 성능 (Jetson Orin)

| Metric | Billy (A5000) | **Jetson Orin (예상)** |
|--------|---------------|----------------------|
| **GPU Memory** | 1.80 GB | 1.8-2.0 GB |
| **Inference** | 495 ms | 500-600 ms |
| **Rate** | 2.0 Hz | 1.7-2.0 Hz |
| **18 calls** | 9.6 sec | 10-11 sec |

**평가**: ✅ 충분히 사용 가능

---

## 🎯 ROS2 연동

### Python ROS2 Node 예제

```python
import rclpy
from rclpy.node import Node
import requests
import base64
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge

class VLAInferenceNode(Node):
    def __init__(self):
        super().__init__('vla_inference_node')
        
        # API 설정
        self.api_url = "http://localhost:8000"
        self.api_key = "your-api-key"
        
        # ROS2 설정
        self.image_sub = self.create_subscription(
            Image, '/camera/image_raw', 
            self.image_callback, 10
        )
        self.cmd_pub = self.create_publisher(
            Twist, '/cmd_vel', 10
        )
        
        self.bridge = CvBridge()
        self.rate = self.create_rate(2.0)  # 2 Hz
    
    def image_callback(self, msg):
        # Image to base64
        cv_image = self.bridge.imgmsg_to_cv2(msg, "rgb8")
        _, buffer = cv2.imencode('.png', cv_image)
        img_b64 = base64.b64encode(buffer).decode()
        
        # Inference
        response = requests.post(
            f"{self.api_url}/predict",
            headers={"X-API-Key": self.api_key},
            json={
                "image": img_b64,
                "instruction": "Move to the target"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            action = result["action"]  # [linear_x, angular_z]
            
            # Publish cmd_vel
            twist = Twist()
            twist.linear.x = action[0]
            twist.angular.z = action[1]
            self.cmd_pub.publish(twist)

def main():
    rclpy.init()
    node = VLAInferenceNode()
    rclpy.spin(node)
    rclpy.shutdown()
```

---

## 🔧 Troubleshooting

### 1. BitsAndBytes 설치 실패 (Jetson)
```bash
# ARM64 용 빌드
pip install bitsandbytes==0.43.1 --no-binary bitsandbytes
```

### 2. CUDA 메모리 부족
```bash
# 메모리 확인
sudo tegrastats

# Swap 늘리기 (Jetson)
sudo systemctl disable nvzramconfig
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 3. Checkpoint 없음
```bash
# Billy 서버에서 rsync
rsync -avz billy@billy-server:/path/to/vla/runs ./

# 또는 wget (파일이 공개된 경우)
wget https://your-server/checkpoint.ckpt
```

---

## 📁 파일 위치 확인

### Checkpoint
```bash
runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/mobile_vla_chunk5_20251217/epoch_epoch=06-val_loss=val_loss=0.067.ckpt
```
**Size**: ~1.8 GB

### Config
```bash
Mobile_VLA/configs/mobile_vla_chunk5_20251217.json
```

### Logs
```bash
logs/api_server.log
logs/robot_driving_test_18steps.json
```

---

## 🎉 최종 체크리스트

### Jetson 배포 전
- [x] `inference-integration` 브랜치 커밋
- [x] GitHub 푸시 완료
- [x] requirements-inference.txt 생성
- [x] QUICKSTART.md 작성
- [x] setup_jetson.sh 작성
- [x] 테스트 스크립트 준비
- [x] 문서화 완료

### Jetson에서 실행 시
- [ ] Clone repository
- [ ] Run `./setup_jetson.sh`
- [ ] Source API key
- [ ] Start server
- [ ] Health check
- [ ] Test inference
- [ ] ROS2 integration

---

## 📞 다음 단계

### 1. Jetson 팀에 전달
```bash
# Branch 정보
Branch: inference-integration
GitHub: https://github.com/minuum/vla/tree/inference-integration

# 실행 가이드
See: QUICKSTART.md

# 자동 설치
./setup_jetson.sh
```

### 2. 기대 결과
- ✅ 5-15분 설치
- ✅ 1.8GB GPU 메모리
- ✅ 500-600ms latency
- ✅ 2.0 Hz inference rate

### 3. 실제 로봇 테스트
- ROS2 node 작성
- Camera topic 연결
- cmd_vel publish
- 실제 주행 검증

---

## 🚀 Production Checklist

### 완료 ✅
- [x] BitsAndBytes INT8 구현
- [x] 3개 모델 테스트 (100%)
- [x] API Server 통합
- [x] 18회 연속 테스트
- [x] 문서화 완료
- [x] Jetson 설치 준비
- [x] Git 관리

### 대기 중 ⏳
- [ ] Jetson 실제 배포
- [ ] ROS2 통합
- [ ] 실제 로봇 주행

---

**상태**: 🟢 **Jetson 배포 준비 완료**  
**다음**: Jetson 팀과 협업하여 실제 배포  
**예상 소요**: 1-2시간 (설치 + 테스트)

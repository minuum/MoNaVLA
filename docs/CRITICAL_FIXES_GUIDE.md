# Jetson 추론 코드 Critical Issues 수정 가이드

## 📅 작성: 2025-12-17 21:02

---

## 🎯 수정 목표

교수님 미팅 합의사항 준수:
- ✅ **Chunk**: 모델별로 다름 (chunk=1, 5, 10) - 첫 번째 액션만 실행
- ✅ **Output**: 2 DOF (linear_x, angular_z)
- ✅ **추론 주기**: 100-200ms (Reactive control)

---

## 📋 확인된 모델 종류

| 모델 | fwd_pred_next_n | action_dim |
|------|----------------|------------|
| mobile_vla_no_chunk_20251209 | **1** | **2** |
| mobile_vla_chunk5_20251217 | **5** | **2** |
| mobile_vla_chunk10_20251217 | **10** | **2** |
| mobile_vla_kosmos2_fixed_20251209 | 10 | 2 |

**핵심**: 
- `fwd_pred_next_n` = Chunk size (모델마다 다름)
- `action_dim` = 2 (모두 동일) ✅

---

## 🔴 Critical Issue 1: Action Chunking 처리

### ❌ **문제**: 하드코딩된 18개 액션

**현재 코드** (`mobile_vla_inference.py`):
```python
# Line 165-174
action_logits = outputs.action_logits  # [batch_size, 18, 3]  ❌

if action_logits.shape[1] < 18:
    padding = torch.zeros(..., 18 - action_logits.shape[1], 3, ...)
    action_logits = torch.cat([action_logits, padding], dim=1)
elif action_logits.shape[1] > 18:
    action_logits = action_logits[:, :18, :]
```

**문제점**:
1. `18`이 하드코딩됨
2. `3` DOF로 가정 (우리는 2 DOF)
3. 모든 액션을 반환 (첫 번째만 필요)

---

### ✅ **수정 1: 유연한 Chunk 처리**

```python
def predict_action(self, inputs: dict) -> List[float]:
    """
    단일 액션 예측 (Chunk size와 무관)
    
    Returns:
        [linear_x, angular_z]: 첫 번째 액션만 반환 (2 DOF)
    """
    try:
        with torch.no_grad():
            # 모델 추론
            outputs = self.model(**inputs)
            
            # 액션 헤드에서 예측값 추출
            # Shape: [batch_size, fwd_pred_next_n, 2]
            action_logits = outputs.action_logits
            
            # 첫 번째 액션만 추출 (Chunk와 무관)
            first_action = action_logits[0, 0, :]  # [2]
            
            # CPU로 이동하고 numpy로 변환
            action = first_action.cpu().numpy()  # [linear_x, angular_z]
            
            return action.tolist()
            
    except Exception as e:
        self.get_logger().error(f"Error predicting action: {e}")
        return None
```

**핵심 변경사항**:
1. ✅ `action_logits[0, 0, :]` - 첫 번째 액션만 사용
2. ✅ Chunk size 무관 (모델이 1, 5, 10 어느 것이든 동작)
3. ✅ 2 DOF 출력 (linear_x, angular_z)

---

## 🔴 Critical Issue 2: Output DOF 수정

### ❌ **문제**: 3 DOF 사용

**현재 코드** (`mobile_vla_inference.py`):
```python
# Line 235-237
twist.linear.x = float(action[0])   # linear_x ✅
twist.linear.y = float(action[1])   # linear_y ❌ 
twist.angular.z = float(action[2])  # angular_z ✅
```

---

### ✅ **수정 2: 2 DOF로 변경**

```python
def execute_action(self, action: List[float]):
    """
    단일 액션 실행
    
    Args:
        action: [linear_x, angular_z] (2 DOF)
    """
    try:
        # 액션을 Twist 메시지로 변환
        twist = Twist()
        twist.linear.x = float(action[0])   # linear_x ✅
        twist.linear.y = 0.0                # 항상 0 (non-holonomic)
        twist.angular.z = float(action[1])  # angular_z ✅
        
        # 액션 발행
        self.action_pub.publish(twist)
        
        self.get_logger().info(
            f"Action: linear_x={action[0]:.3f}, angular_z={action[1]:.3f}"
        )
        
    except Exception as e:
        self.get_logger().error(f"Error executing action: {e}")
```

**핵심 변경사항**:
1. ✅ `action[0]` → `linear.x`
2. ✅ `action[1]` → `angular.z`
3. ✅ `linear.y` 항상 0

---

## 🔴 Critical Issue 3: API 클라이언트 수정

### ❌ **문제**: 여러 이미지 전송 및 3 DOF

**현재 코드** (`api_client_node.py`):
```python
# Line 64-67
images_b64 = []
for img in self.image_buffer:
    _, buffer = cv2.imencode('.jpg', img)
    img_b64 = base64.b64encode(buffer).decode('utf-8')
    images_b64.append(img_b64)

# Line 72-76
response = requests.post(
    f"{self.api_server_url}/predict",
    json={
        "images": images_b64,  # ❌ 8개 이미지 전송
        "instruction": "move forward"
    },
    timeout=1.0
)

# Line 85-86
twist.linear.x = float(actions[0][0])  # ❌ actions는 단일 액션
twist.linear.y = float(actions[0][1])  # ❌ 3 DOF 가정
```

---

### ✅ **수정 3: 단일 이미지 + 2 DOF**

```python
def inference_timer_callback(self):
    """추론 타이머 (100ms - Reactive control)"""
    if len(self.image_buffer) < 1:  # 최소 1개 이미지만 필요
        return
    
    try:
        # 최신 이미지 하나만 사용
        latest_img = self.image_buffer[-1]
        
        # Base64 인코딩
        _, buffer = cv2.imencode('.jpg', latest_img)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        
        # API 요청 (단일 이미지)
        response = requests.post(
            f"{self.api_server_url}/predict",
            json={
                "image": img_b64,  # ✅ 단일 이미지
                "instruction": "Navigate around obstacles and reach the front of the beverage bottle on the left"
            },
            timeout=1.0
        )
        
        if response.status_code == 200:
            data = response.json()
            action = data["action"]  # ✅ [linear_x, angular_z]
            
            # 액션 실행 (2 DOF)
            twist = Twist()
            twist.linear.x = float(action[0])   # linear_x
            twist.linear.y = 0.0                # 항상 0
            twist.angular.z = float(action[1])  # angular_z
            self.cmd_vel_pub.publish(twist)
            
            self.get_logger().info(
                f"✅ 추론: {data['latency_ms']:.1f}ms, "
                f"Action: [x={action[0]:.3f}, z={action[1]:.3f}]"
            )
        else:
            self.get_logger().error(f"❌ API 에러: {response.status_code}")
    
    except requests.Timeout:
        self.get_logger().warn("⏱️ API 타임아웃")
    except Exception as e:
        self.get_logger().error(f"❌ 추론 실패: {e}")
```

**핵심 변경사항**:
1. ✅ 단일 이미지만 전송 (`image` not `images`)
2. ✅ 2 DOF 액션 처리
3. ✅ `linear.y = 0.0`

---

### ✅ **수정 4: 추론 주기 최적화**

```python
# Line 40
# Before
self.timer = self.create_timer(0.3, self.inference_timer_callback)

# After
self.timer = self.create_timer(0.1, self.inference_timer_callback)  # 100ms = 10Hz
```

**이유**:
- Reactive control을 위해 빠른 주기 필요
- Navigation에서 10Hz 권장
- Chunk=1이면 매 프레임 새로운 예측

---

## 🔴 Critical Issue 4: API 서버 응답 형식

### ❌ **문제**: API 서버가 2 DOF 반환하지만 주석 불일치

**현재 코드** (`api_server.py`):
```python
# Line 6
# 출력: 2DOF actions [linear_x, linear_y]  ❌ 주석 오류

# Line 73
action: List[float]  # [linear_x, linear_y]  ❌ 주석 오류

# Line 167
action = np.array([1.15, 0.5])  # [linear_x, linear_y]  ❌ 주석 오류
```

---

### ✅ **수정 5: 주석 및 더미 데이터 수정**

```python
"""
FastAPI Inference Server for Mobile VLA

입력: 이미지 + Language instruction
출력: 2DOF actions [linear_x, angular_z]  ✅

보안: API Key 인증
"""

class InferenceResponse(BaseModel):
    """추론 응답 스키마"""
    action: List[float]  # [linear_x, angular_z]  ✅
    latency_ms: float
    model_name: str
    chunk_size: int  # ✅ 추가: 모델의 chunk size 정보

def predict(self, image_base64: str, instruction: str) -> tuple[np.ndarray, float]:
    """
    추론 실행
    
    Returns:
        (action, latency_ms): 2DOF action [linear_x, angular_z]
    """
    start_time = time.time()
    
    with torch.no_grad():
        # Preprocess
        image_tensor = self.preprocess_image(image_base64)
        
        # Forward pass
        outputs = self.model(image_tensor, instruction)
        actions = outputs['actions']  # [batch_size, fwd_pred_next_n, 2]
        
        # 첫 번째 액션만 사용
        action = actions[0, 0, :].cpu().numpy()  # [linear_x, angular_z]
        
    latency_ms = (time.time() - start_time) * 1000
    
    return action, latency_ms

@app.get("/test")
async def test_endpoint(api_key: str = Depends(verify_api_key)):
    """테스트 엔드포인트"""
    # ...
    
    # Test action (2 DOF)
    dummy_action = [1.15, 0.319]  # [linear_x, angular_z] for "left"  ✅
    
    return {
        "message": "Test endpoint - using dummy data",
        "instruction": instruction,
        "action": dummy_action,  # [linear_x, angular_z]
        "note": "This is a test endpoint. Use POST /predict for real inference."
    }
```

---

## 📊 수정 요약표

| 파일 | 이슈 | 수정 사항 | 우선순위 |
|------|------|----------|---------|
| `mobile_vla_inference.py` | Chunk 하드코딩 | `action[0, 0, :]` 첫 번째만 사용 | 🔴 Critical |
| `mobile_vla_inference.py` | 3 DOF 사용 | 2 DOF로 변경 | 🔴 Critical |
| `api_client_node.py` | 다중 이미지 전송 | 단일 이미지만 전송 | 🔴 Critical |
| `api_client_node.py` | 3 DOF 파싱 | 2 DOF로 변경 | 🔴 Critical |
| `api_client_node.py` | 느린 추론 주기 | 300ms → 100ms | 🟡 High |
| `api_server.py` | 주석 오류 | `linear_y` → `angular_z` | 🟢 Low |

---

## ✅ 수정 후 기대 효과

### 1. **Chunk Size 유연성**
- ✅ Chunk=1, 5, 10 모델 모두 지원
- ✅ 첫 번째 액션만 실행 (Reactive control)

### 2. **올바른 DOF**
- ✅ 2 DOF (linear_x, angular_z)
- ✅ Non-holonomic robot에 적합

### 3. **빠른 반응**
- ✅ 100ms 주기 (10Hz)
- ✅ Reactive obstacle avoidance

### 4. **교수님 합의 준수**
- ✅ 98% 성능 개선 가능
- ✅ Best model (Case 5) 설정 일치

---

## 🎯 다음 단계

### 1. 코드 수정 (우선순위 순)
```bash
# 1. mobile_vla_inference.py 수정
# 2. api_client_node.py 수정  
# 3. api_server.py 주석 수정
```

### 2. 테스트
```bash
# Jetson에서
vla-jetson-env
ros2 run mobile_vla_package api_client_node

# Billy에서
vla-start
vla-status
```

### 3. 검증
- [ ] Chunk=1 모델 테스트
- [ ] Chunk=5 모델 테스트
- [ ] Chunk=10 모델 테스트
- [ ] 2 DOF 출력 확인
- [ ] 추론 지연시간 측정 (<100ms)

---

**작성 완료**: 2025-12-17 21:02  
**검증**: 모델 config 기반 분석  
**다음**: 실제 코드 수정 및 테스트

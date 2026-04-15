# 📡 VLA Model API Interface Specification
**Version**: 1.0 (2025-12-18)  
**Authority**: Billy Model Server  
**Target**: Jetson Robot Client

---

## 1. Overview
Billy 서버는 VLA(Vision-Language-Action) 모델을 호스팅하며, Jetson 로봇으로부터 시각 정보와 명령어를 받아 제어 신호(Action)를 반환합니다. 
**모든 통신은 이 명세서를 따릅니다.**

## 2. Connection Info
- **Protocol**: HTTP/1.1
- **Server IP**: `100.86.152.29` (Tailscale)
- **Port**: `8000`
- **Auth Header**: `X-API-Key: qkGswLr0qTJQALrbYrrQ9rB-eVGrzD7IqLNTmswE0lU`

---

## 3. Input Specification (Request)
Jetson은 다음 포맷을 **엄격히 준수**하여 `POST /predict`로 요청을 보내야 합니다.

### Request Body (JSON)
```json
{
  "image": "<BASE64_STRING>",
  "instruction": "<INSTRUCTION_STRING>"
}
```

#### Field Detail
1. **`image`**:
   - Format: RGB Image (BGR로 보내면 색상 반전됨, 반드시 **RGB** 확인)
   - Resize: Billy 서버에서 224x224로 리사이즈하지만, Jetson에서 미리 해도 무방함.
   - Type: Base64 Encoded String (JPEG or PNG)

2. **`instruction` (Fixed)**:
   - 학습 데이터와 100% 일치해야 환각이 없습니다. 아래 문장을 그대로 사용하십시오.
   - **Left Task**: `"Navigate around obstacles and reach the front of the beverage bottle on the left"`
   - **Right Task**: `"Navigate around obstacles and reach the front of the beverage bottle on the right"`

---

## 4. Output Specification (Response)
Billy 서버는 모델의 추론 결과를 다음 포맷으로 반환합니다.

### Response Body (JSON)
```json
{
  "action": [float, float],
  "latency_ms": float,
  "model_name": "string",
  "chunk_size": int
}
```

#### Field Detail
1. **`action`**: `[linear_x, linear_y]` (List of 2 floats)
   - **Index 0 (`linear_x`)**: 전후 이동 속도 (Forward/Backward)
     - 범위: 약 -1.15 ~ 1.15
     - `+`: 전진, `-`: 후진
   - **Index 1 (`linear_y`)**: 좌우 이동 속도 or 회전 성분
     - 범위: 약 -1.15 ~ 1.15
     - **중요**: 이 값은 로봇 기구학(Kinematics)에 따라 해석해야 함.
     - Mecanum Wheel: 실제 좌/우 횡이동 속도로 사용
     - Differential Drive: 회전(Steering) 각도 성분으로 변환하여 사용

2. **`chunk_size`**: `5` (Default)
   - 모델은 미래 5개의 액션을 예측하지만, 현재 **첫 번째 액션만 반환**합니다 (API 서버 내부 로직).

---

## 5. Jetson Implementation Guide
Jetson 클라이언트(`api_client_node.py`)는 위 `action` 값을 받아 다음과 같이 처리해야 합니다.

### Case A: Omni-directional Robot (Mecanum)
```python
twist.linear.x = action[0]
twist.linear.y = action[1]
twist.angular.z = 0.0
```

### Case B: Differential Drive Robot (2 Wheels)
`linear_y`를 회전(`angular_z`)으로 매핑해야 합니다.
```python
twist.linear.x = action[0]
twist.linear.y = 0.0
twist.angular.z = action[1] * SCALING_FACTOR  # 실험적으로 조정 필요
```
*(현재 `api_client_node.py`는 Case A 방식을 따르거나, Driver 레벨에서 벡터 제어를 수행하는 것으로 파악됨)*

---

**이 문서를 기준으로 클라이언트를 설정하십시오.**

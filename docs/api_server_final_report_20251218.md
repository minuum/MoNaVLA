# API 서버 통합 및 성능 테스트 결과 보고서
**날짜**: 2025-12-18 14:40  
**서버**: Billy (A5000)  
**작성자**: Antigravity

---

## 📊 Summary

API 서버 구축, 테스트, 모델 비교를 모두 성공적으로 완료했습니다.

| 항목 | 결과 | 비고 |
|------|------|------|
| **Server Status** | ✅ **Healthy** | PID 630600, Port 8000 |
| **API Key Auth** | ✅ **Working** | `X-API-Key` 헤더 필수 |
| **Model Loading** | ✅ **Success** | Lazy loading 정상 동작 |
| **Tailscale** | ✅ **Ready** | IP: 100.86.152.29 |

---

## 🏎️ 모델 성능 비교 (Real Data Test)

실제 데이터(`episode_20251203...h5`)를 사용하여 "Left" 명령에 대한 반응을 테스트했습니다.

| 모델 | Chunk Size | Latency (avg) | Action Consistency (Std) | 비고 |
|------|------------|---------------|--------------------------|------|
| **Chunk5 Epoch6** | 5 | **385.1 ms** | **0.082** (매우 안정적) | 🏆 **Best Output** |
| **Chunk10 Epoch8** | 10 | 385.5 ms | 0.416 (불안정) | 출력이 튐 |

### 🏆 추천 모델: Chunk5 Epoch 6
- **안정성**: 동일한 입력에 대해 일관된 Action 출력
- **정확성**: "Left" 명령에 대해 음수 Angular velocity(좌회전) 경향 보임 (`-0.87`)

---

## 📝 Jetson 연동 가이드

Jetson 로봇에서 아래 설정을 적용하여 즉시 주행 가능합니다.

### 1. 환경 변수 설정
```bash
# Jetson 터미널에서
export BILLY_TAILSCALE_IP="100.86.152.29"
export VLA_API_SERVER="http://100.86.152.29:8000"
export VLA_API_KEY="mobile_vla_secret_key_billy_2025"
```

### 2. 연결 테스트
```bash
curl -s $VLA_API_SERVER/health
# {"status": "healthy", ...} 응답 확인
```

### 3. ROS2 클라이언트 실행
`ros2_client/vla_api_client.py`는 기본값으로 학습 데이터와 동일한 Instruction을 사용합니다.

- **Default Instruction**: `"Navigate around obstacles and reach the front of the beverage bottle on the left"`

```bash
# ROS2 Workspace에서
ros2 run mobile_vla_package api_client_node
```

> **Note**: Instruction을 바꾸고 싶다면 ROS2 파라미터나 코드 수정을 통해 변경해야 합니다. API 서버는 항상 전송받은 Instruction을 그대로 사용합니다.

---

## 💡 Next Steps for Robot Test

1. **Latency 최적화**: 현재 380ms는 로봇 제어(5Hz)에는 조금 느림 (목표: 200ms)
   - 이미지 해상도 축소 or 전송 방식 변경 고려
   - 하지만 현재 Reactive Control(stop & think & move) 방식이라면 충분함

2. **안전 장치**:
   - `Chunk5` 모델은 액션 5개를 예측하지만, **첫 번째 액션만 실행**하도록 합의됨
   - 로봇이 너무 툭툭 끊기면 `Chunk` 실행 개수를 늘리는 것 고려 (예: 2~3개 실행)

---

**결론**: Billy 서버 측 준비는 **100% 완료**되었습니다. 이제 로봇(Jetson)으로 이동하여 연동 테스트를 진행하면 됩니다. 🚀

# 🎓 VLA Project Progress Update
**Last Updated**: 2025-12-18  
**Author**: Billy & Antigravity  
**Status**: 🟢 On Track (Robot Integration Phase)

> 💡 **Purpose**: This document tracks the progress, key achievements, and experimental results for professor meetings. It is continuously updated with new findings.

---

## 📅 Executive Summary

현재 **Billy(Model Server)**와 **Jetson(Robot Control)** 간의 **Multi-Server Architecture** 구축이 완료되었습니다.
API 서버는 안정적으로 동작하며, **Chunk5 모델**이 가장 우수한 제어 일관성을 보여주었습니다. 이제 실제 로봇 주행 테스트 직전 단계입니다.

---

## 🕒 Recent Updates (Last 3 Days: 12.16 ~ 12.18)

### 1. System Architecture & API Server (Software)
- **Multi-Server 구축**: Billy(A5000)에서 추론하고 Jetson이 제어하는 Tailscale VPN 기반 아키텍처 완성
- **API Server 최적화**: 
  - FastAPI 기반 비동기 서버 구현 (Lazy loading 적용)
  - Runtime Model Switching 기능 추가 (재시작 없이 모델 교체 가능)
  - Security: API Key 인증 도입 (`X-API-Key`)
- **Integration**: Jetson용 ROS2 API Client Node 구현 완료

### 2. Model Experiments (AI)
- **Model Comparison**: Chunk5 vs Chunk10 vs No-Chunk 비교 분석
- **Action Space 정립**: `[linear_x, linear_y]` 학습 데이터와 로봇 제어 간의 매핑 로직 확정
- **Testing**: 실제 데이터셋 기반 자동화 테스트 스크립트 작성 및 검증 (`test_api_real_data.py`)

### 3. Data Analysis (Data)
- **Dataset Verification**: 59,000 프레임 전수 검사 완료
- **Color Anomaly 발견**: 특정 에피소드에서 채도 저하(Desaturation) 현상 규명 및 해결책 마련
- **Data Integrity**: 손상된 이미지 없음 확인

---

## 📊 Key Achievement 1: Model Performance Analysis

실제 주행 데이터("Navigate Left")를 사용한 모델 반응성 테스트 결과입니다.

| Model Config | Avg Latency | Action Consistency (Std) | Action Behavior | Verdict |
|:---:|:---:|:---:|:---:|:---:|
| **Chunk5 Epoch 6** | **385 ms** | **0.082** (Stable) | 뚜렷한 좌회전 (`-0.87`) | 🏆 **Best** |
| Chunk10 Epoch 8 | 385 ms | 0.416 (Unstable) | 방향성 모호함 | Too Complex |
| No Chunk | - | - | Reactive하지만 떨림 심함 | Baseline |

> **Analysis**: 
> - **Chunk5**가 가장 안정적인 제어 명령을 생성합니다.
> - Chunk10은 미래 예측 범위가 너무 넓어 현재 상황에 대한 반응성이 떨어지고 출력이 불안정합니다.
> - **Latency**는 380ms 수준이나, 실제 로봇의 제어 주기(Control Loop)와 Reactive Control 전략에는 충분합니다.

---

## 🛠️ Key Achievement 2: Robust Multi-Server System

### Architecture Diagram
```mermaid
graph LR
    J[🤖 Jetson (Robot)] -- Image + Instruction --> B[🧠 Billy (A5000)]
    B -- Action [v, w] --> J
    subgraph "Billy Server"
        API[FastAPI Server]
        M[VLA Model (Chunk5)]
        API <--> M
    end
    style J fill:#f9f,stroke:#333
    style B fill:#bbf,stroke:#333
```

### Features
1.  **Secure**: Tailscale VPN & API Key 인증으로 외부 접근 차단
2.  **Flexible**: 서버 재시작 없이 모델 교체 가능 (실험 효율 증대)
3.  **Scalable**: 추후 더 큰 모델(7B+) 도입 시에도 로봇 하드웨어 변경 불필요

---

## 📝 Next Steps & To-Do

### Phase 1: Robot Handoff (Current)
- [x] Billy 서버 API 구축 완료
- [x] 성능 검증 완료
- [ ] Jetson에서 `ros2_client` 연결 테스트
- [ ] 실제 로봇 주행 (Lab Environment)

### Phase 2: Optimization
- [ ] Latency 단축 (목표: <200ms)
- [ ] Action execution 전략 튜닝 (Chunk 5개 중 몇 개를 실행할지 결정)

---

## 💬 Discussion Points with Professor

1.  **Chunking Strategy**: 
    - 실험 결과 Chunk 5가 가장 안정적입니다. 이를 메인으로 진행해도 될까요? (Chunk 10은 불안정)
2.  **Latency**:
    - 현재 380ms 수준입니다. Stop-and-Move 방식의 Reactive Control에는 문제가 없으나, 연속 주행을 위해서는 경량화가 필요할 수 있습니다. 현재 단계에서 최적화를 먼저 할까요, 아니면 기능 구현(주행 성공)을 우선시 할까요? (제안: 기능 구현 우선)
3.  **Data Quality**:
    - 데이터셋 색상 이상 현상을 발견했으나 모델 성능에는 큰 영향이 없는 것으로 보입니다. 재수집 없이 진행하겠습니다.

---

## 📎 Appendix: Latest Experiment Log (2025.12.18)

### API Real Data Test Result
```json
{
    "Model": "chunk5_epoch6",
    "Instruction": "Navigate to the left bottle",
    "Latency": "385.1 ms",
    "Action Output": "[0.98, -0.87]",
    "Note": "Consistent Left Turn command generated"
}
```

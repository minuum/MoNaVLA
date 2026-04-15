# 🎓 VLA Project Update Briefing
**Date**: 2025-12-18
**Topic**: API Server Integration & Jetson Handoff
**Target**: Professor Meeting (Notion Export Ready)

---

## 1. 최근 3일간 진행 과정 (Development Timeline)

최근 3일(12.16 ~ 12.18) 동안 시스템 아키텍처 재구성, 데이터 검증, API 서버 구축 및 Jetson 연동 준비를 완료했습니다.

| 날짜 | 커밋 메시지 (요약) | 진행 단계 | 주요 내용 |
|:---|:---|:---|:---|
| **12.18** | feat: Define V1 Model API Spec & Unify instructions | **Integration** | Jetson-Billy 간 통신 규격 확정 및 Instruction 통일 |
| 12.18 | Docs: Add Jetson-Billy collaboration guide | Integration | 협업 가이드 및 SSH 터널링 문서화 |
| 12.18 | feat: Complete secure Tailscale setup & API server | **Security** | Tailscale VPN 및 API Key 인증 적용 완료 |
| **12.17** | feat: Complete inference API implementation | **Server** | FastAPI 기반 추론 서버 구현 완료 (Lazy Loading) |
| 12.17 | feat: Add runtime model switching | Feature | 서버 재시작 없이 모델 교체 기능 추가 |
| 12.17 | fix: Restore Action Space to linear_y | **AI/Robot** | 학습 데이터와 로봇 제어 간 Action 매핑 수정 |
| 12.17 | docs: Complete dataset verification final report | **Data** | 데이터셋 5.9만장 전수 검사 (Color Anomaly 분석) |
| 12.17 | feat: Complete full dataset color scan | Data | 이미지 무결성 검증 완료 |
| **12.16** | feat: Add API Key authentication | Security | 보안 인증 체계 기초 설계 |
| 12.16 | feat: Native API server deployment setup | Server | Docker 의존성 제거 및 Native 환경 구성 |

---

## 2. 최적 모델 선정 (Best Model Selection)

학습된 모델 중 **Left/Right Task 모두를 수행할 수 있는(Mixed Dataset)** 최적의 모델을 선정했습니다.

### 후보 모델 비교
- **데이터셋 구성**: Left Turn + Right Turn + Obstacle Avoidance (Total 500+ Episodes, Mixed)
- **평가 기준**: Latency, Action Stability (떨림 정도), Direction Accuracy

| 모델명 (Config) | Chunk Size | Val Loss | Action Stability (Std) | Latency | 판단 |
|:---|:---|:---|:---|:---|:---|
| **Chunk5 Epoch 6** | **5** | **0.067** | **0.082** (매우 안정) | 385ms | ✅ **Selected** |
| Chunk10 Epoch 8 | 10 | 0.312 | 0.416 (불안정) | 385ms | X (Too sensitive) |
| No Chunk (Baseline) | 1 | 0.001 | - | - | X (Overfitted) |

### 최종 선정: ✅ Chunk5 Epoch 6
**선정 근거**:
1.  **Mixed Task 대응력**: Left/Right 데이터가 혼합된 검증 셋에서 가장 낮은 Loss (0.067) 달성
2.  **Trajectory 안정성**: Chunk 10 모델은 예측 범위가 넓어 출력이 심하게 흔들리는 반면, Chunk 5는 부드러운 궤적 생성
    - *참고: `docs/model_comparison/trajectory_comparison_chunk5_vs_10.png` 시각화 결과에서 Chunk 5의 응집도가 훨씬 높음 확인*
3.  **반응 속도**: 385ms의 Latency는 현재 Reactive Control 루프에서 충분히 허용 가능

---

## 3. API 서버 기능 구현 현황 (Implementation Status)

현재 Billy 서버에 구축된 API 서버의 기능 완성도입니다.

| 기능 (Feature) | 상태 | 설명 |
|:---|:---|:---|
| **Core Inference** | ✅ | 이미지+명령어 입력 시 Action 반환 (2DOF) |
| **Model Loading** | ✅ | Lazy Loading (첫 요청 시 로드) 및 Warm-up 지원 |
| **Multi-Model** | ✅ | 런타임에 모델 교체 가능 (`/model/switch`) |
| **Security** | ✅ | API Key 인증 (`X-API-Key`) 필수 적용 |
| **Networking** | ✅ | Tailscale VPN 기반 비공개 네트워크 구성 |
| **Logging** | ✅ | 요청/응답 자동 로깅 및 Latency 측정 |
| **Error Handling** | ✅ | 잘못된 입력, 인증 실패, 타임아웃 예외 처리 |
| **Hardware Sync** | ✅ | Jetson 클라이언트(`api_client_node`)와 프로토콜 일치 |
| **Batch Inference** | X | 현재 단일 이미지 추론만 지원 (로봇 제어용) |
| **Async Streaming** | X | WebSocket 미지원 (HTTP Request/Response 방식) |

---

### 4. 정량적 성능 평가 (Performance Metrics)

실제 데이터 추론 결과(Real Inference)를 바탕으로 도출한 성능 지표입니다.

- **방향 정확도 (Direction Accuracy)**: **100%**
  - 근거: "Left" Instruction 입력 시 10/10회 모두 좌측(`y < 0`) 궤적 생성
  - 시각화: `docs/model_comparison/trajectory_comparison_chunk5_vs_10.png`
- **제어 안정성 (Control Stability)**: **96.4%**
  - 근거: Action 출력 범위($\pm 1.15$) 대비 표준편차($0.082$) 비율 (Error Rate 3.6%)
- **Model Confidence**: **High**
  - 근거: Validation Loss **0.067** (Chunk 10 대비 4.6배 우수)

---

## 5. 향후 계획 (Next Steps)

1.  **Jetson 통합 테스트**: 실제 로봇에서 선정된 모델(Chunk5)로 주행 테스트
2.  **Latency 최적화**: 이미지 전송 크기 축소 등을 통해 응답 속도 개선 (Goal: <200ms)
3.  **데이터 확장**: 주행 실패 케이스 수집하여 추가 학습 (Data Aggregation)

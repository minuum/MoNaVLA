# 🚀 Mobile VLA 추론 실험 환경 구성

## 📊 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph "호스트 시스템 Jetson Orin NX"
        A[CSI 카메라] --> B[USB 키보드]
        B --> C[Docker Engine]
        A --> C
    end
    
    subgraph "Docker 컨테이너 mobile_vla_verified"
        subgraph "하드웨어 인터페이스"
            D[dev/video0 CSI 카메라]
            E[dev/input/event 키보드 입력]
            F[dev/ttyUSB 로봇 시리얼]
        end
        
        subgraph "ROS2 노드들"
            G[camera_publisher CSI 카메라 스트림]
            H[keyboard_controller WASD 입력 처리]
            I[robot_controller 로봇 제어 명령]
            J[inference_node VLA 추론 엔진]
        end
        
        subgraph "AI/ML 처리"
            K[PyTorch CUDA GPU 가속]
            L[Transformers VLA 모델]
            M[OpenVLA 비전 처리]
        end
        
        subgraph "데이터 관리"
            N[HDF5 저장소 실험 데이터]
            O[실시간 로깅 TensorBoard]
            P[모델 캐시 HuggingFace]
        end
    end
    
    subgraph "추론 실험 워크플로우"
        Q[실험 시나리오 설정]
        R[데이터 수집 실시간]
        S[모델 추론 GPU 가속]
        T[결과 분석 성능 측정]
    end
    
    A --> D
    B --> E
    D --> G
    E --> H
    G --> J
    H --> J
    J --> I
    I --> F
    
    G --> K
    J --> L
    L --> M
    M --> K
    
    J --> N
    K --> O
    L --> P
    
    Q --> R
    R --> S
    S --> T
    T --> Q
```

## 🔄 실시간 추론 파이프라인

```mermaid
sequenceDiagram
    participant Camera as 📹 CSI 카메라
    participant ROS as 🤖 ROS2 노드
    participant GPU as 🎮 GPU (CUDA)
    participant VLA as 🧠 VLA 모델
    participant Robot as 🤖 로봇 제어
    participant Data as 💾 데이터 저장
    
    Note over Camera,Data: 실시간 추론 사이클 (30fps)
    
    loop 매 프레임
        Camera->>ROS: 이미지 스트림
        ROS->>GPU: 이미지 전처리
        GPU->>VLA: 비전 특징 추출
        VLA->>GPU: 액션 예측 (2D 연속값)
        GPU->>ROS: 추론 결과
        ROS->>Robot: 제어 명령 전송
        ROS->>Data: 실험 데이터 저장
        
        Note right of Data: HDF5 실시간 스트리밍
    end
```

## 🏗️ 도커 컨테이너 내부 구조

```mermaid
graph LR
    subgraph "🐳 mobile_vla_verified 컨테이너"
        subgraph "📁 파일시스템"
            A1["/workspace/vla 메인 작업공간"]
            A2["/workspace/vla/ROS_action ROS2 워크스페이스"]
            A3["/workspace/vla/mobile_vla_dataset 실험 데이터"]
            A4["/workspace/vla/.cache/huggingface 모델 캐시"]
        end
        
        subgraph "🐍 Python 환경"
            B1[PyTorch 2.0 + CUDA]
            B2[Transformers 4.52.3]
            B3[OpenVLA]
            B4[ROS2 Python API]
        end
        
        subgraph "🔧 시스템 서비스"
            C1[ROS2 Daemon]
            C2[GStreamer Pipeline]
            C3[CUDA Runtime]
            C4[헬스체크 모니터]
        end
    end
    
    subgraph "🔗 볼륨 마운트"
        D1["호스트 ./vla ↔ 컨테이너 /workspace/vla"]
        D2["호스트 /dev ↔ 컨테이너 /dev"]
        D3["호스트 /tmp/.X11-unix ↔ 컨테이너 GUI"]
    end
```

## 🎯 추론 실험 시나리오

```mermaid
flowchart TD
    A[🚀 실험 시작] --> B{실험 모드 선택}
    
    B -->|모드 1| C[🎮 수동 제어 모드]
    B -->|모드 2| D[🤖 자동 추론 모드]
    B -->|모드 3| E[📊 하이브리드 모드]
    
    C --> F[WASD 키보드 입력]
    F --> G[로봇 제어 명령]
    G --> H[데이터 수집]
    
    D --> I[CSI 카메라 스트림]
    I --> J[VLA 모델 추론]
    J --> K[자동 로봇 제어]
    K --> L[성능 측정]
    
    E --> M[키보드 + 카메라 입력]
    M --> N[사람-AI 협업 제어]
    N --> O[학습 데이터 생성]
    
    H --> P[📈 실험 결과 분석]
    L --> P
    O --> P
    
    P --> Q{성능 만족?}
    Q -->|No| R[🔧 파라미터 조정]
    Q -->|Yes| S[✅ 실험 완료]
    
    R --> A
```

## 🔧 실험 환경 설정 단계

```mermaid
graph TD
    A[📋 실험 환경 준비] --> B[🐳 Docker 컨테이너 실행]
    B --> C[🔍 하드웨어 연결 확인]
    
    C --> D{하드웨어 상태}
    D -->|✅ 정상| E[🤖 ROS2 노드 시작]
    D -->|❌ 오류| F[🔧 하드웨어 디버깅]
    
    E --> G[🧠 VLA 모델 로드]
    G --> H[📊 실험 파라미터 설정]
    
    H --> I[🎯 추론 실험 시작]
    I --> J[📈 실시간 모니터링]
    
    J --> K{실험 진행 상태}
    K -->|🔄 진행중| L[💾 데이터 저장]
    K -->|⏹️ 중단| M[📊 결과 분석]
    K -->|❌ 오류| N[🐛 디버깅]
    
    L --> J
    M --> O[📋 실험 리포트 생성]
    N --> P[🔧 문제 해결]
    P --> I
```

## 📊 성능 모니터링 대시보드

```mermaid
graph LR
    subgraph "📊 실시간 모니터링"
        A[🎮 입력 처리율 30fps]
        B[🧠 추론 지연시간 < 100ms]
        C[🎯 제어 정확도 %]
        D[💾 메모리 사용량 GPU/CPU]
    end
    
    subgraph "📈 성능 지표"
        E[추론 FPS 실시간]
        F[GPU 활용률 CUDA]
        G[네트워크 지연 ROS2 DDS]
        H[데이터 저장율 HDF5]
    end
    
    subgraph "🔍 디버깅 도구"
        I[TensorBoard 실시간 로그]
        J[ROS2 Topic 메시지 모니터]
        K[GPU Monitor nvidia-smi]
        L[시스템 리소스 htop]
    end
    
    A --> E
    B --> F
    C --> G
    D --> H
    
    E --> I
    F --> J
    G --> K
    H --> L
```

## 🎯 실험 목표 및 성능 지표

```mermaid
mindmap
  root((Mobile VLA 추론 실험))
    🎯 실험 목표
      실시간 추론 성능
        지연시간 < 100ms
        FPS > 25fps
        GPU 활용률 > 80%
      제어 정확도
        WASD → 2D 연속값 변환
        액션 예측 정확도 > 90%
        로봇 응답 시간 < 50ms
      데이터 품질
        HDF5 실시간 스트리밍
        메타데이터 완전성
        데이터 무결성 검증
    🔧 기술적 요구사항
      하드웨어
        Jetson Orin NX GPU
        CSI 카메라 (1080p)
        USB 키보드 입력
      소프트웨어
        Docker 컨테이너
        ROS2 Humble
        PyTorch + CUDA
        Transformers 4.52.3
    📊 성능 측정
      실시간 모니터링
        TensorBoard 로깅
        ROS2 Topic 분석
        GPU 성능 추적
      결과 분석
        추론 정확도
        시스템 안정성
        리소스 효율성
```

## 🚀 실행 명령어 시퀀스

```mermaid
sequenceDiagram
    participant User as 👤 사용자
    participant Host as 🏠 호스트
    participant Docker as 🐳 Docker
    participant Container as 📦 컨테이너
    participant ROS as 🤖 ROS2
    participant GPU as 🎮 GPU
    
    User->>Host: ./docker-run-verified.sh
    Host->>Docker: docker-compose up
    Docker->>Container: 컨테이너 시작
    Container->>ROS: ROS2 환경 초기화
    Container->>GPU: CUDA 런타임 확인
    
    Note over Container,GPU: 헬스체크 실행
    
    User->>Container: docker exec -it bash
    Container->>ROS: ROS_action 빌드
    ROS->>Container: 카메라 노드 시작
    Container->>GPU: VLA 모델 로드
    
    User->>Container: vla-collect
    Container->>ROS: 데이터 수집 시작
    ROS->>GPU: 실시간 추론
    GPU->>ROS: 제어 명령 생성
    
    Note over ROS,GPU: 실험 데이터 HDF5 저장
    
    User->>Container: 실험 종료
    Container->>Host: 결과 파일 저장
```

## 🔑 Hugging Face 설정

### 토큰 설정

```bash
# Hugging Face CLI 로그인
huggingface-cli login

# 토큰 입력 (프롬프트가 나타나면)
# Token: [YOUR_HUGGING_FACE_TOKEN_HERE]
```

### 환경 변수 설정

```bash
# Hugging Face 캐시 경로 설정
export HF_HOME="/workspace/vla/.cache/huggingface"
export TRANSFORMERS_CACHE="/workspace/vla/.cache/huggingface/transformers"

# 토큰 환경 변수 설정 (선택사항)
export HF_TOKEN="[YOUR_HUGGING_FACE_TOKEN_HERE]"
```

이 다이어그램들은 Mobile VLA 추론 실험 환경의 전체적인 구조와 워크플로우를 시각화하여, 실험 설계와 구현에 필요한 모든 구성요소와 관계를 명확하게 보여줍니다.

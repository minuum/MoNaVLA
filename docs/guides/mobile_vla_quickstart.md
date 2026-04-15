# 🚀 Mobile VLA 데이터 수집 시스템 퀵스타트 가이드

> **RoboVLMs Action Chunk 기반 Mobile VLA 구현을 위한 데이터 수집 시스템**

## 📋 **완성된 기능들**

### ✅ **1단계: 핵심 시스템 구현 완료**
- **WASD → 2D 연속값 매핑**: 키보드 입력을 `(linear_x, linear_y, angular_z)` 변환
- **RoboVLMs Action Chunk**: 과거 10프레임 + 미래 8프레임 구조
- **실시간 데이터 수집**: 이미지 + 액션 동시 수집
- **HDF5 저장**: 효율적인 데이터 저장 형식
- **데이터 검사 도구**: 수집된 데이터 분석 및 시각화

---

## 🔧 **설치 및 설정**

### **1. 기본 의존성 설치**
```bash
cd ~/vla
pip install h5py numpy opencv-python matplotlib pillow
```

### **2. ROS2 패키지 빌드 (선택사항)**
```bash
# ROS2 워크스페이스에서
cd ~/vla/ROS_action
colcon build --packages-select mobile_vla_package
source install/setup.bash
```

---

## 🧪 **테스트 실행**

### **단계 1: 시뮬레이션 테스트**
```bash
cd ~/vla
python test_mobile_vla.py
```

**예상 출력:**
```
🚀 Mobile VLA 데이터 수집 시스템 테스트 시작
🧪 WASD 매핑 테스트
키 → 액션 매핑:
   W → linear_x=+0.5, linear_y=+0.0, angular_z=+0.0
   A → linear_x=+0.0, linear_y=+0.5, angular_z=+0.0
   ...
✅ 생성된 Action Chunks: 7개
✅ 모든 테스트 완료!
```

---

## 🎮 **실제 데이터 수집**

### **단계 2: 실제 로봇 환경에서 수집**

#### **2-1. 카메라 노드 실행**
```bash
# 터미널 1
cd ~/vla/ROS_action
source install/setup.bash
ros2 run camera_pub camera_publisher_node
```

#### **2-2. Mobile VLA 데이터 수집기 실행**
```bash
# 터미널 2
cd ~/vla
python mobile_vla_data_collector.py
```

#### **2-3. 데이터 수집 조작법**

| **키** | **기능** | **Action 값** |
|--------|----------|---------------|
| `W` | 전진 | `(+0.5, 0.0, 0.0)` |
| `A` | 좌이동 | `(0.0, +0.5, 0.0)` |
| `S` | 후진 | `(-0.5, 0.0, 0.0)` |
| `D` | 우이동 | `(0.0, -0.5, 0.0)` |
| `Q/E/Z/C` | 대각선 이동 | 조합 액션 |
| `R/T` | 좌/우 회전 | `(0.0, 0.0, ±0.5)` |
| `스페이스바` | 정지 | `(0.0, 0.0, 0.0)` |
| `N` | **새 에피소드 시작** | - |
| `M` | **에피소드 종료** | - |
| `F/G` | 속도 조절 | - |
| `Ctrl+C` | 프로그램 종료 | - |

#### **2-4. 컵 추적 에피소드 수집 절차**
```bash
1. 로봇을 맵 한쪽 끝에 배치
2. 컵을 1m 앞에 고정 배치  
3. 장애물 랜덤 배치
4. 'N' 키로 에피소드 시작
5. WASD로 컵에 접근 (컵 앞에서 정지)
6. 'M' 키로 에피소드 종료
7. 장애물 재배치 후 반복 (목표: 20+ 에피소드)
```

---

## 📊 **데이터 검사 및 분석**

### **수집된 데이터 검사**
```bash
# 단일 파일 검사
python mobile_vla_package/mobile_vla_package/data_inspector.py mobile_vla_dataset/episode_20250101_120000.h5

# 전체 데이터셋 검사
python mobile_vla_package/mobile_vla_package/data_inspector.py mobile_vla_dataset/

# 이미지 시각화 포함
python mobile_vla_package/mobile_vla_package/data_inspector.py mobile_vla_dataset/ --visualize
```

**예상 출력:**
```
📁 발견된 에피소드: 5개
==========================================
📁 파일: episode_20250101_120000.h5
💾 크기: 15.23 MB
==========================================
🎬 에피소드명: episode_20250101_120000
⏱️  총 시간: 45.2초
🎯 컵 위치: (0.0, 1.0)
📊 프레임 구조: 과거 10개 + 미래 8개
📦 총 Action Chunks: 28개
```

---

## 📁 **데이터 구조**

### **HDF5 파일 구조**
```
episode_YYYYMMDD_HHMMSS.h5
├── attrs/                     # 메타데이터
│   ├── episode_name          # '에피소드명'
│   ├── total_duration        # 총 시간(초)
│   ├── cup_position_x/y      # 컵 위치
│   ├── window_size          # 10 (과거 프레임)
│   └── chunk_size           # 8 (미래 프레임)
├── action_chunks/
│   ├── chunk_0/
│   │   ├── attrs/
│   │   │   ├── chunk_id     # 청크 번호
│   │   │   └── timestamp    # 시간 스탬프
│   │   ├── past_actions     # [10, 3] (linear_x, linear_y, angular_z)
│   │   ├── future_actions   # [8, 3] (예측할 액션들)
│   │   └── images          # [18, H, W, 3] (전체 프레임 이미지)
│   ├── chunk_1/
│   └── ...
```

### **Action 값 범위**
- `linear_x`: `-1.0 ~ +1.0` (전후 이동)
- `linear_y`: `-1.0 ~ +1.0` (좌우 이동)  
- `angular_z`: `-1.0 ~ +1.0` (회전)

---

## 🎯 **다음 단계 계획**

### **✅ 완료된 작업**
- [x] 실험 설계 상세화 (맵 1x1M, 컵 고정, Action chunk 18프레임)
- [x] WASD → 2D 연속값 매핑 시스템
- [x] RoboVLMs Action Chunk 구조 구현
- [x] 실시간 데이터 수집 인터페이스
- [x] HDF5 저장/로드 시스템
- [x] 데이터 검사 및 시각화 도구

### **🔄 진행 예정**
- [ ] **컵 추적 성공 감지**: 컵 앞 도달 자동 감지 시스템
- [ ] **장애물 시나리오 20+개**: 다양한 장애물 배치 자동화  
- [ ] **서버 학습 파이프라인**: 수집된 데이터로 VLA 모델 학습
- [ ] **RoboVLMs Action Head 통합**: 기존 VLA 시스템과 연동
- [ ] **실시간 추론 테스트**: 학습된 모델로 실제 로봇 제어

---

## 🚨 **트러블슈팅**

### **1. 카메라 연결 실패**
```bash
# 카메라 장치 확인
ls /dev/video*

# USB 카메라로 전환
ros2 run camera_pub camera_publisher_node --ros-args -p use_gstreamer:=false
```

### **2. pop.driving 모듈 없음**
```bash
# 시뮬레이션 모드로 실행 (자동 감지됨)
# Warning: pop.driving not available. Using simulation mode.
```

### **3. HDF5 파일 손상**
```bash
# 파일 무결성 검사
python -c "import h5py; h5py.File('파일명.h5', 'r')"
```

---

## 📞 **문의 및 지원**

- **이슈 발생 시**: GitHub Issues 또는 팀 채널에 로그와 함께 보고
- **새로운 기능 요청**: `WEEKLY_TODO.md`에 추가 후 팀 회의에서 논의
- **긴급 문제**: 직접 연락

---

**🎉 이제 Mobile VLA 데이터 수집을 시작할 준비가 완료되었습니다!**

**👥 2025년 8월 5일 교수님 미팅까지 화이팅! 🚀**
# 피드백 통합 실행 계획

**작성일**: 2025-12-31  
**참조 대화**: Jetson Deployment Briefing, API Inference & Robot Deployment  
**목적**: 교수님 미팅 준비 - 피드백 3가지 반영한 명확한 실행 계획

---

## 📋 피드백 요약

### 1. Jetson 라이브러리 문제 해결
- **현상**: Jetson 환경에서 라이브러리 의존성 문제 발생 가능성
- **필요**: 레퍼런스 찾기 (유사 프로젝트, OpenVLA/RoboVLMs 이슈 트래커 등)
- **우선순위**: 🔴 High

### 2. 리소스 관리 측정 및 문서화 (논문용)
- **목적**: "RoboVLMs의 큰 리소스를 줄였다"를 정량적으로 증명
- **현재 상태**: 서버 작동 전 메모리 6/16GB (OS + 터미널 + SSH IDE)
- **필요**: 상세 메모리 측정 및 프로세스별 분석
- **우선순위**: 🔴 High (논문 작성 필수)

### 3. API Calling 최적화
- **배경**: 
  - 10개 chunk 생성 시 1~8번만 사용
  - 5개 chunk 생성 시 약 2배의 호출 필요
- **시도**: 동작이 부자연스럽더라도 RoboVLMs 팔을 모바일로 변경
- **필요**: Chunk 크기별 성능 비교 및 최적화 전략
- **우선순위**: 🟡 Medium

---

## 🎯 실행 계획

## Phase 1: 현황 파악 및 분석 (1-2일)

### 1.1 Jetson 라이브러리 레퍼런스 조사
**목표**: Jetson Orin Nano (16GB) 환경에서 VLM 배포 시 라이브러리 문제 해결

**작업**:
- [ ] **OpenVLA Jetson 배포 사례 조사**
  - GitHub Issues/Discussions 검색
  - NVIDIA Jetson 커뮤니티 포럼 확인
- [ ] **RoboVLMs 의존성 분석**
  - `RoboVLMs/requirements.txt` 상세 분석
  - Jetson 호환성 문제 가능성 파악
- [ ] **BitsAndBytes Jetson 호환성**
  - INT8 quantization Jetson 지원 확인
  - 대체 솔루션 조사 (TensorRT, ONNX Runtime)
- [ ] **유사 프로젝트 레퍼런스 수집**
  - RT-2, Octo Jetson 배포 사례
  - VLM mobile deployment 논문/블로그

**산출물**:
- `docs/JETSON_LIBRARY_REFERENCES_20251231.md`

**예상 소요**: 4-6시간

---

### 1.2 리소스 사용량 상세 측정 (논문용)
**목표**: RoboVLMs 대비 Mobile VLA의 리소스 절감 정량화

#### 측정 항목

| 구분 | 측정 대상 | 도구 | 비고 |
|------|----------|------|------|
| **Baseline** | OS + SSH + IDE | `htop`, `free -h` | 서버 유휴 상태 |
| **Model Loading** | VLM 모델 로딩 시 | `nvidia-smi`, `ps aux` | FP32 vs INT8 |
| **Inference** | 추론 실행 중 | `nvidia-smi dmon`, `time` | 18회 연속 테스트 |
| **Peak Memory** | 최대 메모리 사용 | `nvidia-smi --query-gpu=memory.used` | GPU + CPU |

#### 작업 체크리스트
- [ ] **Baseline 측정**
  ```bash
  # 서버 재시작 직후
  free -h > baseline_memory.txt
  nvidia-smi --query-gpu=memory.used,memory.total --format=csv > baseline_gpu.txt
  ps aux --sort=-%mem | head -20 > baseline_processes.txt
  ```

- [ ] **OS + SSH + IDE 메모리 측정**
  ```bash
  # SSH 연결 + VSCode Remote 접속 상태
  free -h
  ps aux | grep -E 'sshd|code-server|vscode'
  ```

- [ ] **Model Loading 측정**
  ```python
  # scripts/measure_model_loading.py
  # - FP32 checkpoint: 6.4GB 디스크 → ? GPU
  # - INT8 BitsAndBytes: ? GPU
  ```

- [ ] **Inference 메모리 측정**
  ```bash
  # 18회 연속 추론 중 메모리 프로파일링
  nvidia-smi dmon -s mu -c 20 > inference_gpu_memory.txt
  ```

- [ ] **RoboVLMs와 비교**
  - RoboVLMs 원본 모델 메모리 (논문/README 참조)
  - Mobile VLA (1.6B) 메모리
  - 절감율 계산

**산출물**:
- `docs/RESOURCE_MANAGEMENT_ANALYSIS_20251231.md`
- `scripts/measure_resources.sh` (자동화 스크립트)
- 측정 데이터: `logs/resource_measurements_20251231/`

**예상 소요**: 3-4시간

---

### 1.3 API Calling 최적화 분석
**목표**: Chunk 크기별 성능 비교 및 최적 전략 도출

#### 현재 상황
- **Chunk10**: 10개 action 예측 → 1~8번만 사용 (20~30% 활용)
- **Chunk5**: 5개 action 예측 → 약 2배 호출 필요 (100% 활용)
- **Trade-off**: 추론 횟수 vs 예측 정확도

#### 분석 작업
- [ ] **실제 사용 패턴 분석**
  - 18회 연속 추론 시 chunk 사용 현황
  - Receding horizon 전략에서 chunk 재사용 비율
  
- [ ] **성능 비교 테스트**
  ```bash
  # Chunk5 (현재 Best)
  - 추론 횟수: 18회
  - 평균 latency: 495ms
  - 총 시간: 9.6초

  # Chunk10 (비교)
  - 추론 횟수: ? (예상 10-12회)
  - 평균 latency: ?
  - 총 시간: ?
  ```

- [ ] **RoboVLMs 팔 → 모바일 변환 효과**
  - 기존: 로봇팔 6-DOF action space
  - 변경: 모바일 2-DOF (linear_x, linear_y)
  - Action space 축소 효과 분석

**산출물**:
- `docs/API_CALLING_OPTIMIZATION_20251231.md`

**예상 소요**: 2-3시간

---

## Phase 2: 문제 해결 및 최적화 (2-3일)

### 2.1 Jetson 라이브러리 문제 사전 대응
- [ ] `requirements-jetson.txt` 작성
- [ ] Docker 이미지 준비 (optional)
- [ ] 트러블슈팅 가이드 작성

### 2.2 리소스 측정 자동화
- [ ] 측정 스크립트 작성
- [ ] CI/CD 통합 (optional)
- [ ] 결과 시각화

### 2.3 API Calling 최적화 구현
- [ ] Chunk5 vs Chunk10 성능 실험
- [ ] Optimal chunk size 결정
- [ ] 코드 적용

---

## Phase 3: 문서화 및 미팅 준비 (1일)

### 3.1 통합 리포트 작성
- [ ] **미팅 준비 문서**: `docs/MEETING_READY_20251231.md`
  - 3가지 피드백 해결 상태
  - 정량적 데이터 제시
  - 다음 단계 계획

### 3.2 논문용 데이터 정리
- [ ] 리소스 절감 표/그래프
- [ ] 성능 비교 표
- [ ] 실험 설정 상세 기술

---

## 📊 예상 산출물

### 문서
1. `JETSON_LIBRARY_REFERENCES_20251231.md` - Jetson 배포 레퍼런스
2. `RESOURCE_MANAGEMENT_ANALYSIS_20251231.md` - 리소스 측정 결과
3. `API_CALLING_OPTIMIZATION_20251231.md` - API 최적화 분석
4. `MEETING_READY_20251231.md` - 통합 미팅 준비 문서

### 스크립트
1. `scripts/measure_resources.sh` - 리소스 측정 자동화
2. `scripts/jetson_dependency_check.py` - Jetson 의존성 검증
3. `scripts/chunk_comparison_test.py` - Chunk 크기 비교 실험

### 데이터
1. `logs/resource_measurements_20251231/` - 측정 데이터
2. `assets/resource_comparison_chart.png` - 시각화

---

## ⏱️ 일정 계획

| 날짜 | Phase | 작업 | 예상 시간 |
|------|-------|------|-----------|
| **12/31 (화)** | Phase 1 | 조사 및 분석 | 6시간 |
| **1/1 (수)** | Phase 1-2 | 측정 완료 + 문제 해결 시작 | 8시간 |
| **1/2 (목)** | Phase 2-3 | 최적화 + 문서화 | 6시간 |
| **1/3 (금)** | Phase 3 | 미팅 준비 완료 | 2시간 |

**총 예상 소요**: 22시간 (약 3일)

---

## 🎯 핵심 목표 (Success Criteria)

### 1. Jetson 라이브러리 문제
- ✅ 5개 이상의 레퍼런스 확보
- ✅ 트러블슈팅 가이드 작성
- ✅ Jetson 호환성 검증 스크립트

### 2. 리소스 관리
- ✅ **정량적 데이터**:
  - Baseline: OS + IDE 메모리 사용량
  - Model Loading: FP32 vs INT8
  - Inference: Peak memory
  - RoboVLMs 대비 절감율 (%)
- ✅ 논문에 삽입 가능한 표/그래프

### 3. API Calling 최적화
- ✅ Chunk5 vs Chunk10 정량 비교
- ✅ Optimal chunk size 결정
- ✅ Trade-off 분석 완료

---

## 🔗 참조 문서

### 기존 작업
- `WEEKLY_PROGRESS_20251222-24.md` - 최근 개발 현황
- `final_status_meeting_ready_20251217.md` - 이전 미팅 준비
- `server_performance_analysis_20251217.md` - 서버 성능 분석

### 코드
- `Mobile_VLA/inference_server.py` - API 서버
- `scripts/test_robot_driving_18steps.py` - 성능 테스트
- `setup_jetson.sh` - Jetson 설정 스크립트

---

## ⚠️ 주의사항

### Jetson 라이브러리
- BitsAndBytes는 Jetson에서 ARM 아키텍처 호환성 문제 가능
- 대체 방안: TensorRT, ONNX Runtime 검토 필요

### 리소스 측정
- 측정 환경 일관성 유지 (재부팅 후, 동일 조건)
- GPU 메모리는 `nvidia-smi` 명령어 시점의 snapshot
- 평균값 산출을 위해 최소 3회 반복 측정

### API Calling
- Chunk10은 Val Loss가 높아 정확도 떨어짐 (0.284 vs Chunk5 0.067)
- 단순 호출 횟수 감소보다 **정확도 우선** 고려

---

**작성자**: Billy  
**다음 미팅**: 미정  
**상태**: 🟡 계획 수립 완료, 실행 대기

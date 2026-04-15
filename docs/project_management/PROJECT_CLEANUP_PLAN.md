# Mobile VLA 프로젝트 정리 계획

## 🎯 정리 목표
- 불필요한 파일 제거
- 중복 스크립트 통합
- 아이디어별 노트 정리
- Git 커밋 준비

## 📋 정리 대상 파일들

### 🗑️ 제거할 파일들
1. **중복된 Docker 관련 파일들**:
   - `docker-compose.yml` (기본) → `docker-compose.mobile-vla.yml` 사용
   - `run_ros2_docker.sh` → `run_robovlms_docker.sh` 사용
   - `run_ros2_system.sh` → `run_mobile_vla_system.sh` 사용

2. **중복된 설정 스크립트들**:
   - `setup_aliases_docker.sh` → `install_aliases_docker.sh` 사용
   - `setup_aliases_host.sh` → `install_aliases_host.sh` 사용
   - `setup_ros2_docker.sh` → 통합
   - `setup_ros2_host.sh` → 통합

3. **테스트 이미지들**:
   - `test_image_1.jpg`, `test_image_2.jpg`, `test_image_3.jpg`
   - `new_image.jpg`

4. **중복된 문서들**:
   - `cursor_resolve_merge_conflict_issue.md` → `DOCKER_DEBUG_LOG.md`에 통합
   - `cursor_recover_and_merge_dockerfile_com.md` → 정리 후 보관

### 🔄 통합할 파일들
1. **Docker 관련 스크립트들**:
   - `docker-build.sh`, `docker-run.sh`, `docker-stop.sh`, `docker-monitor.sh`
   - → `docker-build-verified.sh`, `docker-run-verified.sh` 등으로 통합

2. **설정 스크립트들**:
   - 모든 `install_aliases_*.sh` → `install_all_aliases.sh`로 통합

3. **ROS 관련 스크립트들**:
   - `run_*.sh` 파일들 → `scripts/` 디렉토리로 이동

### 📝 아이디어별 노트 생성
1. **Docker 환경**: `DOCKER_ENVIRONMENT_NOTES.md`
2. **ROS2 시스템**: `ROS2_SYSTEM_NOTES.md`
3. **모델 학습**: `MODEL_TRAINING_NOTES.md`
4. **데이터 수집**: `DATA_COLLECTION_NOTES.md`
5. **로봇 제어**: `ROBOT_CONTROL_NOTES.md`

## 🚀 실행 순서
1. 중복 파일 제거
2. 스크립트 통합
3. 아이디어별 노트 생성
4. Git 커밋

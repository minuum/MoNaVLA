# 추론 시 이미지 데이터 로깅(Session Image Capture) 추가 플랜
작성일: 2026-02-27

## 1. 개요
현재 VLA 추론(18-step Inference) 모드 진행 시 서버상에 액션(Action)과 지연시간(Latency) 정보는 `inference_logger.py`를 통해 세션별 JSON 파일(`session_{YYYYMMDD_HHMMSS}.json`)로 저장되고 있습니다.
이에 더하여 **실제 추론 시 사용된 카메라 이미지(Numpy/PNG 형)도 해당 실험 세션과 동일한 기준(디렉토리 및 타임스탬프)으로 캡처/저장**하여 실험 분석과 오프라인 검증의 정확도를 높이고자 합니다. 데이터 수집 스크립트(`mobile_vla_data_collector.py`)의 이미지 로깅 방식을 참고합니다.

## 2. 요구 사항 및 구현 방안

### 2.1 저장 구조 일원화
저장될 데이터 형태:
```text
docs/inference_reports/
 ├── session_20260227_175342.json  (기존 액션 메타데이터)
 └── session_20260227_175342/       (신규 추가될 이미지 저장 폴더)
      ├── frame_00.png (1/18 정지 프레임)
      ├── frame_01.png
      └── ...
      └── frame_17.png
```

### 2.2 `inference_logger.py` 기능 확장 (P1)
**현황:** `InferenceLogger` 클래스가 `start_session()`, `log_step()`, `end_session()` 구조로 텍스트/숫자 정보만 JSON 배열에 누적 저장 중.
**플랜:**
1. **디렉토리 생성**: `start_session()` 호출 시 `self.session_id`와 동일한 이름의 하위 폴더 생성. `self.image_log_dir = os.path.join(self.log_dir, f"session_{self.session_id}")`
2. **이미지 덤프 함수 추가**: `log_step(self, step_idx, action, latency, chunk=None, image=None)`로 파라미터를 확장하여, `image`가 주어질 경우 Pillow(PIL)나 OpenCV를 사용하여 `frame_{step_idx:02d}.jpg` 파일로 저장. HDF5를 쓰지 않고 개별 이미지로 가볍게 저장(\*분석 용이성).

### 2.3 `Mobile_VLA/inference_server.py` 또는 `gradio_inference_dashboard.py` 연동 (P1)
**현황:** 대시보드 스크립트의 `update_ui` 내부에서 `logger_instance.log_step(current_step, raw_act, raw_lat, raw_chunk)`를 호출 중.
**플랜:**
1. 프레임을 얻어오는 `ros_node.get_inference_frame()` 리턴 객체(`PIL.Image`)를 `log_step` 호출 시 추가 인자로 넘기도록 수정.
2. Step 1(Start/Wait)에서도 화면에 표시될 이미지를 저장하도록 `log_step` (Zero-Action) 호출 추가 연동.

## 3. 작업 순서 가이드 (DO NOT EXECUTE YET)
1. `scripts/inference_logger.py` 열기: `log_step` 시그니처 수정 및 PIL.Image 파일 저장(`save`) 로직 추가.
2. `scripts/gradio_inference_dashboard.py` 열기: `logger_instance.log_step` 호출부에 `image` 데이터 패싱 (Base64 최적화 플랜과 충돌 방지를 위해, PIL 객체 자체를 넘겨 파일 I/O 유도).
3. 추론 폴더(`docs/inference_reports`) 내 권한과 경로 검증.

---
**비고:**
이 기능 업데이트는 "메모리 최적화 플랜(`260227_memory_optimization_plan.md`)"과 병행/후속으로 진행될 예정입니다. 아직은 계획 문서만 깃에 Push하며, 소스 코드는 수정 대기 상태입니다.

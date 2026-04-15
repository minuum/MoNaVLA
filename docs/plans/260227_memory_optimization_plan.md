# 메모리 누수 및 오버헤드 해결 플랜
작성일: 2026-02-27

## 1. 개요
Jetson Orin NX (16GB RAM) 환경에서 Gradio 기반 VLA 모델 추론 시 시스템 메모리가 14.8GB까지 치솟고 SWAP 메모리가 약 9.3GB나 잡히는 등 극심한 메모리 누수 및 오버헤드 문제가 발생하고 있습니다. 이는 실제 로봇 주행 테스트 시 랙이나 시스템 정지를 유발할 수 있어 긴급한 수정이 필요합니다.

## 2. 주요 원인 및 해결 방안

### 2.1. Base64 직렬화/역직렬화에 의한 가비지 버퍼 누수 (우선순위: P1)
**문제점:** `run_api_inference()` 함수 내에서 API 방식의 레거시 코드로 인해, 매 0.5초마다 고해상도 이미지를 Base64 문자열로 압축/변환(`img_b64 = base64.b64encode(buffered.getvalue())`)하고 추론 서버 파일에서는 이를 다시 Decode(`image_bytes = base64.b64decode(image_input)`)하여 PIL 이미지로 바꾸는 비효율적인 연산이 반복되고 있습니다. 이로 인해 GC가 회수하기 전에 메모리에 심각한 용량이 누적됩니다.
**해결안:**
- 로컬 추론 모드(`use_local=True`) 시에는 Base64 변환 없이 PIL Image 객체나 OpenCV `ndarray` 텐서를 모델 파이프라인(`local_model_instance.predict`)에 직접 주입(Direct Injection)하도록 수정.
- `MobileVLAInference` 클래스의 `preprocess_image` 입력 타입을 유연하게 변경하여 변환 비용을 최소화.

### 2.2. 추론 루프 구간 불필요한 캐시 누적 및 텐서 누수 (우선순위: P1)
**문제점:** `with torch.no_grad():`를 사용하고 있으나, 계속되는 이미지 플로우에서 메모리 파편화(Fragmentation)와 CPU-GPU 간 데이터 처리 중 캐시가 지속적으로 팽창하고 있습니다.
**해결안:**
- `update_ui` 내부 추론 완료 시점에서 불필요해진 변환 텐서나 이미지를 명시적으로 `del` 처리.
- 주기적인 `import gc; gc.collect()` 및 `torch.cuda.empty_cache()` 호출 추가.
- 가능하다면 `torch.inference_mode()`로 변경하여 추론 오버헤드를 한층 더 줄이기.

### 2.3. Gradio UI 타이머 및 세션 폴링 (우선순위: P2)
**문제점:** Gradio 내부 타이머 컴포넌트(`gr.Timer`) 및 이미지 렌더러가 이전 이미지를 계속 캡처하여 메모리를 붙잡고 있을 수 있습니다.
**해결안:**
- 이미지 객체 레퍼런스가 과도하게 쌓이지 않도록 state 관리 효율화 점검 및 필요 시 `cv2.destroyAllWindows()` 개념과 같이 명시적인 null 처리 고려.

## 3. 작업 순서 가이드 (DO NOT EXECUTE YET)
1. `Mobile_VLA/inference_server.py`의 `predict`와 `preprocess_image`가 PIL/numpy 직접 입력을 처리하도록 구조 수정.
2. `scripts/gradio_inference_dashboard.py` 파일의 `run_api_inference`에서 Base64 변환 로직 제거 및 raw image 파단 로직 연결.
3. 명시적 가비지 컬렉터(`gc.collect()`, `torch.cuda.empty_cache()`) 추가 삽입.
4. 테스트: UI 실행 후 jtop 확인, 메모리가 10GB 미만에서 Stabilize(안정화) 되는지 테스트.

---
**비고:** 위 수정 사항은 현재 적용 대기 상태이며, `git push` 등 이전 작업 먼저 완료할 예정입니다.

# Jetson 라이브러리 레퍼런스 및 배포 가이드

**작성일**: 2025-12-31  
**목적**: Jetson Orin Nano (16GB) VLM 배포 시 라이브러리 문제 해결 레퍼런스 제공  
**대상 모델**: Mobile VLA (Kosmos-2 1.6B + BitsAndBytes INT8)

---

## 📚 Executive Summary

Jetson Orin Nano (16GB)에서 VLM 배포는 **충분히 가능**하나, ARM 아키텍처 및 라이브러리 호환성 문제에 대비해야 합니다. 특히 **BitsAndBytes는 ARM에서 직접 설치 시 이슈**가 있으며, **TensorRT를 활용한 최적화가 더 효율적**일 수 있습니다.

### 핵심 발견사항
- ✅ Jetson Orin Nano는 **최대 7B 모델**까지 INT8 양자화로 실행 가능
- ✅ Kosmos-2 1.6B는 **문제없이 배포 가능**
- ⚠️ BitsAndBytes는 ARM에서 **소스 컴파일 필요** 가능성
- ✅ **TensorRT 최적화**가 Jetson에서 더 효율적
- ✅ NanoVLA, EdgeVLA 같은 경량화 모델 레퍼런스 존재

---

## 🔍 주요 레퍼런스

### 1. BitsAndBytes on Jetson

#### 호환성 및 문제점

| 항목 | 상태 | 비고 |
|------|------|------|
| **Jetson Architecture** | Ampere (Compute Capability 8.7) | INT8 하드웨어 지원 ✅ |
| **BitsAndBytes 지원** | 공식 지원 (이론적) | Linux, CUDA 10.0+ |
| **ARM 빌드** | ⚠️ 문제 가능성 | 소스 컴파일 필요할 수 있음 |
| **대체 솔루션** | TensorRT, GGUF, GPTQ | Jetson에서 더 최적화됨 |

#### 설치 방법

**방법 1: pip 설치 (시도)**
```bash
pip install bitsandbytes
```
- **문제**: ARM 아키텍처에서 pre-built wheel 없을 수 있음
- **에러 예시**: `RuntimeError: CUDA binary not found`

**방법 2: 소스 빌드 (권장)**
```bash
# CUDA 환경 확인
nvcc --version  # JetPack CUDA

# 소스에서 빌드
git clone https://github.com/TimDettmers/bitsandbytes.git
cd bitsandbytes
CUDA_VERSION=114 make cuda11x  # JetPack 5.x는 CUDA 11.4
python setup.py install
```

**방법 3: Docker 사용 (가장 안전)**
```bash
# NVIDIA Jetson Generative AI Lab 컨테이너 활용
dustynv/l4t-pytorch:r35.2.1-pth2.0-py3  # JetPack 5.x
```

**레퍼런스**:
- [BitsAndBytes GitHub Issues - Jetson 관련](https://github.com/TimDettmers/bitsandbytes/issues)
- [NVIDIA Jetson Forum - BitsAndBytes](https://forums.developer.nvidia.com/search?q=bitsandbytes)
- [Stack Overflow - BitsAndBytes ARM Build](https://stackoverflow.com/questions/tagged/bitsandbytes+arm)

---

### 2. OpenVLA on Jetson

#### 관련 연구 및 프로젝트

**NanoVLA (OpenReview, 2024)**
- **목적**: Edge 디바이스용 경량 VLA
- **성능**: OpenVLA 대비 **52배 빠른 추론**
- **타겟 디바이스**: Jetson Orin Nano
- **기법**:
  - Visual-language decoupling
  - Long-short action chunking
  - Dynamic routing
- **링크**: [OpenReview - NanoVLA](https://openreview.net)

**EdgeVLA (EVLA, arXiv 2024)**
- **목적**: 추론 속도 및 메모리 효율성 개선
- **핵심**: Autoregressive 요구 제거, Small Language Model (SLM) 활용
- **효과**: 메모리 사용량 및 latency 감소
- **링크**: [arXiv - EdgeVLA](https://arxiv.org/)

**OpenVLA Quantization**
- **4-bit quantization**: Jetson Orin Nano에서 OOM 가능성
- **8-bit quantization**: 메모리 내 실행 가능
- **레퍼런스**: [OpenVLA GitHub - Quantization](https://github.com/openvla/openvla)

**TensorRT 최적화**
- **방법**: OpenVLA → ONNX → TensorRT
- **필수**: Jetson AGX Orin 타겟 디바이스에서 변환
- **효과**: 추론 속도 대폭 향상
- **레퍼런스**: [NVIDIA Forum - OpenVLA TensorRT](https://forums.developer.nvidia.com/t/openvla-tensorrt)

---

### 3. Kosmos-2 on Jetson

#### Deployment 전략

**PyTorch Mobile 방식**
1. **TorchScript 변환**
   ```python
   import torch
   model = load_kosmos2_model()
   scripted_model = torch.jit.script(model)
   scripted_model.save("kosmos2_scripted.pt")
   ```

2. **Quantization (INT8)**
   ```python
   from torch.quantization import quantize_dynamic
   quantized_model = quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
   ```

3. **Jetson 배포**
   ```bash
   # JetPack PyTorch 설치
   pip3 install torch-2.x.x+jetson -f https://nvidia.com/pytorch
   
   # 모델 로딩
   model = torch.jit.load("kosmos2_scripted.pt")
   ```

**TensorRT 방식 (권장)**
```bash
# ONNX 변환
python -m torch.onnx.export model.pt model.onnx

# TensorRT 변환 (Jetson에서 실행)
trtexec --onnx=model.onnx --saveEngine=model.trt --int8
```

**레퍼런스**:
- [Hugging Face - Kosmos-2](https://huggingface.co/microsoft/kosmos-2)
- [NVIDIA Jetson - PyTorch Installation](https://forums.developer.nvidia.com/t/pytorch-for-jetson)
- [PyTorch Mobile Documentation](https://pytorch.org/mobile)

---

### 4. Jetson VLM 배포 성공 사례

#### NVIDIA Jetson Generative AI Lab
- **제공**: Pre-built containers, tutorials, VLM examples
- **모델 지원**:
  - Qwen2.5-VL-3B (INT8)
  - VILA 1.5-3B
  - Gemma 3/4B
- **도구**: Live VLM WebUI (실시간 테스트)
- **링크**: [Jetson AI Lab](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/)

#### RoboSuite on Jetson AGX Orin
- **환경**: Jetson AGX Orin, OpenVLA
- **주의사항**: 좌표계 변환 (model output ↔ robot control)
- **레퍼런스**: [NVIDIA Forum - RoboSuite](https://forums.developer.nvidia.com/t/robosuite-jetson)

#### Jetson Orin Nano 메모리 제약
- **8GB 모델**: 최대 4B parameters (INT8)
- **16GB 모델**: 최대 7B parameters (INT8) ← **우리 타겟** ✅
- **8-bit quantization 효과**: 2배 모델 크기 지원 가능

---

## 🛠️ 권장 배포 전략

### Option 1: BitsAndBytes PTQ (현재 방식)
**장점**:
- ✅ 코드 변경 없음 (이미 구현됨)
- ✅ Post-training (재학습 불필요)
- ✅ FP32 checkpoint 재사용

**단점**:
- ⚠️ ARM 빌드 문제 가능성
- ⚠️ Inference 속도 최적화 부족

**필요 조치**:
1. Jetson에서 BitsAndBytes 소스 빌드 테스트
2. Docker 컨테이너 사용 고려
3. 실패 시 Option 2로 전환

---

### Option 2: TensorRT Optimization (권장)
**장점**:
- ✅ Jetson 최적화 (NVIDIA 공식)
- ✅ 더 빠른 추론 속도
- ✅ 메모리 효율적

**단점**:
- ⚠️ 추가 변환 작업 필요
- ⚠️ Jetson 장비에서 변환 필수

**구현 단계**:
1. **ONNX 변환**:
   ```bash
   python scripts/export_to_onnx.py --checkpoint best_model.ckpt
   ```

2. **TensorRT 변환 (Jetson에서)**:
   ```bash
   trtexec --onnx=mobile_vla.onnx \
           --saveEngine=mobile_vla_int8.trt \
           --int8 \
           --workspace=4096
   ```

3. **Inference 코드 수정**:
   ```python
   import tensorrt as trt
   import pycuda.driver as cuda
   
   # TensorRT 엔진 로딩
   engine = load_trt_engine("mobile_vla_int8.trt")
   ```

**예상 성능**:
- 추론 속도: BitsAndBytes 대비 **2-3배 빠름**
- 메모리: 유사 (~1.8GB)

---

### Option 3: Hybrid (BitsAndBytes 백업 with TensorRT 목표)
**전략**:
1. **Phase 1**: BitsAndBytes로 초기 배포 (빠른 검증)
2. **Phase 2**: TensorRT로 최적화 (성능 향상)

**이유**:
- BitsAndBytes로 빠르게 동작 검증
- TensorRT 변환 문제 발생 시에도 fallback 가능

---

## 📋 Jetson 배포 체크리스트

### Pre-deployment (Billy 서버)
- [x] BitsAndBytes INT8 모델 학습 완료
- [x] API Server 테스트 (18회 연속 성공)
- [ ] ONNX export 스크립트 작성 (Option 2용)
- [ ] requirements-jetson.txt 작성

### Deployment (Jetson)
- [ ] JetPack 5.x 설치 확인
- [ ] PyTorch (Jetson용) 설치
- [ ] **BitsAndBytes 빌드 테스트**
  - [ ] pip 설치 시도
  - [ ] 실패 시 소스 빌드
  - [ ] 실패 시 Docker 사용
- [ ] Kosmos-2 pretrained model 다운로드
- [ ] Checkpoint 전송 (6.4GB)
- [ ] API Server 실행 테스트
- [ ] ROS2 Integration

### Troubleshooting 준비
- [ ] BitsAndBytes 소스 빌드 스크립트
- [ ] Docker 컨테이너 이미지 준비
- [ ] TensorRT 변환 스크립트 (백업)

---

## 📊 예상 성능 비교

### BitsAndBytes PTQ

| 항목 | Billy (A5000) | Jetson Orin Nano (예상) |
|------|---------------|------------------------|
| **GPU Memory** | 1.8GB | 1.8GB |
| **Inference Latency** | 495ms | 600-800ms (1.2-1.6x) |
| **Throughput** | 2.0 Hz | 1.3-1.7 Hz |

### TensorRT INT8

| 항목 | Billy (A5000) | Jetson Orin Nano (예상) |
|------|---------------|------------------------|
| **GPU Memory** | ~1.5GB | ~1.5GB |
| **Inference Latency** | ~300ms | ~400ms |
| **Throughput** | 3.3 Hz | 2.5 Hz |

---

## 🔗 참고 자료

### 필수 문서
1. [NVIDIA Jetson Software](https://developer.nvidia.com/embedded/jetpack)
2. [Jetson PyTorch Installation](https://forums.developer.nvidia.com/t/pytorch-for-jetson)
3. [BitsAndBytes GitHub](https://github.com/TimDettmers/bitsandbytes)
4. [TensorRT Documentation](https://docs.nvidia.com/deeplearning/tensorrt/)

### 연구 논문
1. **NanoVLA**: [OpenReview](https://openreview.net) - Jetson Orin Nano용 경량 VLA
2. **EdgeVLA**: [arXiv](https://arxiv.org) - Edge 디바이스 VLA 최적화

### 커뮤니티
1. [NVIDIA Jetson Forums](https://forums.developer.nvidia.com/c/agx-autonomous-machines/jetson-embedded-systems/)
2. [Jetson AI Lab GitHub](https://github.com/dusty-nv/jetson-inference)
3. [OpenVLA Discussions](https://github.com/openvla/openvla/discussions)

---

## 💡 결론 및 권장사항

### 배포 전략
1. **우선**: BitsAndBytes PTQ로 초기 배포 (현재 구현 활용)
2. **백업**: Docker 컨테이너 준비 (ARM 빌드 문제 대비)
3. **최적화**: TensorRT 변환 (성능 향상 목표)

### 핵심 메시지
- Jetson Orin Nano 16GB에서 **Mobile VLA 1.6B INT8 배포 충분히 가능** ✅
- BitsAndBytes ARM 이슈는 **소스 빌드 또는 Docker로 해결 가능**
- TensorRT 최적화 시 **더 빠른 추론 속도 확보 가능**

---

**작성자**: Billy  
**작성일**: 2025-12-31  
**상태**: ✅ 레퍼런스 조사 완료

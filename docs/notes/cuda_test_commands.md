# Jetson CUDA 테스트 명령어 모음

## 1. 기본 CUDA 테스트
```bash
# PyTorch CUDA 사용 가능 여부 확인
python3 -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"

# 상세 CUDA 정보 확인
python3 -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'CUDA Device Count: {torch.cuda.device_count()}'); print(f'CUDA Device Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

## 2. Docker 컨테이너에서 CUDA 테스트
```bash
# 기존 컨테이너에서 테스트
docker exec ros2_inference bash -c "python3 -c 'import torch; print(f\"CUDA Available: {torch.cuda.is_available()}\"); print(f\"PyTorch Version: {torch.__version__}\")'"

# 새 컨테이너로 테스트
docker run --rm --gpus all mobile_vla:robovlms-cuda-verified bash -c "python3 -c 'import torch; print(f\"CUDA Available: {torch.cuda.is_available()}\"); print(f\"PyTorch Version: {torch.__version__}\")'"
```

## 3. Jetson 전용 CUDA 테스트
```bash
# Jetson 환경에서 CUDA 라이브러리 확인
ls -la /usr/local/cuda/lib64/libcudart*

# CUDA 환경 변수 확인
echo $CUDA_HOME
echo $LD_LIBRARY_PATH

# Jetson PyTorch CUDA 테스트
python3 -c "import torch; print('Jetson CUDA Test:'); print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

## 4. 실제 CUDA 연산 테스트
```bash
# 간단한 CUDA 연산 테스트
python3 -c "import torch; x = torch.randn(1000, 1000); y = torch.randn(1000, 1000); print('CPU Test:'); print(torch.mm(x, y).shape); print('CUDA Test:'); if torch.cuda.is_available(): x = x.cuda(); y = y.cuda(); print(torch.mm(x, y).shape); else: print('CUDA not available')"
```

## 5. Transformers 모델 CUDA 테스트
```bash
# Transformers 모델 CUDA 테스트
python3 -c "from transformers import AutoModel; import torch; model = AutoModel.from_pretrained('bert-base-uncased'); print(f'Model device: {next(model.parameters()).device}'); if torch.cuda.is_available(): model = model.cuda(); print(f'Model moved to: {next(model.parameters()).device}'); else: print('CUDA not available')"
```

## 6. 메모리 사용량 확인
```bash
# GPU 메모리 사용량 확인 (Jetson)
python3 -c "import torch; print(f'CUDA Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB' if torch.cuda.is_available() else 'CUDA not available')"

# 시스템 메모리 확인
free -h
```

## 7. 문제 해결용 테스트
```bash
# CUDA 라이브러리 경로 확인
python3 -c "import torch; print('CUDA Library Path:'); print(torch.cuda.get_device_properties(0)) if torch.cuda.is_available() else print('CUDA not available')"

# PyTorch 빌드 정보 확인
python3 -c "import torch; print('PyTorch Build Info:'); print(torch.__config__.show())"
```

## 8. run_multi_container_ros.sh에 추가할 CUDA 테스트
```bash
# 추론 컨테이너에서 CUDA 테스트
docker exec ros2_inference bash -c "
    cd /workspace/vla
    echo '=== Jetson CUDA Test ==='
    python3 -c \"import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'CUDA Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')\"
    echo ''
    echo '=== CUDA Memory Test ==='
    python3 -c \"import torch; print(f'Total GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB' if torch.cuda.is_available() else 'CUDA not available')\"
    echo ''
    echo '=== Transformers CUDA Test ==='
    python3 -c \"from transformers import AutoModel; import torch; model = AutoModel.from_pretrained('bert-base-uncased'); print(f'Model loaded on: {next(model.parameters()).device}'); if torch.cuda.is_available(): model = model.cuda(); print(f'Model moved to: {next(model.parameters()).device}'); else: print('CUDA not available')\"
"
```

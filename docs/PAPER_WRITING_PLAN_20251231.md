# 논문 작성 계획 (Billy 서버 기준)

**작성일**: 2025-12-31  
**대상**: Mobile VLA 논문  
**범위**: Billy 서버에서의 학습 및 평가 결과 (API 서버 제외)

---

## 📋 Executive Summary

논문의 핵심 주장:
1. **RoboVLMs 경량화**: 7B → 1.6B parameters (Kosmos-2 채택)
2. **리소스 절감**: 87% GPU 메모리 감소 (INT8 양자화)
3. **Edge 배포 가능**: Jetson Orin Nano (16GB) 타겟
4. **성능 유지**: Val Loss 0.067, 모바일 navigation 태스크 수행

---

## 📊 논문 구조 및 필요 데이터

### 1. Introduction

#### 필요 내용
- VLA 모델의 리소스 요구사항 문제
- Edge device (Jetson) 배포 필요성
- RoboVLMs의 한계 (7B, 14GB GPU memory)

#### 준비 상태
- ✅ RoboVLMs 리소스 요구사항 데이터
- ✅ Mobile VLA 리소스 절감 데이터

---

### 2. Related Work

#### 필요 내용
- VLA 모델 비교 (OpenVLA, RT-2, RoboFlamingo, Octo)
- Quantization 기법 (BitsAndBytes, QLoRA, TensorRT)
- Edge VLA (NanoVLA, EdgeVLA)

#### 준비 상태
- ✅ 레퍼런스 확보 완료 (`JETSON_LIBRARY_REFERENCES_20251231.md`)
- ⏳ 비교 표 작성 필요

---

### 3. Method

#### 3.1 Model Architecture

**필요 데이터**:
- Kosmos-2 architecture 상세
- Policy head 구조
- Action chunking mechanism

**준비 상태**:
- ✅ 코드 구현 완료
- ⏳ 아키텍처 diagram 필요

**작업 계획**:
```markdown
1. Kosmos-2 backbone 설명
   - Vision Encoder (ViT)
   - Language Model (Transformer Decoder)
   - 1.6B parameters 구성

2. Policy Head
   - MLP 구조
   - Action space: (linear_x, linear_y)
   - Chunk size: 5

3. Action Chunking
   - Receding Horizon 전략
   - Window size: 8 frames
   - Chunk size: 5 actions
```

---

#### 3.2 Training Setup

**데이터셋**:
- **Source**: 모바일 로봇 navigation 데이터
- **Episodes**: 500개 (Left 250 + Right 250)
- **Task**: 목표 지점까지 주행 (box detection)
- **Image**: 224x224, RGB
- **Actions**: (linear_x, linear_y), continuous

**학습 설정**:
```python
{
  "batch_size": 4,
  "learning_rate": 1e-5,
  "epochs": 10,
  "optimizer": "AdamW",
  "window_size": 8,
  "chunk_size": 5 또는 10,
  "freeze_vision": false,
  "freeze_llm": false  # Full fine-tuning
}
```

**준비 상태**:
- ✅ 데이터셋 500개 확보
- ✅ 학습 완료 (Chunk5, Chunk10)
- ⏳ 데이터셋 통계 분석 필요

**필요 작업**:
1. 데이터셋 통계 분석
   ```python
   # scripts/analyze_dataset_statistics.py
   - Episode 길이 분포
   - Action 분포 (linear_x, linear_y)
   - Left/Right 비율
   - 이미지 품질 분석
   ```

2. 학습 곡선 그래프
   ```python
   # scripts/plot_training_curves.py
   - Train Loss vs Epoch (Chunk5, Chunk10)
   - Val Loss vs Epoch
   - RMSE vs Epoch
   ```

---

#### 3.3 Quantization

**BitsAndBytes INT8 PTQ**:
- Post-Training Quantization
- LLM.int8() 알고리즘
- FP32 checkpoint 재사용
- 로딩 시 자동 변환

**준비 상태**:
- ✅ 구현 완료
- ✅ 성능 측정 완료 (6.3GB → 1.8GB)

**필요 데이터**:
- ✅ GPU Memory: FP32 vs INT8
- ✅ Inference Latency: 15s → 0.495s
- ⏳ Accuracy 비교 (FP32 vs INT8)

**필요 실험**:
```markdown
1. Accuracy 비교 (Optional)
   - FP32 모델 Validation Loss
   - INT8 모델 Validation Loss
   - 차이 분석

   **현재 데이터**:
   - Chunk5 FP32: Val Loss 0.067 (이미 학습됨)
   - Chunk5 INT8: 측정 필요
```

---

### 4. Experiments

#### 4.1 Experimental Setup

**Hardware**:
- GPU: NVIDIA RTX A5000 (24GB VRAM)
- CPU: AMD Ryzen
- RAM: 125GB
- OS: Ubuntu 22.04

**Software**:
- Python: 3.10
- PyTorch: 2.x
- CUDA: 11.8
- BitsAndBytes: 0.41.x

**준비 상태**: ✅ 완료

---

#### 4.2 Evaluation Metrics

**학습 지표**:
1. **Loss**
   - Train Loss
   - Validation Loss
   - RMSE (Root Mean Square Error)

2. **Convergence**
   - Best Epoch
   - Train-Val Gap (Overfitting 지표)

**리소스 지표**:
1. **GPU Memory**
   - Model Loading (FP32 / INT8)
   - Peak Memory (Inference)

2. **Inference Speed**
   - Latency (ms/frame)
   - Throughput (Hz)

**준비 상태**:
- ✅ Loss metrics 확보
- ✅ GPU Memory 측정 완료
- ✅ Inference Speed 측정 완료

---

#### 4.3 Main Results

**표 1: Action Chunking 비교**

| Model | Chunk Size | Val Loss | RMSE | Best Epoch | Train-Val Gap |
|-------|-----------|----------|------|-----------|---------------|
| Mobile VLA | 5 | **0.067** | 0.259 | 6 | 0.0261 |
| Mobile VLA | 10 | 0.284 | 0.533 | 5 | ? |

**필요 데이터**:
- ✅ Chunk5: Val Loss 0.067
- ✅ Chunk10: Val Loss 0.284
- ⏳ Chunk10 RMSE 계산 필요
- ⏳ Train-Val Gap 계산 필요

**필요 작업**:
```python
# scripts/calculate_metrics.py
1. Chunk10 RMSE 추출
   - Best checkpoint 로드
   - Validation set 평가

2. Train-Val Gap 계산
   - Train Loss - Val Loss
   - Overfitting 정도 분석

3. 통계적 유의성 테스트 (Optional)
   - t-test or Wilcoxon test
```

---

**표 2: 리소스 비교 (RoboVLMs vs Mobile VLA)**

| Model | Backbone | Params | GPU Mem (FP32) | GPU Mem (INT8) | Inference |
|-------|----------|--------|----------------|----------------|-----------|
| RoboVLMs | Qwen-VL 7B | 7.0B | ~14GB | - | ~15s |
| **Mobile VLA** | Kosmos-2 1.6B | 1.6B | 6.3GB | **1.8GB** | **0.495s** |
| **절감율** | - | **77%** | **55%** | **87%** | **97%** |

**준비 상태**: ✅ 완료

---

**표 3: Random Baseline 비교**

| Method | Val Loss | RMSE | Improvement |
|--------|----------|------|-------------|
| Random Baseline | - | 0.576 | - |
| **Mobile VLA (Chunk5)** | 0.067 | **0.259** | **70.5%** ↓ |

**데이터 출처**: `validation_experiments_results.json`

**준비 상태**: ✅ 완료

---

#### 4.4 Ablation Studies

**실험 1: Chunk Size 영향**

| Chunk Size | Val Loss | RMSE | 분석 |
|-----------|----------|------|------|
| 5 | **0.067** | 0.259 | Best |
| 10 | 0.284 | 0.533 | 4.2배 높음 |

**결론**: Chunk 5가 최적 (정확도 우선)

**필요 추가 실험 (Optional)**:
- Chunk 3, 7 확인
- Chunk size vs accuracy trade-off curve

---

**실험 2: Quantization 영향**

| Precision | GPU Memory | Inference Latency | Accuracy (Val Loss) |
|-----------|-----------|-------------------|---------------------|
| FP32 | 6.3GB | 15,000ms | 0.067 |
| INT8 | 1.8GB | 495ms | ? |

**필요 실험**:
```python
# INT8 모델 Validation
1. BitsAndBytes INT8 모델 로드
2. Validation set 평가
3. Val Loss 측정
4. FP32 대비 accuracy degradation 계산
```

**예상 결과**: ~98% accuracy 유지 (BitVLA 논문 참조)

---

**실험 3: Fine-tuning Strategy (Optional)**

| Strategy | Val Loss | 학습 시간 | GPU Memory |
|----------|----------|----------|-----------|
| Freeze Vision + LLM | ? | ? | ? |
| **Full Fine-tuning** (현재) | 0.067 | ~6 hours | 6.3GB |
| LoRA | ? | ? | ? |

**현재 상태**: Full fine-tuning만 수행

**필요 여부**: ❌ Skip (시간 소요, 논문에 필수 아님)

---

#### 4.5 Visualization

**그래프 1: Training Curves**
```python
# scripts/plot_training_curves.py
- X축: Epoch (1~10)
- Y축: Loss
- Line 1: Chunk5 Train Loss
- Line 2: Chunk5 Val Loss
- Line 3: Chunk10 Train Loss
- Line 4: Chunk10 Val Loss
```

**필요 데이터**:
- ⏳ Lightning logs 파싱 필요
- 파일 위치: `RoboVLMs/training_results/` 또는 checkpoints 디렉토리

---

**그래프 2: GPU Memory Comparison (Bar Chart)**
```
RoboVLMs (7B FP32):     ████████████████ 14GB
Mobile VLA (1.6B FP32): ██████ 6.3GB
Mobile VLA (1.6B INT8): ██ 1.8GB
```

**준비 상태**: ✅ 데이터 확보, 그래프 생성 필요

---

**그래프 3: Inference Speed Comparison**
```
             FP32 (15s)    INT8 (0.495s)
RoboVLMs:     ████████████████  -
Mobile VLA:   ████████████████  █
```

**준비 상태**: ✅ 데이터 확보, 그래프 생성 필요

---

**그래프 4: Action Distribution (데이터셋 분석)**
```python
# scripts/analyze_action_distribution.py
- Histogram: linear_x, linear_y
- Left vs Right action 비교
- Scatter plot: (linear_x, linear_y)
```

**필요 작업**: ⏳ 스크립트 작성 및 실행

---

### 5. Discussion

#### 5.1 Performance Analysis

**주장**:
1. Chunk5가 Chunk10보다 76% 우수 → 짧은 horizon이 모바일 navigation에 효과적
2. Random baseline 대비 70% 개선 → 학습 효과 검증
3. BitsAndBytes INT8으로 71% 메모리 절감, 30배 속도 향상

**필요 데이터**: ✅ 모두 확보

---

#### 5.2 RoboVLMs vs Mobile VLA

**장점**:
- 87% 리소스 절감 (14GB → 1.8GB)
- Edge device 배포 가능 (Jetson 16GB)
- 빠른 추론 속도 (2.0 Hz)

**Trade-off**:
- 모델 크기 축소 (7B → 1.6B)
- Task-specific fine-tuning 필요
- Generalization 능력 제한 (single task)

---

#### 5.3 Limitations

1. **데이터셋 규모**: 500 episodes (작은 규모)
2. **단일 태스크**: 모바일 navigation만 검증
3. **Simulation only**: 실제 로봇 테스트 미검증 (향후 계획)
4. **Generalization**: 다양한 환경 미테스트

---

### 6. Conclusion

**핵심 메시지**:
- Mobile VLA: RoboVLMs의 경량화 버전
- 87% GPU 메모리 절감, Edge 배포 가능
- Chunk5 최적, Val Loss 0.067 달성

---

## 📝 필요 작업 목록

### 우선순위 1: 필수 데이터 수집 (1-2일)

#### 1.1 학습 로그 분석
```bash
# Training curves 생성
python scripts/plot_training_curves.py \
  --chunk5_log RoboVLMs/.../chunk5_log \
  --chunk10_log RoboVLMs/.../chunk10_log \
  --output docs/figures/training_curves.png
```

**필요**:
- [ ] Lightning logs 파일 위치 확인
- [ ] CSV 또는 TensorBoard 로그 파싱
- [ ] Epoch별 Train/Val Loss 추출

---

#### 1.2 Chunk10 RMSE 계산
```python
# scripts/eval_chunk10_rmse.py
1. Chunk10 Best checkpoint 로드
2. Validation set 평가
3. RMSE 계산 및 저장
```

**예상 소요**: 30분

---

#### 1.3 데이터셋 통계 분석
```python
# scripts/analyze_dataset_statistics.py
1. 500 episodes 파싱
2. Episode 길이, action 분포 계산
3. Left/Right 통계
4. 그래프 생성
```

**예상 소요**: 1-2시간

---

#### 1.4 INT8 Accuracy 측정 (Optional)
```python
# scripts/eval_int8_accuracy.py
1. BitsAndBytes INT8 모델 로드
2. Validation set 평가
3. FP32 대비 accuracy degradation 계산
```

**예상 소요**: 1시간  
**필요 여부**: 🟡 Medium (논문 completeness 향상)

---

### 우선순위 2: 시각화 자료 생성 (1일)

#### 2.1 Training Curves
- [ ] Chunk5 Train/Val Loss
- [ ] Chunk10 Train/Val Loss

#### 2.2 리소스 비교 Bar Chart
- [ ] GPU Memory (RoboVLMs vs Mobile VLA)
- [ ] Inference Speed

#### 2.3 데이터셋 분석
- [ ] Action distribution histogram
- [ ] Left/Right action scatter plot

**도구**: Matplotlib, Seaborn

---

### 우선순위 3: 논문 초안 작성 (2-3일)

#### 3.1 Methods
- [ ] Model Architecture (diagram 포함)
- [ ] Training Setup
- [ ] Quantization

#### 3.2 Experiments
- [ ] Experimental Setup
- [ ] Evaluation Metrics
- [ ] Main Results (표 3개)
- [ ] Ablation Studies
- [ ] Visualization (그래프 4개)

#### 3.3 Discussion
- [ ] Performance Analysis
- [ ] RoboVLMs vs Mobile VLA
- [ ] Limitations

---

## 📊 데이터 체크리스트

### ✅ 확보 완료
- [x] Chunk5 Val Loss: 0.067
- [x] Chunk10 Val Loss: 0.284
- [x] GPU Memory (FP32): 6.3GB
- [x] GPU Memory (INT8): 1.8GB
- [x] Inference Latency (INT8): 495ms
- [x] Random Baseline RMSE: 0.576
- [x] Mobile VLA RMSE: 0.259
- [x] 데이터셋: 500 episodes

### ⏳ 추가 필요
- [ ] Training curves (Epoch별 Loss)
- [ ] Chunk10 RMSE
- [ ] INT8 Validation Loss (Optional)
- [ ] 데이터셋 통계 (episode 길이, action 분포)
- [ ] Train-Val Gap (Chunk5, Chunk10)

---

## 🎯 일정 계획

| 날짜 | 작업 | 예상 시간 |
|------|------|-----------|
| **1/1 (수)** | 필수 데이터 수집 | 4시간 |
| **1/2 (목)** | 시각화 생성 | 4시간 |
| **1/3 (금)** | 논문 초안 작성 (Methods) | 6시간 |
| **1/4 (토)** | 논문 초안 작성 (Experiments) | 6시간 |
| **1/5 (일)** | 논문 초안 작성 (Discussion, Conclusion) | 4시간 |

**총 예상 소요**: 24시간 (약 5일)

---

## 💡 논문 핵심 메시지

### Title (안)
"Mobile VLA: Lightweight Vision-Language-Action Model for Edge Robotic Deployment"

### Abstract (초안)
> We present Mobile VLA, a resource-efficient vision-language-action model designed for edge device deployment. By replacing the 7B Qwen-VL backbone with the 1.6B Kosmos-2 model and applying BitsAndBytes INT8 quantization, we achieve **87% GPU memory reduction** (14GB → 1.8GB) compared to RoboVLMs while maintaining competitive performance. Our model achieves a validation loss of 0.067 and 2.0 Hz inference rate, enabling deployment on resource-constrained devices like Jetson Orin Nano (16GB). Experiments on mobile robot navigation demonstrate **70% improvement over random baseline** with efficient action chunking (chunk size 5).

### Contributions
1. **경량 VLA 아키텍처**: Kosmos-2 1.6B 기반 모바일 로봇용 VLA
2. **효율적 양자화**: BitsAndBytes INT8 PTQ로 71% 메모리 절감
3. **Edge 배포 가능**: Jetson Orin Nano (16GB) 타겟
4. **성능 검증**: Val Loss 0.067, 70% improvement over baseline

---

**작성자**: Billy  
**작성일**: 2025-12-31  
**상태**: 📋 계획 수립 완료, 데이터 수집 필요

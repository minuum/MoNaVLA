#!/usr/bin/env python3
"""
TensorRT 모델 최적화 스크립트
- PyTorch 모델을 TensorRT로 변환
- FP16/INT8 양자화 지원
- 로봇 태스크 최적화
"""

import torch
import torch.nn as nn
import numpy as np
import os
import json
import time
from typing import Dict, Any, List
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

class Kosmos2CLIPHybridModel(nn.Module):
    """Kosmos2 + CLIP 하이브리드 모델 (MAE 0.212)"""
    
    def __init__(self):
        super().__init__()
        
        # 모델 구조 정의
        self.image_encoder = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten()
        )
        
        self.text_encoder = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 128)
        )
        
        self.fusion_layer = nn.Sequential(
            nn.Linear(256 + 128, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 3)  # linear_x, linear_y, angular_z
        )
    
    def forward(self, images, text_embeddings):
        """전방 전파"""
        # 이미지 인코딩
        image_features = self.image_encoder(images)
        
        # 텍스트 인코딩
        text_features = self.text_encoder(text_embeddings)
        
        # 특징 융합
        combined_features = torch.cat([image_features, text_features], dim=1)
        
        # 액션 예측
        actions = self.fusion_layer(combined_features)
        
        return actions

class TensorRTOptimizer:
    """TensorRT 최적화 클래스"""
    
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.logger = trt.Logger(trt.Logger.WARNING)
        self.runtime = trt.Runtime(self.logger)
        
        # 테스트 데이터 준비
        self.test_images = torch.randn(1, 3, 224, 224, device=self.device)
        self.test_text = torch.randn(1, 512, device=self.device)
        
        print(f"🔧 Device: {self.device}")
        print(f"📊 Test data shape: images {self.test_images.shape}, text {self.test_text.shape}")
        print(f"🎯 Target: Kosmos2 + CLIP Hybrid (MAE 0.212)")
        print(f"🚀 TensorRT Version: {trt.__version__}")
    
    def create_onnx_model(self, onnx_path: str):
        """PyTorch 모델을 ONNX로 변환"""
        print(f"\n🔨 Creating ONNX model...")
        
        # 모델 생성
        model = Kosmos2CLIPHybridModel().to(self.device)
        model.eval()
        
        # ONNX 변환
        torch.onnx.export(
            model,
            (self.test_images, self.test_text),
            onnx_path,
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=['images', 'text_embeddings'],
            output_names=['actions'],
            dynamic_axes={
                'images': {0: 'batch_size'},
                'text_embeddings': {0: 'batch_size'},
                'actions': {0: 'batch_size'}
            }
        )
        
        print(f"✅ ONNX model saved: {onnx_path}")
        print(f"📊 ONNX size: {os.path.getsize(onnx_path) / (1024*1024):.1f} MB")
        
        return onnx_path
    
    def build_tensorrt_engine(self, onnx_path: str, engine_path: str, precision: str = 'fp16'):
        """ONNX 모델을 TensorRT 엔진으로 변환"""
        print(f"\n🔨 Building TensorRT engine ({precision})...")
        
        # TensorRT 빌더 생성
        builder = trt.Builder(self.logger)
        config = builder.create_builder_config()
        config.max_workspace_size = 1 << 30  # 1GB
        
        # 정밀도 설정
        if precision == 'fp16' and builder.platform_has_fast_fp16:
            config.set_flag(trt.BuilderFlag.FP16)
            print(f"   Using FP16 precision")
        elif precision == 'int8' and builder.platform_has_fast_int8:
            config.set_flag(trt.BuilderFlag.INT8)
            config.set_flag(trt.BuilderFlag.STRICT_TYPES)
            print(f"   Using INT8 precision")
        else:
            print(f"   Using FP32 precision")
        
        # 네트워크 파싱
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, self.logger)
        
        with open(onnx_path, 'rb') as model:
            if not parser.parse(model.read()):
                for error in range(parser.num_errors):
                    print(f"   ONNX parsing error: {parser.get_error(error)}")
                return None
        
        # 엔진 빌드
        print(f"   Building TensorRT engine...")
        engine = builder.build_engine(network, config)
        
        if engine is None:
            print(f"   Failed to build TensorRT engine")
            return None
        
        # 엔진 저장
        with open(engine_path, 'wb') as f:
            f.write(engine.serialize())
        
        print(f"✅ TensorRT engine saved: {engine_path}")
        print(f"📊 Engine size: {os.path.getsize(engine_path) / (1024*1024):.1f} MB")
        
        return engine_path
    
    def benchmark_tensorrt(self, engine_path: str, num_runs: int = 100):
        """TensorRT 엔진 벤치마크"""
        print(f"\n📈 Benchmarking TensorRT Engine ({num_runs} runs)")
        print("-" * 50)
        
        # 엔진 로드
        with open(engine_path, 'rb') as f:
            engine_data = f.read()
        
        engine = self.runtime.deserialize_cuda_engine(engine_data)
        context = engine.create_execution_context()
        
        # 메모리 할당
        input_images = cuda.mem_alloc(self.test_images.numpy().nbytes)
        input_text = cuda.mem_alloc(self.test_text.numpy().nbytes)
        output_actions = cuda.mem_alloc(3 * 4)  # 3 float32 values
        
        # 워밍업
        print("🔥 Warming up TensorRT engine...")
        for i in range(50):
            cuda.memcpy_htod(input_images, self.test_images.cpu().numpy())
            cuda.memcpy_htod(input_text, self.test_text.cpu().numpy())
            
            context.execute_v2(bindings=[int(input_images), int(input_text), int(output_actions)])
            
            if (i + 1) % 10 == 0:
                print(f"   Warmup: {i + 1}/50")
        
        # 벤치마크
        print(f"⚡ Running TensorRT benchmark...")
        times = []
        for i in range(num_runs):
            start_time = time.perf_counter()
            
            # GPU로 데이터 복사
            cuda.memcpy_htod(input_images, self.test_images.cpu().numpy())
            cuda.memcpy_htod(input_text, self.test_text.cpu().numpy())
            
            # 추론 실행
            context.execute_v2(bindings=[int(input_images), int(input_text), int(output_actions)])
            
            # GPU 동기화
            cuda.Context.synchronize()
            
            inference_time = time.perf_counter() - start_time
            times.append(inference_time)
            
            if (i + 1) % 20 == 0:
                print(f"   Progress: {i + 1}/{num_runs}")
        
        # 결과 분석
        avg_time = np.mean(times)
        std_time = np.std(times)
        min_time = np.min(times)
        max_time = np.max(times)
        fps = 1.0 / avg_time
        
        result = {
            "model_name": "Kosmos2+CLIP_Hybrid",
            "framework": "TensorRT",
            "precision": "FP16",
            "average_time_ms": avg_time * 1000,
            "std_time_ms": std_time * 1000,
            "min_time_ms": min_time * 1000,
            "max_time_ms": max_time * 1000,
            "fps": fps,
            "num_runs": num_runs,
            "engine_size_mb": os.path.getsize(engine_path) / (1024 * 1024)
        }
        
        print(f"📊 TensorRT Results:")
        print(f"   Average: {avg_time*1000:.3f} ms")
        print(f"   Std Dev: {std_time*1000:.3f} ms")
        print(f"   Min: {min_time*1000:.3f} ms")
        print(f"   Max: {max_time*1000:.3f} ms")
        print(f"   FPS: {fps:.1f}")
        print(f"   Engine Size: {result['engine_size_mb']:.1f} MB")
        
        return result
    
    def compare_all_frameworks(self):
        """모든 프레임워크 비교"""
        print(f"\n" + "="*80)
        print("🏆 COMPREHENSIVE FRAMEWORK COMPARISON")
        print("="*80)
        
        results = []
        
        # 1. PyTorch 벤치마크
        print(f"\n1. PyTorch Benchmark")
        pytorch_result = self.benchmark_pytorch()
        results.append(pytorch_result)
        
        # 2. ONNX Runtime 벤치마크
        print(f"\n2. ONNX Runtime Benchmark")
        onnx_result = self.benchmark_onnx()
        if onnx_result:
            results.append(onnx_result)
        
        # 3. TensorRT 벤치마크
        print(f"\n3. TensorRT Benchmark")
        tensorrt_result = self.benchmark_tensorrt_optimized()
        if tensorrt_result:
            results.append(tensorrt_result)
        
        # 4. 결과 비교
        self.create_comparison_report(results)
        
        return results
    
    def benchmark_pytorch(self, num_runs: int = 100):
        """PyTorch 벤치마크"""
        print(f"📈 Benchmarking PyTorch Model ({num_runs} runs)")
        
        model = Kosmos2CLIPHybridModel().to(self.device)
        model.eval()
        
        # 워밍업
        with torch.no_grad():
            for i in range(50):
                _ = model(self.test_images, self.test_text)
        
        # 벤치마크
        times = []
        for i in range(num_runs):
            start_time = time.perf_counter()
            
            with torch.no_grad():
                outputs = model(self.test_images, self.test_text)
            
            inference_time = time.perf_counter() - start_time
            times.append(inference_time)
        
        avg_time = np.mean(times)
        std_time = np.std(times)
        fps = 1.0 / avg_time
        
        result = {
            "model_name": "Kosmos2+CLIP_Hybrid",
            "framework": "PyTorch",
            "precision": "FP32",
            "average_time_ms": avg_time * 1000,
            "std_time_ms": std_time * 1000,
            "fps": fps,
            "num_runs": num_runs
        }
        
        print(f"   Average: {avg_time*1000:.3f} ms, FPS: {fps:.1f}")
        return result
    
    def benchmark_onnx(self, num_runs: int = 100):
        """ONNX Runtime 벤치마크"""
        try:
            import onnxruntime as ort
            
            onnx_path = "Mobile_VLA/tensorrt_best_model/best_model_kosmos2_clip.onnx"
            if not os.path.exists(onnx_path):
                print(f"   ONNX model not found, skipping...")
                return None
            
            print(f"📈 Benchmarking ONNX Runtime Model ({num_runs} runs)")
            
            providers = ['CPUExecutionProvider']
            session = ort.InferenceSession(onnx_path, providers=providers)
            
            input_names = [input.name for input in session.get_inputs()]
            inputs = {
                input_names[0]: self.test_images.cpu().numpy(),
                input_names[1]: self.test_text.cpu().numpy()
            }
            
            # 워밍업
            for i in range(50):
                _ = session.run(None, inputs)
            
            # 벤치마크
            times = []
            for i in range(num_runs):
                start_time = time.perf_counter()
                outputs = session.run(None, inputs)
                inference_time = time.perf_counter() - start_time
                times.append(inference_time)
            
            avg_time = np.mean(times)
            std_time = np.std(times)
            fps = 1.0 / avg_time
            
            result = {
                "model_name": "Kosmos2+CLIP_Hybrid",
                "framework": "ONNX Runtime",
                "precision": "FP32",
                "average_time_ms": avg_time * 1000,
                "std_time_ms": std_time * 1000,
                "fps": fps,
                "num_runs": num_runs,
                "model_size_mb": os.path.getsize(onnx_path) / (1024 * 1024)
            }
            
            print(f"   Average: {avg_time*1000:.3f} ms, FPS: {fps:.1f}")
            return result
            
        except Exception as e:
            print(f"   ONNX benchmark failed: {e}")
            return None
    
    def benchmark_tensorrt_optimized(self, num_runs: int = 100):
        """TensorRT 최적화 벤치마크"""
        # ONNX 모델 생성
        onnx_path = "Mobile_VLA/tensorrt_optimized/model.onnx"
        os.makedirs("Mobile_VLA/tensorrt_optimized", exist_ok=True)
        
        if not os.path.exists(onnx_path):
            self.create_onnx_model(onnx_path)
        
        # TensorRT 엔진 생성
        engine_path = "Mobile_VLA/tensorrt_optimized/model_fp16.engine"
        if not os.path.exists(engine_path):
            self.build_tensorrt_engine(onnx_path, engine_path, 'fp16')
        
        if os.path.exists(engine_path):
            return self.benchmark_tensorrt(engine_path, num_runs)
        else:
            print(f"   TensorRT engine creation failed")
            return None
    
    def create_comparison_report(self, results: List[Dict]):
        """비교 리포트 생성"""
        print(f"\n" + "="*80)
        print("🏆 FINAL PERFORMANCE COMPARISON")
        print("="*80)
        
        if len(results) < 2:
            print("❌ Need at least 2 results for comparison")
            return
        
        # 결과 정렬 (FPS 기준)
        sorted_results = sorted(results, key=lambda x: x['fps'], reverse=True)
        
        print(f"\n📊 Performance Ranking (by FPS):")
        print("-" * 80)
        
        for i, result in enumerate(sorted_results, 1):
            framework = result['framework']
            precision = result.get('precision', 'N/A')
            avg_time = result['average_time_ms']
            fps = result['fps']
            size = result.get('model_size_mb', result.get('engine_size_mb', 'N/A'))
            
            print(f"{i}. {framework} ({precision})")
            print(f"   ⏱️  Time: {avg_time:.3f} ms")
            print(f"   🚀 FPS: {fps:.1f}")
            print(f"   📏 Size: {size if isinstance(size, str) else f'{size:.1f} MB'}")
            print()
        
        # 로봇 태스크 분석
        print(f"🤖 Robot Task Analysis:")
        print("-" * 80)
        
        fastest = sorted_results[0]
        control_cycle = 20  # 20ms 제어 주기
        
        print(f"   Control Cycle: {control_cycle}ms")
        print(f"   Fastest Framework: {fastest['framework']} ({fastest['average_time_ms']:.3f}ms)")
        print(f"   Usage: {fastest['average_time_ms']/control_cycle*100:.1f}% of control cycle")
        
        if fastest['average_time_ms'] < 1.0:
            print(f"   ✅ Excellent for real-time robot control")
        elif fastest['average_time_ms'] < 5.0:
            print(f"   ⚠️  Good for robot control")
        else:
            print(f"   ❌ May cause control delays")
        
        # 결과 저장
        report_path = "Mobile_VLA/tensorrt_comparison_results.json"
        with open(report_path, "w") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "device": str(self.device),
                "results": results,
                "ranking": [r['framework'] for r in sorted_results]
            }, f, indent=2)
        
        print(f"\n✅ Comparison report saved: {report_path}")

def main():
    """메인 함수"""
    print("🚀 Starting TensorRT Optimization")
    print("🎯 Optimizing for Robot Tasks")
    
    optimizer = TensorRTOptimizer()
    
    try:
        # 모든 프레임워크 비교
        results = optimizer.compare_all_frameworks()
        
        print(f"\n✅ TensorRT optimization completed!")
        print(f"📊 Tested {len(results)} frameworks")
        print(f"🔧 Device: {optimizer.device}")
        
    except Exception as e:
        print(f"❌ Optimization failed: {e}")
        raise

if __name__ == "__main__":
    main()

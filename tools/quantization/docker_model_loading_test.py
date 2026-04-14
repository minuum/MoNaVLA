#!/usr/bin/env python3
"""
Docker 컨테이너에서 실제 모델 로딩 테스트
"""

import subprocess
import json
import os

def run_docker_command(command: str) -> dict:
    """Docker 명령어 실행 및 결과 반환"""
    try:
        print(f"🔧 Running: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': 'Command timed out after 5 minutes',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }

def test_model_loading_in_docker():
    """Docker 컨테이너에서 모델 로딩 테스트"""
    print("🚀 Testing model loading in Docker container")
    print("=" * 80)
    
    # 테스트할 모델들
    models = [
        "Mobile_VLA/results/simple_clip_lstm_results_extended/best_simple_clip_lstm_model.pth",
        "Mobile_VLA/results/simple_lstm_results_extended/best_simple_lstm_model.pth",
        "Mobile_VLA/results/simple_lstm_results_extended/final_simple_lstm_model.pth"
    ]
    
    results = {}
    
    for model_path in models:
        model_name = os.path.basename(model_path).replace('.pth', '')
        print(f"\n🔍 Testing model: {model_name}")
        print("-" * 60)
        
        # 1. 파일 존재 확인
        print("1️⃣ Checking file existence...")
        check_file_cmd = f'docker exec -it mobile_vla_robovlms_final bash -c "ls -la /workspace/vla/{model_path}"'
        file_check = run_docker_command(check_file_cmd)
        
        if not file_check['success']:
            print(f"❌ File not found in Docker container: {file_check['stderr']}")
            results[model_name] = {
                'status': 'File Not Found',
                'error': file_check['stderr'],
                'file_check': file_check
            }
            continue
        
        print(f"✅ File exists in Docker container")
        print(f"   Output: {file_check['stdout']}")
        
        # 2. 파일 크기 확인
        print("2️⃣ Checking file size...")
        size_cmd = f'docker exec -it mobile_vla_robovlms_final bash -c "stat -c %s /workspace/vla/{model_path}"'
        size_check = run_docker_command(size_cmd)
        
        if size_check['success']:
            file_size_mb = int(size_check['stdout'].strip()) / (1024 * 1024)
            print(f"✅ File size: {file_size_mb:.1f}MB")
        else:
            print(f"❌ Size check failed: {size_check['stderr']}")
        
        # 3. PyTorch 로딩 테스트
        print("3️⃣ Testing PyTorch loading...")
        
        # 간단한 로딩 테스트
        simple_load_test = f'''
import torch
import sys

try:
    print("Loading checkpoint...")
    checkpoint_path = "/workspace/vla/{model_path}"
    checkpoint = torch.load(checkpoint_path, map_location='cpu')
    print("✅ Checkpoint loaded successfully!")
    print(f"Checkpoint keys: {list(checkpoint.keys())}")
    
    if 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
        print(f"Model state dict keys: {len(state_dict)}")
        print(f"First few keys: {list(state_dict.keys())[:5]}")
    
    if 'val_mae' in checkpoint:
        print(f"Validation MAE: {checkpoint['val_mae']}")
    
    if 'epoch' in checkpoint:
        print(f"Training epoch: {checkpoint['epoch']}")
    
    print("✅ All checks passed!")
    
except Exception as e:
    print(f"❌ Error loading checkpoint: {{e}}")
    print(f"Error type: {{type(e).__name__}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
        
        load_cmd = f'docker exec -it mobile_vla_robovlms_final bash -c "cd /workspace/vla && python3 -c \'{simple_load_test}\'"'
        load_test = run_docker_command(load_cmd)
        
        if load_test['success']:
            print("✅ PyTorch loading successful!")
            print(f"   Output: {load_test['stdout']}")
            results[model_name] = {
                'status': 'Success',
                'file_check': file_check,
                'size_check': size_check,
                'load_test': load_test
            }
        else:
            print("❌ PyTorch loading failed!")
            print(f"   Error: {load_test['stderr']}")
            results[model_name] = {
                'status': 'Load Failed',
                'error': load_test['stderr'],
                'file_check': file_check,
                'size_check': size_check,
                'load_test': load_test
            }
    
    return results

def test_onnx_runtime_availability():
    """ONNX Runtime 가용성 테스트"""
    print("\n🧪 Testing ONNX Runtime availability...")
    print("=" * 60)
    
    onnx_test_script = '''
import sys

try:
    import onnxruntime as ort
    print("✅ ONNX Runtime imported successfully!")
    print(f"Version: {ort.__version__}")
    print(f"Available providers: {ort.get_available_providers()}")
except ImportError as e:
    print(f"❌ ONNX Runtime not available: {e}")
    print("Available packages:")
    import pkg_resources
    installed_packages = [d.project_name for d in pkg_resources.working_set]
    onnx_packages = [pkg for pkg in installed_packages if 'onnx' in pkg.lower()]
    print(f"ONNX-related packages: {onnx_packages}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
'''
    
    onnx_cmd = f'docker exec -it mobile_vla_robovlms_final bash -c "python3 -c \'{onnx_test_script}\'"'
    onnx_test = run_docker_command(onnx_cmd)
    
    return onnx_test

def test_pytorch_availability():
    """PyTorch 가용성 테스트"""
    print("\n🔥 Testing PyTorch availability...")
    print("=" * 60)
    
    pytorch_test_script = '''
import torch
print(f"✅ PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU count: {torch.cuda.device_count()}")
    print(f"Current device: {torch.cuda.current_device()}")
    print(f"Device name: {torch.cuda.get_device_name(0)}")
'''
    
    pytorch_cmd = f'docker exec -it mobile_vla_robovlms_final bash -c "python3 -c \'{pytorch_test_script}\'"'
    pytorch_test = run_docker_command(pytorch_cmd)
    
    return pytorch_test

def create_comprehensive_report(model_results, onnx_test, pytorch_test):
    """종합 보고서 생성"""
    print("\n📋 COMPREHENSIVE DOCKER TEST REPORT")
    print("=" * 80)
    
    # 모델 로딩 결과
    print("\n🔍 **Model Loading Results**:")
    for model_name, result in model_results.items():
        print(f"\n🏷️  **{model_name}**:")
        print(f"   - Status: {result['status']}")
        
        if result['status'] == 'Success':
            print(f"   - ✅ Loaded successfully in Docker")
        elif result['status'] == 'Load Failed':
            print(f"   - ❌ Failed to load: {result.get('error', 'Unknown error')}")
        elif result['status'] == 'File Not Found':
            print(f"   - ❌ File not found in Docker container")
    
    # ONNX Runtime 테스트 결과
    print(f"\n🧪 **ONNX Runtime Test**:")
    if onnx_test['success']:
        print(f"   - ✅ ONNX Runtime available")
        print(f"   - Output: {onnx_test['stdout']}")
    else:
        print(f"   - ❌ ONNX Runtime not available")
        print(f"   - Error: {onnx_test['stderr']}")
    
    # PyTorch 테스트 결과
    print(f"\n🔥 **PyTorch Test**:")
    if pytorch_test['success']:
        print(f"   - ✅ PyTorch available")
        print(f"   - Output: {pytorch_test['stdout']}")
    else:
        print(f"   - ❌ PyTorch not available")
        print(f"   - Error: {pytorch_test['stderr']}")
    
    # 문제 진단
    print(f"\n🔍 **Problem Diagnosis**:")
    
    successful_models = [name for name, result in model_results.items() if result['status'] == 'Success']
    failed_models = [name for name, result in model_results.items() if result['status'] != 'Success']
    
    if len(successful_models) == len(model_results):
        print("✅ All models loaded successfully in Docker!")
        print("   - Files are not damaged")
        print("   - Docker environment is working")
        print("   - Issue might be in the application code")
    elif len(failed_models) > 0:
        print(f"⚠️  {len(failed_models)} out of {len(model_results)} models failed to load")
        print("   - Possible file path issues")
        print("   - Possible permission issues")
        print("   - Possible PyTorch version incompatibility")
    
    if not onnx_test['success']:
        print("❌ ONNX Runtime is not available in Docker container")
        print("   - This explains the 'No module named onnxruntime' error")
        print("   - Solution: Install ONNX Runtime or use PyTorch-only approach")

def main():
    """메인 함수"""
    print("🚀 Docker Model Loading Test")
    print("🎯 Testing why models were considered damaged")
    
    try:
        # 1. 모델 로딩 테스트
        model_results = test_model_loading_in_docker()
        
        # 2. ONNX Runtime 가용성 테스트
        onnx_test = test_onnx_runtime_availability()
        
        # 3. PyTorch 가용성 테스트
        pytorch_test = test_pytorch_availability()
        
        # 4. 종합 보고서 생성
        create_comprehensive_report(model_results, onnx_test, pytorch_test)
        
        # 5. 결과 저장
        output_path = "Mobile_VLA/docker_model_loading_test_results.json"
        with open(output_path, "w") as f:
            json.dump({
                'model_results': model_results,
                'onnx_test': onnx_test,
                'pytorch_test': pytorch_test,
                'timestamp': '2024-08-22'
            }, f, indent=2)
        
        print(f"\n✅ Test results saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    main()

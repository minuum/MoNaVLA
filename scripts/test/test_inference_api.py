#!/usr/bin/env python3
"""
Inference API 자동 테스트 스크립트
FastAPI 서버의 모든 엔드포인트를 자동으로 테스트

실행: python3 scripts/test_inference_api.py
"""

import requests
import base64
import json
import time
from PIL import Image
from io import BytesIO
from pathlib import Path


class InferenceAPITester:
    """추론 API 자동 테스트"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        
        # API Key 설정
        import os
        self.api_key = os.getenv("VLA_API_KEY")
        if not self.api_key:
            print("⚠️ Warning: VLA_API_KEY not set. Some tests may fail.")
        
        self.headers = {
            "X-API-Key": self.api_key
        } if self.api_key else {}
        
    def print_section(self, title: str):
        """섹션 출력"""
        print("\n" + "="*60)
        print(f"  {title}")
        print("="*60)
        
    def test_root(self) -> bool:
        """Root 엔드포인트 테스트"""
        self.print_section("1. Testing GET /")
        
        try:
            response = requests.get(f"{self.base_url}/")
            
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            success = response.status_code == 200
            self.results.append(("GET /", success))
            
            return success
            
        except Exception as e:
            print(f"❌ Error: {e}")
            self.results.append(("GET /", False))
            return False
    
    def test_health(self) -> bool:
        """Health check 테스트"""
        self.print_section("2. Testing GET /health")
        
        try:
            response = requests.get(f"{self.base_url}/health")
            
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            success = response.status_code == 200
            self.results.append(("GET /health", success))
            
            return success
            
        except Exception as e:
            print(f"❌ Error: {e}")
            self.results.append(("GET /health", False))
            return False
    
    def test_test_endpoint(self) -> bool:
        """Test 엔드포인트 테스트"""
        self.print_section("3. Testing GET /test")
        
        try:
            response = requests.get(f"{self.base_url}/test", headers=self.headers)
            
            print(f"Status: {response.status_code}")
            
            data = response.json()
            print(f"Instruction: {data.get('instruction', 'N/A')}")
            print(f"Action: {data.get('action', 'N/A')}")
            print(f"Note: {data.get('note', 'N/A')}")
            
            success = response.status_code == 200
            self.results.append(("GET /test", success))
            
            return success
            
        except Exception as e:
            print(f"❌ Error: {e}")
            self.results.append(("GET /test", False))
            return False
    
    def create_test_image(self) -> str:
        """테스트용 이미지 생성 (base64)"""
        # Create red dummy image
        img = Image.new('RGB', (1280, 720), color=(255, 0, 0))
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return img_base64
    
    def test_predict_left(self) -> bool:
        """Predict 엔드포인트 테스트 (Left)"""
        self.print_section("4. Testing POST /predict (Left)")
        
        try:
            # Create request
            img_base64 = self.create_test_image()
            
            payload = {
                "image": img_base64,
                "instruction": "Navigate around obstacles and reach the front of the beverage bottle on the left"
            }
            
            print(f"Instruction: {payload['instruction']}")
            print(f"Image size: {len(img_base64)} characters")
            
            # Send request
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/predict",
                json=payload,
                headers=self.headers,
                timeout=120
            )
            latency = (time.time() - start_time) * 1000
            
            print(f"\nStatus: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Action: {data['action']}")
                print(f"Model Latency: {data.get('latency_ms', 'N/A')} ms")
                print(f"Total Latency: {latency:.1f} ms")
                print(f"Model: {data.get('model_name', 'N/A')}")
                
                success = True
            else:
                print(f"Error: {response.text}")
                success = False
            
            self.results.append(("POST /predict (Left)", success))
            return success
            
        except Exception as e:
            print(f"❌ Error: {e}")
            self.results.append(("POST /predict (Left)", False))
            return False
    
    def test_predict_right(self) -> bool:
        """Predict 엔드포인트 테스트 (Right)"""
        self.print_section("5. Testing POST /predict (Right)")
        
        try:
            img_base64 = self.create_test_image()
            
            payload = {
                "image": img_base64,
                "instruction": "Navigate around obstacles and reach the front of the beverage bottle on the right"
            }
            
            print(f"Instruction: {payload['instruction']}")
            
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/predict",
                json=payload,
                headers=self.headers,
                timeout=120
            )
            latency = (time.time() - start_time) * 1000
            
            print(f"\nStatus: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Action: {data['action']}")
                print(f"Total Latency: {latency:.1f} ms")
                
                success = True
            else:
                print(f"Error: {response.text}")
                success = False
            
            self.results.append(("POST /predict (Right)", success))
            return success
            
        except Exception as e:
            print(f"❌ Error: {e}")
            self.results.append(("POST /predict (Right)", False))
            return False
    
    def print_summary(self):
        """테스트 결과 요약"""
        self.print_section("TEST SUMMARY")
        
        total = len(self.results)
        passed = sum(1 for _, success in self.results if success)
        failed = total - passed
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: ✅ {passed}")
        print(f"Failed: ❌ {failed}")
        print(f"\nSuccess Rate: {passed/total*100:.1f}%\n")
        
        print("Detailed Results:")
        for endpoint, success in self.results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status}  {endpoint}")
        
        print()
        
        return passed == total
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "🧪 INFERENCE API TEST SUITE ".center(60, "="))
        print(f"Target: {self.base_url}\n")
        
        # Run tests
        self.test_root()
        self.test_health()
        self.test_test_endpoint()
        self.test_predict_left()
        self.test_predict_right()
        
        # Summary
        all_passed = self.print_summary()
        
        if all_passed:
            print("✅ All tests passed!")
            return 0
        else:
            print("❌ Some tests failed!")
            return 1


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Inference API")
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="API base URL"
    )
    
    args = parser.parse_args()
    
    tester = InferenceAPITester(base_url=args.url)
    exit_code = tester.run_all_tests()
    
    exit(exit_code)


if __name__ == "__main__":
    main()

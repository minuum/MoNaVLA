#!/usr/bin/env python3
"""
VLA API Client for Robot Server
A5000 서버의 FastAPI를 호출하여 action 예측

사용법:
    export VLA_API_SERVER="http://192.168.1.100:8000"
    python3 vla_api_client.py
"""

import requests
import base64
import numpy as np
from io import BytesIO
from PIL import Image
import os
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VLAClient:
    """A5000 FastAPI 클라이언트"""
    
    def __init__(self, api_server: str = None, api_key: str = None):
        """
        Args:
            api_server: A5000 서버 URL (예: "http://192.168.1.100:8000")
            api_key: API Key (보안 인증용)
        """
        self.api_server = api_server or os.getenv(
            "VLA_API_SERVER",
            "http://localhost:8000"  # 기본값
        )
        
        self.api_key = api_key or os.getenv("VLA_API_KEY")
        
        if not self.api_key:
            logger.warning("⚠️  VLA_API_KEY 환경 변수가 설정되지 않았습니다!")
            logger.warning("   일부 엔드포인트는 API Key가 필요합니다")
        
        logger.info(f"🔗 VLA API 서버: {self.api_server}")
        if self.api_key:
            logger.info(f"🔑 API Key: {self.api_key[:10]}...")
        
        # Health check
        self._check_server()
        
    def _check_server(self):
        """서버 상태 확인"""
        try:
            response = requests.get(
                f"{self.api_server}/health",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ 서버 연결 성공")
                logger.info(f"   Model loaded: {data.get('model_loaded')}")
                logger.info(f"   Device: {data.get('device')}")
                
                # GPU 정보 (있으면)
                gpu_info = data.get('gpu_memory')
                if gpu_info:
                    logger.info(f"   GPU: {gpu_info.get('device_name', 'N/A')}")
                    logger.info(f"   VRAM: {gpu_info.get('allocated_gb', 0):.2f}GB")
            else:
                logger.warning(f"⚠️  서버 응답 이상: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ 서버 연결 실패: {self.api_server}")
            logger.error("   A5000 서버의 API가 실행 중인지 확인하세요")
            logger.error("   방화벽 포트 8000이 열려있는지 확인하세요")
            raise
        except Exception as e:
            logger.error(f"❌ 오류 발생: {e}")
            raise
    
    def predict(
        self,
        image: np.ndarray,
        instruction: str = "Navigate around obstacles and reach the front of the beverage bottle on the left"
    ) -> tuple[np.ndarray, float]:
        """
        이미지로부터 action 예측
        
        Args:
            image: (H, W, 3) RGB numpy array
            instruction: Language instruction
            
        Returns:
            (action, latency_ms): action과 latency
        """
        # PIL Image로 변환
        if image.dtype != np.uint8:
            image = (image * 255).astype(np.uint8)
        
        pil_img = Image.fromarray(image)
        
        # Base64 인코딩
        buffer = BytesIO()
        pil_img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Headers에 API Key 추가
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        # API 호출
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.api_server}/predict",
                json={
                    "image": img_base64,
                    "instruction": instruction
                },
                headers=headers,
                timeout=10
            )
            
            total_latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                action = np.array(data['action'])
                model_latency = data.get('latency_ms', 0)
                
                logger.debug(f"Model latency: {model_latency:.1f}ms")
                logger.debug(f"Total latency: {total_latency:.1f}ms")
                logger.debug(f"Action: {action}")
                
                return action, total_latency
            elif response.status_code == 403:
                logger.error("❌ API Key 인증 실패!")
                logger.error("   VLA_API_KEY 환경 변수를 확인하세요")
                raise RuntimeError("Authentication failed: Invalid API Key")
            else:
                raise RuntimeError(
                    f"API 호출 실패: {response.status_code}\n{response.text}"
                )
                
        except requests.exceptions.Timeout:
            logger.error("⏱️  API 타임아웃 (10초 초과)")
            raise
        except requests.exceptions.ConnectionError:
            logger.error("❌ 네트워크 연결 끊김")
            raise


def test_client():
    """클라이언트 테스트"""
    print("\n" + "="*60)
    print("🧪 VLA API Client 테스트")
    print("="*60 + "\n")
    
    # 클라이언트 생성
    client = VLAClient()
    
    print("\n📝 테스트 케이스:")
    print("-" * 60)
    
    # 테스트용 더미 이미지
    dummy_image = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    
    test_cases = [
        ("Left", "Navigate around obstacles and reach the front of the beverage bottle on the left"),
        ("Right", "Navigate around obstacles and reach the front of the beverage bottle on the right"),
        ("Target-Only", "Navigate directly to the gray basket"),
    ]
    
    for name, instruction in test_cases:
        print(f"\n{name} instruction:")
        print(f"  {instruction}")
        
        try:
            action, latency = client.predict(dummy_image, instruction)
            
            print(f"\n  결과:")
            print(f"    Action: {action}")
            print(f"    linear_x: {action[0]:.3f} m/s")
            print(f"    linear_y: {action[1]:.3f} m/s")
            print(f"    Latency: {latency:.1f} ms")
            print(f"    {'✅ Success' if latency < 100 else '⚠️  Slow (>100ms)'}")
            
        except Exception as e:
            print(f"  ❌ 실패: {e}")
    
    print("\n" + "="*60)
    print("✅ 테스트 완료")
    print("="*60 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="VLA API Client")
    parser.add_argument(
        "--server",
        type=str,
        help="API 서버 URL (기본: 환경변수 VLA_API_SERVER)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="테스트 모드 실행"
    )
    
    args = parser.parse_args()
    
    if args.server:
        os.environ["VLA_API_SERVER"] = args.server
    
    if args.test or not args.server:
        # 기본적으로 테스트 실행
        test_client()
    else:
        # 서버 지정만 하고 종료
        print(f"VLA_API_SERVER set to: {args.server}")

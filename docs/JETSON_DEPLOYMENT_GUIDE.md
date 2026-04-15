# 🚀 Jetson Deployment Guide for Mobile VLA

**최종 업데이트**: 2026-02-11  
**대상 모델**: **EXP-17 (Champion Model)**  
**목적**: 빌리 서버에서 학습 완료된 VLA 모델을 젯슨 오린(Jetson Orin)으로 이전하고 로컬에서 실행하는 가이드

---

## 1. 📂 필수 이전 파일 리스트 (Bills Server → Jetson)

| 구분 | 빌리 서버 파일 경로 | 젯슨 로컬 권장 경로 |
| :--- | :--- | :--- |
| **Weights** | `runs/unified_regression_win12/kosmos/mobile_vla_exp17_win8_k1/2026-02-10/exp17_win8_k1/epoch=epoch=09-val_loss=val_loss=0.0013.ckpt` | `~/vla/checkpoints/exp17_win8_final.ckpt` |
| **Config** | `Mobile_VLA/configs/mobile_vla_exp17_win8_k1.json` | `~/vla/configs/exp17_win8.json` |
| **Source** | `robovlms/`, `Mobile_VLA/` 폴더 전체 | `~/vla/` 아래 동일 구조 유지 |
| **Backbone** | `~/.cache/huggingface/hub/` (Kosmos-2 관련) | 젯슨의 동일한 캐시 경로 |

---

## 2. 🚛 파일 전송 방법 (rsync 권장)

빌리 서버 터미널에서 실행하여 젯슨으로 한 번에 쏩니다. (IP 주소 확인 필요)

```bash
# 코드 및 설정 전송
rsync -avz --exclude '.git' --exclude 'runs' ~/25-1kp/vla/ [젯슨_아이디]@[젯슨_IP]:~/vla/

# 챔피언 체크포인트만 별도 전송
rsync -avz ~/25-1kp/vla/runs/unified_regression_win12/kosmos/mobile_vla_exp17_win8_k1/2026-02-10/exp17_win8_k1/epoch=epoch=09-val_loss=val_loss=0.0013.ckpt [젯슨_아이디]@[젯슨_IP]:~/vla/checkpoints/
```

---

## 3. 💻 젯슨 전용 로컬 추론 코드 샘플

FastAPI 종속성을 제거하고 로컬에서 가장 빠르게 동작하는 구조입니다.

```python
import torch
import numpy as np
from PIL import Image
# 프로젝트 구조에 따른 import 경로 확인 필요
from robovlms.model.backbone.base_backbone import MobileVLABackbone 

class MobileVLALocalInference:
    def __init__(self, checkpoint_path, config_path):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 1. Config 로드
        import json
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # 2. 모델 로드 (Head 부분 가중치 로딩)
        # _load_model() 메서드는 api_server.py의 로직을 참고하여 구현
        self.model = self._setup_model(checkpoint_path)
        self.model.to(self.device).eval()
        
        self.frame_count = 0 
        self.image_history = []
        self.window_size = self.config.get('window_size', 8)

    def _setup_model(self, path):
        # [주의] _load_model 로직 그대로 사용하되 FastAPI 로거만 제거
        pass

    def predict(self, pil_image, instruction="Navigate to the basket"):
        self.frame_count += 1
        
        # ✅ Safety Heuristic: 첫 프레임 무조건 정지
        if self.frame_count == 1:
            return np.array([0.0, 0.0])
            
        # 3.2D Velocity 추론 로직 (Inference)
        with torch.no_grad():
            # (api_server.py의 run_inference 로직 참고)
            pass
        return action
```

---

## 4. ⚠️ 젯슨 배포 시 체크리스트

1.  **메모리**: Kosmos-2 로딩 시 VRAM이 약 4GB 소요됩니다. 젯슨의 `tegrastats`로 체크하세요.
2.  **전처리**: PIL 대신 `torchvision.transforms`를 사용하여 GPU 가속 전처리를 권장합니다.
3.  **에피소드 종료**: 로봇 작업이 끝날 때마다 반드시 `frame_count = 0` 및 `image_history = []` 처리를 해주어야 다음 주행이 안전하게 시작됩니다.
4.  **FP16**: 추론 엔진 로드 시 `torch_dtype=torch.float16` 옵션을 확인하세요. (Orin에서는 FP16이 가장 효율적입니다.)

---

## 5. 🛠️ 트러블슈팅

- **Backbone 로딩 이슈**: 젯슨이 오프라인일 경우 HuggingFace에서 Kosmos-2를 못 가져올 수 있습니다. 빌리 서버의 캐시(`~/.cache/huggingface`)를 통째로 옮기세요.
- **Path Mismatch**: `config.json` 내부에 하드코딩된 경로가 있다면 젯슨 경로에 맞춰 수정하십시오.

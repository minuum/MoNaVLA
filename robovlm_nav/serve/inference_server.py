"""
FastAPI Inference Server for Mobile VLA
교수님 서버에서 모델 호출을 위한 API 서버

입력: 이미지 + Language instruction
출력: 2DOF actions [linear_x, linear_y]

보안: API Key 인증
"""

import sys
import os
import time
import io
import base64
import logging
import secrets
import json
from typing import List, Optional, Literal, Any
from pathlib import Path
import gc
import copy

# 1. Add project root and RoboVLMs to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Handle scripts path for inference_logger
scripts_path = os.path.join(project_root, 'scripts')
if os.path.exists(scripts_path) and scripts_path not in sys.path:
    sys.path.append(scripts_path)

try:
    from inference_logger import get_logger
    logger_instance = get_logger()
except ImportError:
    logger_instance = None

# Handle RoboVLMs path (try both RoboVLMs and RoboVLMs_upstream and third_party/RoboVLMs)
for root_name in ['RoboVLMs', 'RoboVLMs_upstream', 'third_party/RoboVLMs']:
    p = os.path.join(project_root, root_name)
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

# Third-party imports
import torch
import numpy as np
import cv2
from PIL import Image
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

# Project imports
try:
    from robovlm_nav.serve.action_buffer import ActionBuffer
    from robovlms.data.data_utils import unnoramalize_action
except ImportError as e:
    print(f"FATAL ERROR: Failed to import project modules. sys.path: {sys.path}")
    raise e

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mobile VLA Inference API", version="1.0.0")

# API Key 설정
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# 환경 변수에서 API Key 읽기 (없으면 생성)
def get_api_key():
    api_key = os.getenv("VLA_API_KEY")
    if not api_key:
        # API Key 자동 생성 및 출력
        api_key = secrets.token_urlsafe(32)
        logger.warning("="*60)
        logger.warning("⚠️  VLA_API_KEY 환경 변수가 없습니다!")
        logger.warning(f"생성된 API Key: {api_key}")
        logger.warning("다음 명령어로 저장하세요:")
        logger.warning(f'export VLA_API_KEY="{api_key}"')
        logger.warning("="*60)
    return api_key

VALID_API_KEY = get_api_key()

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """API Key 검증"""
    if api_key != VALID_API_KEY:
        logger.warning(f"❌ 인증 실패: {api_key[:10]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )
    return api_key

# Global model instance (lazy loading)
model_instance = None


class InferenceRequest(BaseModel):
    """추론 요청 스키마"""
    image: str  # base64 encoded image
    instruction: str  # Language instruction
    strategy: Literal["chunk_reuse", "receding_horizon"] = "chunk_reuse"  # Inference strategy
    

class InferenceResponse(BaseModel):
    """추론 응답 스키마"""
    action: List[float]  # [linear_x, linear_y]
    latency_ms: float  # Inference latency in milliseconds
    model_name: str
    strategy: str  # Inference strategy used
    source: str  # "inferred" or "reused"
    buffer_status: dict  # Buffer status for chunk_reuse
    

class MobileVLAInference:
    """Mobile VLA 추론 파이프라인"""
    
    def _load_config_recursive(self, path: str) -> dict:
        """Load JSON config and recursively merge with parent if specified."""
        # Handle case where path might be hardcoded to old user
        if "/home/billy/25-1kp/vla" in path:
            path = path.replace("/home/billy/25-1kp/vla", project_root)
            
        if not os.path.exists(path):
            # Try relative to configs dir
            alt_path = os.path.join(project_root, "Mobile_VLA", "configs", os.path.basename(path))
            if os.path.exists(alt_path):
                path = alt_path
                
        with open(path, 'r') as f:
            config = json.load(f)
            
        if "parent" in config and config["parent"]:
            parent_path = config["parent"]
            parent_config = self._load_config_recursive(parent_path)
            # Merge: config values override parent_config values
            # For nested dicts like train_setup, we should do a shallow merge or deep merge?
            # Standard RoboVLMs uses deep_update for some things, but shallow merge is usually enough for top level.
            # Let's do a simple recursive merge for dicts.
            def deep_update(d, u):
                for k, v in u.items():
                    if isinstance(v, dict):
                        d[k] = deep_update(d.get(k, {}), v)
                    else:
                        d[k] = v
                return d
            
            merged = copy.deepcopy(parent_config)
            deep_update(merged, config)
            return merged
        return config

    def __init__(self, checkpoint_path: str, config_path: str, device: str = "cuda", use_quant: Optional[bool] = None):
        """
        Args:
            checkpoint_path: LoRA Fine-tuned 모델 checkpoint 경로
            config_path: Config JSON 파일 경로
            device: "cuda" or "cpu"
            use_quant: Explicitly set quantization (True=INT8, False=FP16). If None, use Env.
        """
        import copy
        self.device = device
        self.checkpoint_path = checkpoint_path
        self.config_path = config_path
        self.model_name = Path(config_path).stem
        
        # Determine quantization mode
        if use_quant is not None:
            self.use_quant = use_quant
        else:
            self.use_quant = os.getenv("VLA_QUANTIZE", "false").lower() == "true"
        
        # Initialize action buffer for chunk_reuse strategy
        self.action_buffer = ActionBuffer(chunk_size=10)
        self.inference_count = 0
        
        logger.info(f"Loading model from {checkpoint_path}")
        logger.info(f"Using device: {device}")
        
        # Load config recursively
        self.config = self._load_config_recursive(config_path)
        self._normalize_config_paths()

        self.inference_mode = "classification" if self.config.get("discrete_action", False) else self._resolve_inference_mode()
        self.class_labels, self.class_action_map, self.class_index_action_map = self._build_classification_map()
        
        # 6-class mapping 강제 보정 (v3 dataset 기준)
        if self.config.get("num_classes") == 6:
            speed = float(self.config.get("classification_speed", 1.15))
            diag = speed * 0.707
            self.class_index_action_map = {
                0: [0.0, 0.0],   # STOP
                1: [speed, 0.0], # FORWARD
                2: [0.0, speed], # LEFT
                3: [0.0, -speed],# RIGHT
                4: [diag, diag], # FL
                5: [diag, -diag] # FR
            }
            logger.info("🎯 Forced 6-class index mapping (STOP/F/L/R/FL/FR)")
        
        # Integration fallback for scale_factor
        self.scale_factor = self.config.get("scale_factor", self.config.get("classification_speed", 1.15))
        
        logger.info(f"✅ [INIT] Inference Mode: {self.inference_mode.upper()}")
        
        # Load model
        self._load_model()
        
        # [OPTIMIZATION] Initialize processor once
        from transformers import AutoProcessor
        self.processor = AutoProcessor.from_pretrained(
            self.config['tokenizer']['pretrained_model_name_or_path']
        )
        logger.info(f"Processor initialized from {self.config['tokenizer']['pretrained_model_name_or_path']}")
        
        logger.info("Model loaded successfully")
        
        # [CRITICAL] 2. Initialize Image History Buffer
        # Prefer explicit root key, then nested experiment settings, then a safe default.
        self.window_size = (
            self.config.get("window_size")
            or self.config.get("act_head", {}).get("window_size")
            or self.config.get("train_dataset", {}).get("window_size")
            or 8
        )
        self.image_history = []
        logger.info(f"✅ Initialized Image History Buffer (Window Size: {self.window_size})")

    def _normalize_config_paths(self) -> None:
        """Normalize relative config paths against project root for stable CWD-independent loading."""
        def _norm_path(raw: Any) -> Any:
            if not isinstance(raw, str) or raw.strip() == "":
                return raw
            val = raw.strip()
            if "://" in val:  # URL / HF repo-like identifiers should remain untouched
                return val
            p = Path(val).expanduser()
            if p.is_absolute():
                return str(p)

            candidates = [
                Path(project_root) / val,
                Path(self.config_path).resolve().parent / val,
                Path.cwd() / val,
            ]
            for c in candidates:
                if c.exists():
                    return str(c.resolve())
            # Fallback: project-root anchored path
            return str((Path(project_root) / val).resolve())

        if "model_path" in self.config:
            self.config["model_path"] = _norm_path(self.config.get("model_path"))
        if "model_config" in self.config:
            self.config["model_config"] = _norm_path(self.config.get("model_config"))
        if "model_load_path" in self.config:
            self.config["model_load_path"] = _norm_path(self.config.get("model_load_path"))

        tokenizer_cfg = self.config.get("tokenizer", {})
        if isinstance(tokenizer_cfg, dict) and "pretrained_model_name_or_path" in tokenizer_cfg:
            tokenizer_cfg["pretrained_model_name_or_path"] = _norm_path(tokenizer_cfg.get("pretrained_model_name_or_path"))

        vlm_cfg = self.config.get("vlm", {})
        if isinstance(vlm_cfg, dict) and "pretrained_model_name_or_path" in vlm_cfg:
            vlm_cfg["pretrained_model_name_or_path"] = _norm_path(vlm_cfg.get("pretrained_model_name_or_path"))

    def _resolve_inference_mode(self) -> str:
        """Resolve runtime inference mode from config."""
        mode = str(self.config.get("inference_mode", "")).strip().lower()
        act_head_type = str(self.config.get("act_head", {}).get("type", "")).lower()
        if mode in {"classification", "regression"}:
            return mode
        if "classification" in act_head_type:
            return "classification"
        return "regression"

    def _build_classification_map(self) -> tuple[List[str], dict[str, List[float]], dict[int, List[float]]]:
        """Build class label/action map for classification inference."""
        default_labels = ["STOP", "FORWARD", "BACKWARD", "LEFT", "RIGHT", "FORWARD_LEFT", "FORWARD_RIGHT", "BACKWARD_LEFT", "BACKWARD_RIGHT"]
        num_classes = int(self.config.get("act_head", {}).get("num_classes", 9))
        labels = self.config.get("class_labels", default_labels[:num_classes])
        if not isinstance(labels, list) or not labels:
            labels = default_labels[:num_classes]
        labels = [str(x).upper() for x in labels]

        speed = float(self.config.get("classification_speed", 1.15))
        diagonal = float(self.config.get("classification_diagonal_speed", speed))
        default_map = {
            "STOP": [0.0, 0.0],
            "FORWARD": [speed, 0.0],
            "BACKWARD": [-speed, 0.0],
            "LEFT": [0.0, speed],
            "RIGHT": [0.0, -speed],
            "FORWARD_LEFT": [diagonal, diagonal],
            "FORWARD_RIGHT": [diagonal, -diagonal],
            "BACKWARD_LEFT": [-diagonal, diagonal],
            "BACKWARD_RIGHT": [-diagonal, -diagonal],
            "FL": [diagonal, diagonal],
            "FR": [diagonal, -diagonal],
            "BL": [-diagonal, diagonal],
            "BR": [-diagonal, -diagonal],
            "F": [speed, 0.0],
            "B": [-speed, 0.0],
            "L": [0.0, speed],
            "R": [0.0, -speed],
        }
        # Index-priority default map (0~8): Stop/F/B/L/R/FL/FR/BL/BR
        default_index_map = {
            0: [0.0, 0.0],
            1: [speed, 0.0],
            2: [-speed, 0.0],
            3: [0.0, speed],
            4: [0.0, -speed],
            5: [diagonal, diagonal],
            6: [diagonal, -diagonal],
            7: [-diagonal, diagonal],
            8: [-diagonal, -diagonal],
        }

        user_map = self.config.get("classification_action_map", {})
        if isinstance(user_map, dict):
            for k, v in user_map.items():
                if isinstance(v, (list, tuple)) and len(v) >= 2:
                    try:
                        idx = int(k)
                        default_index_map[idx] = [float(v[0]), float(v[1])]
                    except (ValueError, TypeError):
                        default_map[str(k).upper()] = [float(v[0]), float(v[1])]

        return labels, default_map, default_index_map

    def _extract_action_tensor(self, action_out: Any) -> Any:
        """Normalize output variants to action/logits tensor."""
        if isinstance(action_out, tuple):
            # Regression heads may return (action, gripper). Classification should not concat.
            if self.inference_mode == "regression":
                if (
                    len(action_out) == 2
                    and isinstance(action_out[0], torch.Tensor)
                    and isinstance(action_out[1], torch.Tensor)
                    and action_out[0].shape[:-1] == action_out[1].shape[:-1]
                ):
                    act_t, grip_t = action_out
                    logger.debug(f"📊 [TENSOR STATS] Actions mean: {act_t.mean():.4f}, Gripper mean: {grip_t.mean():.4f}")
                    return torch.cat(action_out, dim=-1)
            return action_out[0]
        return action_out

    def _decode_classification_action(self, full_chunk: np.ndarray) -> np.ndarray:
        """Convert class logits/prediction to continuous [linear_x, linear_y]."""
        if full_chunk.size == 0:
            return np.array([0.0, 0.0], dtype=np.float32)

        logits = full_chunk[0]
        if logits.ndim == 0:
            class_idx = int(logits)
            score = float(logits)
        elif logits.ndim == 1 and logits.size == 1:
            # Some models may return class index directly as shape (1,)
            class_idx = int(logits[0])
            score = float(logits[0])
        else:
            class_idx = int(np.argmax(logits))
            score = float(logits[class_idx])

        class_name = self.class_labels[class_idx] if class_idx < len(self.class_labels) else f"IDX_{class_idx}"
        mapped = self.class_index_action_map.get(class_idx, self.class_action_map.get(class_name, [0.0, 0.0]))
        action = np.array(mapped, dtype=np.float32)
        logger.info(f"📤 [CLASS ACTION] idx={class_idx}, class={class_name}, score={score:.4f}, action={action.tolist()}")
        return action
        
    def _load_model(self):
        """모델 로딩 (VLA_QUANTIZE=false면 FP16, true면 INT8로 로드)"""
        import sys
        import os
        project_root = os.getenv("VLA_ROOT", "/home/soda/vla")
        # Ensure RoboVLMs is in path
        if project_root not in sys.path:
            sys.path.append(project_root)
            
        def _update_paths(config_dict):
            # soda 서버와 billy 서버의 경로 차이를 모두 동적 대응
            old_roots = ["/home/billy/25-1kp/vla", "/home/soda/vla"]
            fixed_model_base = os.getenv("VLA_MODEL_PATH", os.path.join(project_root, ".vlms"))
            
            for k, v in config_dict.items():
                if isinstance(v, str):
                    # 1순위: 모델 기반 경로 전용 강제 치환 (가장 확실함)
                    if "kosmos-2-patch14-224" in v:
                         config_dict[k] = os.path.join(fixed_model_base, "kosmos-2-patch14-224")
                         continue
                    
                    # 2순위: 기타 일반 경로 치환
                    for old_root in old_roots:
                        if old_root in v:
                             config_dict[k] = v.replace(old_root, project_root)
                elif isinstance(v, dict):
                    _update_paths(v)
        _update_paths(self.config)
        
        try:
            from robovlms.train.mobile_vla_trainer import MobileVLATrainer
        except ImportError:
            # Fallback for inference-integration branch structure where it's kept in a different directory
            import sys
            import os
            fallback_path = os.path.join(os.getenv("VLA_ROOT", "/home/soda/vla"), "Robo+", "Mobile_VLA", "core", "train_core")
            if fallback_path not in sys.path:
                sys.path.append(fallback_path)
            from mobile_vla_trainer import MobileVLATrainer

        # Inject model backbone mapping required by newer V3 configs
        try:
            from robovlms.model.backbone.robokosmos import RoboKosMos
            import robovlms.model.backbone as backbone
            backbone.__dict__["RoboVLM-Nav"] = RoboKosMos
            
            import robovlms.model.policy_head as policy_head
            from robovlms.model.policy_head.mobile_vla_policy import MobileVLAClassificationDecoder, MobileVLALSTMDecoder
            policy_head.__dict__["NavPolicy"] = MobileVLAClassificationDecoder
            policy_head.__dict__["NavPolicyRegression"] = MobileVLALSTMDecoder
            
            logger.info("🔧 Injected RoboVLM-Nav & NavPolicy mapping")
        except Exception as base_e:
            logger.warning(f"⚠️ Failed to inject model mapping: {base_e}")
        
        if self.use_quant:
            from transformers import BitsAndBytesConfig
            logger.info("🔧 [MODE] BitsAndBytes INT8 (Standard/Stable)")
            bnb_config = BitsAndBytesConfig(load_in_8bit=True, llm_int8_threshold=6.0)
            self.model = MobileVLATrainer(self.config, quantization_config=bnb_config)
        else:
            logger.info("🚀 [MODE] FP16/BF16 (Action Diversity prioritized)")
            self.model = MobileVLATrainer(self.config)
            # FP16 conversion happens after loading params to avoid mismatch during load
            
        # [LEAN LOADING] Load only necessary weights and move them directly to device
        logger.info(f"Loading checkpoint (Lean Mode): {self.checkpoint_path}")
        
        # Load state dict on CPU
        checkpoint = torch.load(self.checkpoint_path, map_location='cpu', weights_only=False)
        full_state_dict = checkpoint.get('model_state_dict', checkpoint.get('state_dict'))
        
        # Filter for Projector and Policy Head only (Backbone is already official)
        # This avoids size mismatch and saves 6GB+ RAM/VRAM
        logger.info("🎯 Filtering: Loading only Projector and Policy Head")
        state_dict = {}
        for k, v in full_state_dict.items():
            if any(x in k for x in ["image_to_text_projection", "act_head", "policy_head", "resampler", "action_token", "lora"]):
                # Handle model. prefix
                new_key = k
                if k.startswith('model.') and not hasattr(self.model, 'model'):
                     new_key = k.replace('model.', '', 1)
                state_dict[new_key] = v
        
        # Cleanup full checkpoint immediately
        del full_state_dict
        del checkpoint
        gc.collect()
        
        # Load into model
        missing_keys, unexpected_keys = self.model.load_state_dict(state_dict, strict=False)
        logger.info(f"✅ Loaded {len(state_dict)} fine-tuned weights")
        
        # [CRITICAL] 1. Finalize Precision
        self.model.to(self.device).eval()
        
        if not self.use_quant:
            if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
                 logger.info("🚀 Converting backbone to BFloat16 (Ampere+ Optimized)")
                 self.model.bfloat16()
            else:
                 logger.info("🚀 Converting backbone to Float16 (Standard)")
                 self.model.half()
        else:
            logger.info("✅ Kept in INT8 (BitsAndBytes) mode")
             
        # [DEBUG/PATH FIX] Store policy_head for robust First-Frame Safety
        self.policy_head = None
        
        # 실제 모델 구조(RoboKosMos)에서는 'act_head'라는 이름을 사용하기도 합니다.
        potential_model = self.model.model if hasattr(self.model, 'model') else self.model
        
        for name in ['act_head', 'policy_head']:
            if hasattr(potential_model, name):
                self.policy_head = getattr(potential_model, name)
                logger.info(f"✅ Verified: policy_head found at model.{name}")
                break
        
        if self.policy_head is None:
            logger.warning("⚠️ Warning: policy_head (act_head) not found in model structure!")
            
        # Measure actual GPU memory
        if torch.cuda.is_available():
            gpu_memory = torch.cuda.memory_allocated() / 1024**3
            logger.info(f"\n📊 Actual GPU Memory: {gpu_memory:.3f} GB")
            logger.info(f"   Expected: ~1.7 GB (73% reduction from 6.3GB FP32)")
        
        if self.use_quant:
            logger.info("✅ Model loaded with BitsAndBytes INT8")
        else:
            logger.info("✅ Model loaded in FP16/BF16 (High Precision)")
        logger.info("="*60)
        
        # Setup image transforms
        from torchvision import transforms
        # 학습 규격에 맞는 정규화 값 유지
        self.image_transform = transforms.Compose([
            transforms.Resize((224, 224), interpolation=transforms.InterpolationMode.BICUBIC),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=self.config.get('image_mean', [0.48145466, 0.4578275, 0.40821073]),
                std=self.config.get('image_std', [0.26862954, 0.26130258, 0.27577711])
            )
        ])
        
    def preprocess_image(self, image_input: str | np.ndarray) -> torch.Tensor:
        """
        이미지를 모델 입력 형식으로 변환 (Base64 문자열 또는 NumPy 배열 지원)
        """
        if isinstance(image_input, str):
            # Base64 decode
            image_bytes = base64.b64decode(image_input)
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        elif isinstance(image_input, np.ndarray):
            # NumPy (OpenCV BGR) -> PIL RGB
            image = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
        else:
             raise ValueError(f"Unsupported image type: {type(image_input)}")
        
        # Transform
        image_tensor = self.image_transform(image)
        
        # [DEBUG] 이미지 입력 변화 확인 (환각 디버깅용)
        img_mean = image_tensor.mean().item()
        logger.debug(f"🖼️ [INPUT] Image Mean: {img_mean:.6f}")
        
        # Add batch and window dimensions: (3, 224, 224) -> (1, 1, 3, 224, 224)
        image_tensor = image_tensor.unsqueeze(0).unsqueeze(0)
        
        return image_tensor.to(self.device)
        
    def _tokenize_instruction(self, instruction: str) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Instruction을 tokenize하여 tensor로 변환
        """
        # [TEST] 접두사 없이 순수 Instruction만 사용 (학습 데이터 규합 확인용)
        # 만약 학습 시 <grounding> 포맷을 썼다면 다시 복구해야 함
        logger.debug(f"📝 [INPUT] Prompt: {instruction}")
            
        # Tokenize instruction using the pre-initialized processor
        encoded = self.processor.tokenizer(
            instruction,
            return_tensors='pt',
            padding='max_length',
            max_length=self.config['tokenizer']['max_text_len'],
            truncation=True
        )
        
        lang_x = encoded['input_ids'].to(self.device)  # (1, seq_len)
        attention_mask = encoded['attention_mask'].to(self.device)  # (1, seq_len)
        
        return lang_x, attention_mask

    
    def reset(self, instruction: str = "N/A"):
        """추론 히스토리 초기화 (LSTM state 등) 및 세션 리포트 저장"""
        try:
            # 1. End existing session if any
            if logger_instance:
                logger_instance.end_session()
            
            self.action_buffer.clear()
            self.inference_count = 0
            self.image_history = [] # Clear image buffer
            logger.info("✅ Image History Buffer Cleared")
            
            # 2. Start new logging session
            if logger_instance:
                logger_instance.start_session(model_name=self.model_name, instruction=instruction)
            
            # RoboKosMos -> act_head -> reset() 호출 (동적 조회)
            potential_model = self.model.model if hasattr(self.model, 'model') else self.model
            for name in ['act_head', 'policy_head']:
                if hasattr(potential_model, name):
                    head = getattr(potential_model, name)
                    head.reset()
                    logger.info(f"✅ Model history reset (Target: model.{name}, ID: {id(head)})")
                    return
            
            logger.warning("⚠️ act_head not found, cannot reset history")
        except Exception as e:
            logger.error(f"Reset failed: {e}")

    def predict(self, image_base64: str, instruction: str) -> tuple[np.ndarray, float, np.ndarray]:
        """
        추론 실행
        Returns:
            action: [linear, angular] (Current step action)
            latency_ms: Inference time
            full_chunk: Full action chunk sequence (N, 2)
        """
        start_time = time.time()
        
        # 0. First-Frame Zero Enforcement (EXP-History Insight)
        # 매 호출마다 policy_head를 동적으로 조회하여 일관성 유지
        potential_model = self.model.model if hasattr(self.model, 'model') else self.model
        current_policy_head = None
        for name in ['act_head', 'policy_head']:
            if hasattr(potential_model, name):
                current_policy_head = getattr(potential_model, name)
                break
        
        # [SAFETY] Always use count-based enforcement instead of history-based, 
        # as windowed inference doesn't always populate history_memory.
        is_first_frame = (self.inference_count == 0)
        
        try:
            h_len = len(current_policy_head.history_memory) if current_policy_head and hasattr(current_policy_head, 'history_memory') else -1
            if is_first_frame:
                logger.warning(f"🛡️ First-Frame Zero Enforcement (ID: {id(self)}, InfCount: {self.inference_count}, HistLen: {h_len})")
        except Exception as e:
            logger.error(f"❌ Safety check failed: {e}")
        
        if is_first_frame:

            # Increment FIRST to prevent infinite loop even if inference() crashes
            self.inference_count += 1
            
            # Apply Grounding Format (V2 Standard)
            if not instruction.startswith("<grounding>"):
                full_prompt_init = f"<grounding>An image of a robot {instruction}"
            else:
                full_prompt_init = instruction

            if logger_instance:
                logger_instance.update_instruction(instruction)
                
            logger.info(f"🛡️ Applying Enforcement... (Count now: {self.inference_count}, Prompt: {full_prompt_init})")
            with torch.no_grad():
                image_tensor = self.preprocess_image(image_base64)
                lang_x, attention_mask = self._tokenize_instruction(full_prompt_init)
                # This call MUST populate history_memory in act_head
                self.model.model.inference(vision_x=image_tensor, lang_x=lang_x, attention_mask=attention_mask)
            
            # 이미지 히스토리도 초기화해줌 (일관성)
            self.image_history = [] 
            
            latency_ms = (time.time() - start_time) * 1000
            return np.array([0.0, 0.0]), latency_ms, np.zeros((1, 2))



        # [CRITICAL] 3. Prompt Engineering (Grounding Tag)
        # instruction = request.instruction (raw) -> converted to grounding format
        if not instruction.startswith("<grounding>"):
            full_prompt = f"<grounding>An image of a robot {instruction}"
        else:
            full_prompt = instruction
            
        with torch.no_grad():
            # Preprocess image
            image_tensor = self.preprocess_image(image_base64) # (1, 1, 3, 224, 224)
            
            # Tokenize instruction
            lang_x, attention_mask = self._tokenize_instruction(full_prompt)
            
            # Ensure type matches model (FP16/BF16)
            target_dtype = next(self.model.parameters()).dtype
            image_tensor = image_tensor.to(dtype=target_dtype, device=self.device)
            
            # 🔍 입력 텐서 shape 로깅 (디버깅)
            logger.debug(f"🖼️ [INPUT] Vision Input: {image_tensor.shape}")
            logger.debug(f"📝 [INPUT] Prompt: {full_prompt}")
            
            # Model inference
            action = np.array([0.0, 0.0])
            full_chunk = np.zeros((1, 2))
            
            try:
                outputs = self.model.model.inference(
                    vision_x=image_tensor,
                    lang_x=lang_x,
                    attention_mask=attention_mask
                )
                
                # Extract action from outputs
                if isinstance(outputs, dict) and 'action' in outputs:
                    action_out = outputs['action']  # (B, T, Chunk, Dim) or (B, Chunk, Dim)
                    action_out = self._extract_action_tensor(action_out)
                    
                    # Move to CPU
                    if isinstance(action_out, torch.Tensor):
                        full_chunk = action_out.detach().float().cpu().numpy()
                    else:
                        full_chunk = action_out

                    # Reshape to (N, ActionDim) where ActionDim is usually 2 or 7
                    # full_chunk shape can be (B, T, Dim) or (B, T, Chunk, Dim)
                    # We want (TotalItems, Dim)
                    if full_chunk.ndim >= 2:
                        dim = full_chunk.shape[-1]
                        full_chunk = full_chunk.reshape(-1, dim)
                    else:
                        # Handle 1D case (e.g. [v, w])
                        full_chunk = full_chunk.reshape(1, -1)
                    
                    # Safety check
                    if full_chunk.size == 0:
                        action = np.array([0.0, 0.0])
                    else:
                        if self.inference_mode == "classification":
                            action = self._decode_classification_action(full_chunk)
                        else:
                            # Use first action for regression mode
                            action = full_chunk[0]
                    
                else:
                    logger.warning(f"Unexpected outputs type: {type(outputs)}")
                    action = np.array([0.0, 0.0])
                    full_chunk = np.zeros((1, 2))
                
                # 🔍 Raw 액션 로깅 (디버깅)
                # Check history memory length if possible
                hist_len = "N/A"
                try:
                    # Search for history memory in policy head
                    target_policy = None
                    if hasattr(self.model.model, 'act_head'):
                         target_policy = self.model.model.act_head
                    elif hasattr(self.model, 'act_head'):
                         target_policy = self.model.act_head
                         
                    if target_policy and hasattr(target_policy, 'history_memory'):
                        hist_len = len(target_policy.history_memory)
                except: pass

                logger.info(f"📤 [DETAILED ACTION] InfCount: {self.inference_count}, Hist: {hist_len}/8, Raw: {action}")
                
                # De-normalize and Clip (regression only)
                if self.inference_mode == "regression":
                    target_min = -1.15
                    target_max = 1.15
                    
                    # Config에서 norm_action 확인
                    norm_action = self.config.get('norm_action', False)
                    
                    if not norm_action:
                        # Tanh 헤드면 [-1, 1] 범위로 나옴.
                        # 우리 데이터는 [-1.15, 1.15] 범위로 학습됨 (Bang-bang control)
                        if abs(action[0]) <= 1.0 and abs(action[1]) <= 1.0:
                            logger.warning(f"⚠️ Applied auto-scaling to [-1.15, 1.15] (Raw LX: {action[0]:.4f}, LY: {action[1]:.4f})")
                            action = action * 1.15
                    elif norm_action:
                        # 학습 시 정규화했다면 Denormalize 필요
                        action = unnoramalize_action(
                            action,
                            action_min=target_min,
                            action_max=target_max
                        )
                        logger.debug("✅ Applied denormalization (norm_action=True)")

                logger.debug(f"📤 [PROCESSED ACTION] After scaling: {action}")

                # Clip to valid range
                action[0] = np.clip(action[0], -1.5, 1.5)
                action[1] = np.clip(action[1], -1.5, 1.5)
                logger.info(f"📤 [FINAL ACTION] After clipping: [{action[0]:.3f}, {action[1]:.3f}]")
                
            except Exception as e:
                logger.error(f"Inference failed: {e}")
                import traceback
                traceback.print_exc()
                # action and full_chunk already have defaults

            
        latency_ms = (time.time() - start_time) * 1000
        self.inference_count += 1
        
        # 4. Log step data
        if logger_instance:
            logger_instance.log_step(self.inference_count, action, latency_ms, full_chunk)
            
        return action, latency_ms, full_chunk


def get_model(refresh=False, use_quant=None):
    """
    모델 인스턴스 가져오기 (lazy loading)
    Args:
        refresh: Force reload model
        use_quant: Override quantization setting
    """
    global model_instance
    
    if refresh:
        if model_instance:
            del model_instance
            torch.cuda.empty_cache()
            model_instance = None
            logger.info("🔄 Model unloaded for refresh")
    
    if model_instance is None:
        # Checkpoint and Config from Env or Default
        checkpoint_path = os.getenv(
            "VLA_CHECKPOINT_PATH",
            "runs/v4_nav/kosmos/mobile_vla_v4_exp01/2026-03-15/v4-retrain-v4/epoch_epoch=epoch=04-val_loss=val/loss=1.851.ckpt"
        )
        config_path = os.getenv(
            "VLA_CONFIG_PATH", 
            "configs/mobile_vla_v4_exp01.json"
        )
        
        model_instance = MobileVLAInference(
            checkpoint_path=checkpoint_path,
            config_path=config_path,
            device="cuda" if torch.cuda.is_available() else "cpu",
            use_quant=use_quant
        )
    
    return model_instance


@app.get("/")
async def root():
    """API 정보 (인증 불필요)"""
    return {
        "name": "Mobile VLA Inference API",
        "version": "1.0.0",
        "status": "running",
        "auth": "API Key required (X-API-Key header)"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 (인증 불필요)"""
    gpu_memory = None
    model_name = "Unknown"
    
    if torch.cuda.is_available():
        gpu_memory = {
            "allocated_gb": torch.cuda.memory_allocated() / 1024**3,
            "reserved_gb": torch.cuda.memory_reserved() / 1024**3,
            "device_name": torch.cuda.get_device_name(0)
        }
        
    if model_instance:
        try:
            config_path = model_instance.config_path
            model_name = os.path.basename(config_path).replace(".json", "")
        except:
            model_name = "Loaded"
    
    return {
        "status": "healthy",
        "model_loaded": model_instance is not None,
        "model_name": model_name,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "gpu_memory": gpu_memory
    }


@app.post("/predict", response_model=InferenceResponse)
async def predict(request: InferenceRequest, api_key: str = Depends(verify_api_key)):
    """추론 엔드포인트"""
    try:
        model = get_model()
        
        action, latency_ms, chunk = model.predict(
            image_base64=request.image,
            instruction=request.instruction
        )
        
        logger.info(f"✅ Prediction: {action}, Latency: {latency_ms:.1f}ms")
        
        return InferenceResponse(
            action=action.tolist(),
            latency_ms=latency_ms,
            model_name=model.model_name,
            strategy="receding_horizon",
            source="inferred",
            buffer_status={}
        )
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset")
async def reset_history(api_key: str = Depends(verify_api_key)):
    """추론 히스토리(LSTM Hidden State 등) 초기화 및 세션 종료"""
    model = get_model()
    try:
        model.reset()
        return {"status": "success", "message": "History, buffer, and logging session reset"}
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
async def test_endpoint(api_key: str = Depends(verify_api_key)):
    """테스트 엔드포인트"""
    import base64
    from io import BytesIO
    from PIL import Image
    
    dummy_img = Image.new('RGB', (1280, 720), color=(255, 0, 0))
    buffer = BytesIO()
    dummy_img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    instruction = "Navigate around obstacles and reach the front of the beverage bottle on the left"
    dummy_action = [1.15, 0.319]
    
    return {
        "message": "Test endpoint - using dummy data",
        "instruction": instruction,
        "action": dummy_action,
        "note": "This is a test endpoint. Use POST /predict for real inference."
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
